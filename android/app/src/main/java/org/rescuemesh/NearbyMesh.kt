package org.rescuemesh

import android.content.Context
import com.google.android.gms.nearby.Nearby
import com.google.android.gms.nearby.connection.*
import kotlinx.coroutines.*
import kotlinx.serialization.encodeToString
import java.security.SecureRandom
import java.util.concurrent.ConcurrentHashMap

class NearbyMesh(context: Context, private val store: EventStore, private val scope: CoroutineScope, private val log: (String)->Unit, private val pairing: (String,String,String)->Unit) {
    private val client = Nearby.getConnectionsClient(context)
    private val connected = ConcurrentHashMap<String,String>()
    private val pendingNames = ConcurrentHashMap<String,String>()
    private val challenges = ConcurrentHashMap<String,String>()
    private val readyPeers = ConcurrentHashMap.newKeySet<String>()
    private var ticker: Job? = null
    private val serviceId = "org.rescuemesh.$MISSION.v1"
    private val lifecycle = object: ConnectionLifecycleCallback() {
        override fun onConnectionInitiated(endpoint: String, info: ConnectionInfo) {
            if(info.endpointName !in store.trust.devices) { client.rejectConnection(endpoint); log("Rejected unenrolled endpoint"); return }
            pendingNames[endpoint] = info.endpointName
            pairing(endpoint,info.endpointName,info.authenticationDigits)
        }
        override fun onConnectionResult(endpoint: String, resolution: ConnectionResolution) {
            if(resolution.status.isSuccess) {
                val nonce = ByteArray(32).also { SecureRandom().nextBytes(it) }.b64(); challenges[endpoint] = nonce
                send(endpoint,Packet("challenge",nonce=nonce,device_id=store.identity.id)); log("Encrypted transport connected; verifying mission key")
            } else { pendingNames.remove(endpoint); log("Connection refused or failed: ${resolution.status.statusCode}") }
        }
        override fun onDisconnected(endpoint: String) { connected.remove(endpoint); challenges.remove(endpoint); pendingNames.remove(endpoint); readyPeers.remove(endpoint); log("Peer disconnected; stored events retained") }
    }
    private fun proofBytes(nonce: String, challenger: String, responder: String) = "$MISSION|$challenger|$responder|$nonce".toByteArray()
    private val payloads = object: PayloadCallback() {
        override fun onPayloadReceived(endpoint: String, payload: Payload) {
            val bytes = payload.asBytes() ?: return
            if(bytes.size > 30000) { log("Rejected oversized packet"); return }
            scope.launch(Dispatchers.IO) {
                try {
                    val p = wire.decodeFromString<Packet>(bytes.toString(Charsets.UTF_8))
                    require(p.ids.size <= 64 && p.events.size <= 2 && p.offset in 0..250)
                    when(p.kind) {
                        "challenge" -> {
                            val peer = pendingNames[endpoint] ?: error("Unknown peer")
                            require(p.device_id == peer && p.nonce!!.unb64().size == 32)
                            send(endpoint,Packet("proof",device_id=store.identity.id,signature=store.identity.sign(proofBytes(p.nonce,peer,store.identity.id))))
                        }
                        "proof" -> {
                            val peer = pendingNames[endpoint] ?: error("Unknown peer")
                            val nonce = challenges.remove(endpoint) ?: error("No challenge")
                            require(p.device_id == peer)
                            verifySignature(store.trust,peer,proofBytes(nonce,store.identity.id,peer),p.signature!!)
                            connected[endpoint] = peer; log("Authorized mission peer ${peer.take(8)}")
                            send(endpoint,Packet("ready"))
                            if(endpoint in readyPeers) inventory(endpoint,0)
                        }
                        "ready" -> {
                            require(pendingNames.containsKey(endpoint))
                            readyPeers.add(endpoint)
                            if(connected.containsKey(endpoint)) inventory(endpoint,0)
                        }
                        else -> {
                            val peer = connected[endpoint] ?: error("Peer key not authenticated")
                            when(p.kind) {
                                "inventory_request" -> inventory(endpoint,p.offset)
                                "inventory" -> {
                                    val have = store.dao.byIds(p.ids).map { it.id }.toSet()
                                    (p.ids.filter { it !in have }).chunked(2).forEach { send(endpoint,Packet("request",ids=it)) }
                                    p.next?.let { require(it == p.offset + 64 && it <= 250); send(endpoint,Packet("inventory_request",offset=it)) }
                                }
                                "request" -> {
                                    require(p.ids.size <= 2)
                                    val rows = store.dao.byIds(p.ids)
                                    eventPackets(rows.map { it.envelope() }).forEach { send(endpoint,it) }
                                }
                                "events" -> {
                                    val ids = store.receive(p.events,peer)
                                    // Application ACK follows Room commit, never the transport completion callback.
                                    send(endpoint,Packet("ack",ids=ids)); log("Durably stored ${ids.size} events from ${peer.take(8)}")
                                }
                                "ack" -> log("Peer committed ${p.ids.size} events")
                                "spike" -> log("Nearby small payload received from ${peer.take(8)}")
                                else -> error("Unknown packet kind")
                            }
                        }
                    }
                } catch(e: Exception) { log("Rejected packet: ${e.message}"); client.disconnectFromEndpoint(endpoint); connected.remove(endpoint); readyPeers.remove(endpoint) }
            }
        }
        override fun onPayloadTransferUpdate(endpoint: String, update: PayloadTransferUpdate) {
            if(update.status == PayloadTransferUpdate.Status.FAILURE) log("Payload transfer failed; foreground inventory will retry")
        }
    }
    private fun send(endpoint: String, p: Packet) {
        val bytes = wire.encodeToString(p).toByteArray(); require(bytes.size <= 30000)
        client.sendPayload(endpoint,Payload.fromBytes(bytes)).addOnFailureListener { log("Send failed: ${it.message}") }
    }
    private suspend fun inventory(endpoint: String, offset: Int) {
        val rows = store.dao.inventory(offset)
        send(endpoint,Packet("inventory",ids=rows.map { it.id },offset=offset,next=if(rows.size==64 && offset+64<250) offset+64 else null))
    }
    fun confirm(endpoint: String, accept: Boolean) {
        if(accept) client.acceptConnection(endpoint,payloads).addOnFailureListener { log("Accept failed: ${it.message}") }
        else { client.rejectConnection(endpoint); pendingNames.remove(endpoint) }
    }
    fun start() {
        client.startAdvertising(store.identity.id,serviceId,lifecycle,AdvertisingOptions.Builder().setStrategy(Strategy.P2P_CLUSTER).build()).addOnSuccessListener { log("Advertising") }.addOnFailureListener { log("Advertising failed: ${it.message}") }
        client.startDiscovery(serviceId,object: EndpointDiscoveryCallback() {
            override fun onEndpointFound(endpoint: String, info: DiscoveredEndpointInfo) {
                if(info.endpointName in store.trust.devices && store.identity.id < info.endpointName)
                    client.requestConnection(store.identity.id,endpoint,lifecycle).addOnFailureListener { log("Request failed: ${it.message}") }
            }
            override fun onEndpointLost(endpoint: String) { log("Discovery endpoint lost") }
        },DiscoveryOptions.Builder().setStrategy(Strategy.P2P_CLUSTER).build()).addOnSuccessListener { log("Discovering") }.addOnFailureListener { log("Discovery failed: ${it.message}") }
        ticker?.cancel()
        ticker = scope.launch(Dispatchers.IO) { var backoff = 2000L; while(isActive) { delay(backoff); connected.keys.toList().filter { it in readyPeers }.forEach { inventory(it,0) }; backoff=(backoff*2).coerceAtMost(30000) } }
    }
    fun spike() { val peers=connected.keys.toList().filter { it in readyPeers }; peers.forEach { send(it,Packet("spike")) }; log("Small payload sent to ${peers.size} authenticated peers") }
    fun refresh() { scope.launch(Dispatchers.IO) { connected.keys.toList().filter { it in readyPeers }.forEach { inventory(it,0) } } }
    fun stop() { ticker?.cancel(); client.stopAdvertising(); client.stopDiscovery(); client.stopAllEndpoints(); connected.clear(); challenges.clear(); pendingNames.clear(); readyPeers.clear() }
}
