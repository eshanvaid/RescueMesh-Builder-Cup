package org.rescuemesh

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import androidx.room.*
import kotlinx.coroutines.flow.Flow
import kotlinx.serialization.encodeToString
import java.security.*
import java.security.spec.ECGenParameterSpec
import java.time.Instant
import java.util.UUID

@Entity(tableName="events", indices=[Index(value=["origin","sequence"], unique=true)])
data class EventRow(@PrimaryKey val id: String, val origin: String, val sequence: Long, val incident: String, val eventType: String, val eventB64: String, val signatureB64: String, val receivedFrom: String, val receivedAt: String, val uploaded: Boolean = false) {
    fun envelope() = Envelope(eventB64, signatureB64)
    fun event() = parseEvent(eventB64.unb64())
}
@Entity(tableName="counters") data class Counter(@PrimaryKey val origin: String, val next: Long)
@Dao interface EventDao {
    @Query("SELECT * FROM events ORDER BY receivedAt DESC") fun watch(): Flow<List<EventRow>>
    @Query("SELECT * FROM events ORDER BY id LIMIT 64 OFFSET :offset") suspend fun inventory(offset: Int): List<EventRow>
    @Query("SELECT * FROM events WHERE id IN (:ids)") suspend fun byIds(ids: List<String>): List<EventRow>
    @Query("SELECT * FROM events WHERE incident=:incident ORDER BY id") suspend fun incident(incident: String): List<EventRow>
    @Query("SELECT * FROM events WHERE id=:id") suspend fun get(id: String): EventRow?
    @Query("SELECT * FROM events WHERE origin=:origin AND sequence=:seq") suspend fun sequence(origin: String, seq: Long): EventRow?
    @Query("SELECT COUNT(*) FROM events") suspend fun count(): Int
    @Insert suspend fun insert(row: EventRow)
    @Query("SELECT * FROM counters WHERE origin=:origin") suspend fun counter(origin: String): Counter?
    @Insert(onConflict=OnConflictStrategy.REPLACE) suspend fun counter(row: Counter)
    @Query("SELECT * FROM events WHERE uploaded=0 ORDER BY receivedAt LIMIT 16") suspend fun pending(): List<EventRow>
    @Query("UPDATE events SET uploaded=1 WHERE id IN (:ids)") suspend fun uploaded(ids: List<String>)
}
@Database(entities=[EventRow::class,Counter::class], version=1, exportSchema=false)
abstract class MeshDatabase: RoomDatabase() { abstract fun events(): EventDao }

class Identity {
    private val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
    init {
        if(!store.containsAlias("rescuemesh-origin")) {
            KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC,"AndroidKeyStore").apply {
                initialize(KeyGenParameterSpec.Builder("rescuemesh-origin", KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY).setAlgorithmParameterSpec(ECGenParameterSpec("secp256r1")).setDigests(KeyProperties.DIGEST_SHA256).build())
            }.generateKeyPair()
        }
    }
    val publicKey: String get() = store.getCertificate("rescuemesh-origin").publicKey.encoded.b64()
    val id: String get() = publicKey.unb64().sha256().take(32)
    fun sign(bytes: ByteArray): String = Signature.getInstance("SHA256withECDSA").run { initSign(store.getKey("rescuemesh-origin",null) as PrivateKey); update(bytes); sign().b64() }
}

class EventStore(context: Context, val identity: Identity, databaseName: String = "rescuemesh.db") {
    val db = Room.databaseBuilder(context, MeshDatabase::class.java,databaseName).build()
    val dao = db.events()
    private val prefs = context.getSharedPreferences("mission",Context.MODE_PRIVATE)
    var trust: Trust = prefs.getString("trust", null)?.let { wire.decodeFromString<Trust>(it) } ?: Trust(MISSION, mapOf(identity.id to identity.publicKey))
        private set
    fun importTrust(bytes: ByteArray) {
        require(bytes.size <= 65536)
        val next = wire.decodeFromString<Trust>(bytes.toString(Charsets.UTF_8))
        require(next.mission_id == MISSION && next.devices.size in 1..20 && next.devices[identity.id] == identity.publicKey)
        next.devices.forEach { (id,key) -> require(key.unb64().sha256().take(32) == id) }
        check(prefs.edit().putString("trust",wire.encodeToString(next)).commit()) { "Could not persist mission trust" }; trust = next
    }
    suspend fun create(type: String, payload: EventPayload, refs: List<String> = emptyList()): EventRow = db.withTransaction {
        require(dao.count() < 250) { "Demo event capacity reached" }
        val seq = dao.counter(identity.id)?.next ?: 1L
        require(dao.incident(payload.incident_id).all { it.event().payload.location_id == payload.location_id }) { "Incident location changed" }
        if(type == "answer") require(refs.isNotEmpty() && refs.all { id -> dao.get(id)?.let { it.eventType=="question" && it.incident==payload.incident_id } == true }) { "Answer must reference an existing question for this incident" }
        val event = Event(event_id=UUID.randomUUID().toString(),origin_device_id=identity.id, origin_sequence=seq,event_type=type,created_at=Instant.now().toString(),referenced_event_ids=refs,payload=payload)
        val bytes = wire.encodeToString(event).toByteArray(); parseEvent(bytes)
        val row = EventRow(event.event_id,identity.id,seq,payload.incident_id,type,bytes.b64(),identity.sign(bytes),identity.id,Instant.now().toString())
        dao.insert(row); dao.counter(Counter(identity.id,seq+1)); row
    }
    suspend fun receive(envelopes: List<Envelope>, peer: String): List<String> {
        require(envelopes.size <= 2)
        val parsed = envelopes.map { verifyEnvelope(it,trust) }
        return db.withTransaction {
            val fresh = mutableListOf<Event>()
            val acknowledged = parsed.zip(envelopes).map { (event,envelope) ->
                val old = dao.get(event.event_id)
                if(old != null) require(old.eventB64 == envelope.event_b64) { "Event ID collision" }
                else {
                    require(dao.count() < 250); require(dao.sequence(event.origin_device_id,event.origin_sequence) == null) { "Origin sequence collision" }
                    require(dao.incident(event.payload.incident_id).all { it.event().payload.location_id == event.payload.location_id }) { "Incident location changed" }
                    dao.insert(EventRow(event.event_id,event.origin_device_id,event.origin_sequence,event.payload.incident_id,event.event_type,envelope.event_b64,envelope.signature_b64,peer,Instant.now().toString()))
                    fresh.add(event)
                }
                event.event_id
            }
            // One receipt per incident for newly received source evidence only; receipts never generate receipts.
            fresh.filter { it.event_type in setOf("observation","answer") }.groupBy { it.payload.incident_id }.values.forEach { group ->
                val first=group.first(); val ids=group.map { it.event_id }
                create("delivery-receipt",EventPayload(first.payload.incident_id,first.payload.location_id,text="Durably received source events from authorized peer $peer",receipt_event_ids=ids),ids)
            }
            acknowledged
        }
    }
}
