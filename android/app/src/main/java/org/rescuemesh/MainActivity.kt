package org.rescuemesh

import android.Manifest
import android.content.Intent
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.*
import kotlinx.serialization.encodeToString

class MainActivity: ComponentActivity() {
    private lateinit var store: EventStore
    private lateinit var mesh: NearbyMesh
    private lateinit var agent: LocalAgent
    private var logs by mutableStateOf(listOf("Synthetic mission only. Real inference requires imported model."))
    private var pair by mutableStateOf<Triple<String,String,String>?>(null)
    private var tab by mutableStateOf("Report")
    private var busy by mutableStateOf(false)
    private var auto by mutableStateOf(false)
    private var modelReady by mutableStateOf(false)
    private var lastAutoRevision by mutableStateOf("")
    private var notice by mutableStateOf("")
    private fun log(message: String) { runOnUiThread { logs=(listOf(message)+logs).take(40); notice=message } }
    private fun work(block: suspend ()->Unit) { lifecycleScope.launch { busy=true; try { block() } catch(e: Exception) { log("Failure: ${e.message}. Source reports retained.") } catch(e: LinkageError) { log("Native runtime unavailable: ${e.message}. Source reports and relay retained.") } finally { busy=false } } }
    private val permissions=registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { grants -> if(grants.values.all { it }) mesh.start() else log("Nearby permissions denied; relay not started") }
    private val modelPicker=registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri -> if(uri != null) work { agent.importModel(uri); modelReady=false } }
    private val trustPicker=registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri -> if(uri != null) work { withContext(Dispatchers.IO) { contextRead(uri,65536).let { store.importTrust(it) } }; log("Mission trust manifest imported: ${store.trust.devices.size} devices") } }
    private val exportIdentity=registerForActivityResult(ActivityResultContracts.CreateDocument("application/json")) { uri -> if(uri != null) work { withContext(Dispatchers.IO) { contentResolver.openOutputStream(uri)!!.use { it.write(wire.encodeToString(Trust(MISSION,mapOf(store.identity.id to store.identity.publicKey))).toByteArray()) } }; log("Public identity exported; combine identities into mission trust manifest") } }
    private fun contextRead(uri: android.net.Uri, max: Int): ByteArray = contentResolver.openInputStream(uri)!!.use { input ->
        val out=java.io.ByteArrayOutputStream(); val buffer=ByteArray(8192)
        while(true) { val n=input.read(buffer); if(n<0) break; require(out.size()+n<=max); out.write(buffer,0,n) }
        out.toByteArray()
    }
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        store=EventStore(this,Identity()); agent=LocalAgent(this,store,::log)
        mesh=NearbyMesh(this,store,lifecycleScope,::log) { endpoint,name,digits -> runOnUiThread { pair=Triple(endpoint,name,digits) } }
        setContent { MaterialTheme(colorScheme=darkColorScheme()) {
            val rows by store.dao.watch().collectAsState(initial=emptyList())
            var iid by remember { mutableStateOf("school-01") }; var location by remember { mutableStateOf("river-school") }
            var report by remember { mutableStateOf("Synthetic: six people waiting at River School. Water is rising. Route condition unknown.") }
            var subject by remember { mutableStateOf("school-route") }; var predicate by remember { mutableStateOf("passable") }; var value by remember { mutableStateOf("unknown") }
            var answerTo by remember { mutableStateOf("") }
            var base by remember { mutableStateOf(getSharedPreferences("gateway",MODE_PRIVATE).getString("url","") ?: "") }; var token by remember { mutableStateOf("") }
            val sources=rows.map { it.event() }.filter { it.payload.incident_id==iid && it.event_type in setOf("observation","answer") }
            val rev=revision(sources)
            LaunchedEffect(rev,auto,modelReady,busy) {
                if(auto && modelReady && sources.isNotEmpty() && !busy && lastAutoRevision!=rev && rows.none { it.incident==iid && it.eventType=="assessment" && it.event().payload.evidence_revision==rev }) {
                    lastAutoRevision=rev; work { agent.assess(iid); mesh.refresh() }
                }
            }
            Surface(Modifier.fillMaxSize()) { Column(Modifier.padding(18.dp).verticalScroll(rememberScrollState())) {
                Text("RescueMesh",style=MaterialTheme.typography.headlineLarge)
                Text("OFFLINE RESPONSE · SYNTHETIC DEMO",color=MaterialTheme.colorScheme.primary)
                Text("Device ${store.identity.id.take(12)} · ${rows.size} durable events · ${rows.count { !it.uploaded }} pending cloud")
                Spacer(Modifier.height(12.dp))
                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(4.dp)) { listOf("Report","Nearby","Model").forEach { label -> Button(onClick={tab=label},modifier=Modifier.weight(1f)) { Text(label) } } }
                Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) { TextButton(onClick={tab="Evidence"}) { Text("Evidence") }; TextButton(onClick={tab="Gateway"}) { Text("Gateway") } }
                if(busy) LinearProgressIndicator(Modifier.fillMaxWidth())
                Text(notice,style=MaterialTheme.typography.bodySmall)
                Spacer(Modifier.height(12.dp))
                when(tab) {
                    "Report" -> {
                        OutlinedTextField(iid,{iid=it},label={Text("Incident ID")},modifier=Modifier.fillMaxWidth())
                        locations.forEach { (id,name) -> Row { RadioButton(selected=location==id,onClick={location=id}); Text(name,Modifier.padding(top=12.dp)) } }
                        OutlinedTextField(report,{report=it},label={Text("Observation or follow-up answer")},minLines=3,modifier=Modifier.fillMaxWidth())
                        OutlinedTextField(answerTo,{answerTo=it},label={Text("Question event ID (blank = observation)")},modifier=Modifier.fillMaxWidth())
                        Text("Optional explicit claim for contradiction comparison")
                        OutlinedTextField(subject,{subject=it},label={Text("Subject")},modifier=Modifier.fillMaxWidth())
                        OutlinedTextField(predicate,{predicate=it},label={Text("Predicate")},modifier=Modifier.fillMaxWidth())
                        OutlinedTextField(value,{value=it},label={Text("Reported value")},modifier=Modifier.fillMaxWidth())
                        Button(enabled=!busy,onClick={ work {
                            val claims=if(subject.isBlank()) emptyList() else listOf(Claim(subject,predicate,value))
                            val r=store.create(if(answerTo.isBlank()) "observation" else "answer",EventPayload(iid,location,text=report,claims=claims),if(answerTo.isBlank()) emptyList() else listOf(answerTo))
                            log("Source saved before inference: ${r.id}"); mesh.refresh()
                        } }) { Text("Save source evidence") }
                        Button(enabled=!busy && sources.isNotEmpty(),onClick={work { agent.assess(iid); mesh.refresh() }}) { Text("Run real offline assessment") }
                        Row { Switch(auto,{auto=it}); Text("Reassess selected incident on new evidence",Modifier.padding(top=10.dp)) }
                        Text("Models propose only. Route safety remains unknown. No automatic dispatch.")
                    }
                    "Nearby" -> {
                        Text("Foreground encrypted Nearby transport. Both users compare pairing digits, then registered keys prove mission membership.")
                        Button(onClick={exportIdentity.launch("identity-${store.identity.id.take(8)}.json")}) { Text("Export public device identity") }
                        Button(onClick={trustPicker.launch(arrayOf("application/json","text/plain"))}) { Text("Import authorized mission manifest") }
                        Text("Enrolled devices: ${store.trust.devices.size}")
                        Button(onClick={
                            val required=if(Build.VERSION.SDK_INT>=33) arrayOf(Manifest.permission.BLUETOOTH_SCAN,Manifest.permission.BLUETOOTH_CONNECT,Manifest.permission.BLUETOOTH_ADVERTISE,Manifest.permission.NEARBY_WIFI_DEVICES) else if(Build.VERSION.SDK_INT>=31) arrayOf(Manifest.permission.BLUETOOTH_SCAN,Manifest.permission.BLUETOOTH_CONNECT,Manifest.permission.BLUETOOTH_ADVERTISE,Manifest.permission.ACCESS_COARSE_LOCATION,Manifest.permission.ACCESS_FINE_LOCATION) else arrayOf(Manifest.permission.ACCESS_COARSE_LOCATION,Manifest.permission.ACCESS_FINE_LOCATION)
                            permissions.launch(required)
                        }) { Text("Discover and advertise") }
                        Button(onClick={mesh.spike()}) { Text("Send small Nearby spike payload") }
                        Button(onClick={mesh.refresh()}) { Text("Exchange missing event IDs") }
                        Button(onClick={mesh.stop(); log("Nearby stopped")}) { Text("Stop peer exchange") }
                        Text("One phone cannot prove a radio transfer. Obtain two more for A → B → C. Events persist after disconnect/restart.")
                    }
                    "Model" -> {
                        Text("Start with official Gemma 4 E2B LiteRT-LM artifact. Weight import is local; inference calls no cloud API. Runtime 0.18.0, CPU, context 4096 tokens. Weights omitted from APK.")
                        Button(enabled=!busy,onClick={modelPicker.launch(arrayOf("*/*"))}) { Text("Import .litertlm weights") }
                        Button(enabled=!busy,onClick={work { agent.load(); modelReady=true }}) { Text("Load real model and measure") }
                        Text("Read measured load/inference timings and checksum in logs. Disable internet and record phone state for proof. Photo inference waits until this spike passes on hardware.")
                    }
                    "Gateway" -> {
                        OutlinedTextField(base,{base=it},label={Text("HTTPS backend URL")},modifier=Modifier.fillMaxWidth())
                        OutlinedTextField(token,{token=it},label={Text("Per-device mission sync token")},visualTransformation=androidx.compose.ui.text.input.PasswordVisualTransformation(),modifier=Modifier.fillMaxWidth())
                        Text("Token is kept in memory only. No Google credentials or Gemini keys on phones.")
                        Button(enabled=!busy,onClick={work {
                            getSharedPreferences("gateway",MODE_PRIVATE).edit().putString("url",base).apply()
                            val n=Gateway(store).sync(base,token); log("Cloud durably acknowledged $n events")
                        }}) { Text("Upload durable events") }
                    }
                    "Evidence" -> {
                        OutlinedTextField(iid,{iid=it},label={Text("Selected incident")},modifier=Modifier.fillMaxWidth())
                        rows.filter { it.incident==iid }.forEach { row ->
                            val e=row.event(); val p=e.payload
                            Card(Modifier.fillMaxWidth().padding(vertical=6.dp)) { Column(Modifier.padding(12.dp)) {
                                Text("${e.event_type.uppercase()} · ${if(row.uploaded) "cloud synced" else "local pending"}")
                                Text("${e.event_id}\nOrigin ${e.origin_device_id.take(12)} #${e.origin_sequence}\nReceived via ${row.receivedFrom.take(12)}",style=MaterialTheme.typography.bodySmall)
                                p.text?.let { Text(it) }
                                p.assessment?.let { a ->
                                    Text("INFERRED · ${p.provider} · ${if(p.evidence_revision==rev) "current evidence" else "STALE — reassess"}")
                                    a.observed_facts.forEach { Text("Reported: ${it.text}\nSupports: ${it.supporting_event_ids.joinToString()}") }
                                    a.uncertain_or_conflicting_claims.forEach { Text("Uncertain: ${it.text}\nSupports: ${it.supporting_event_ids.joinToString()}") }
                                    Text("Question: ${a.next_question}\nDraft response: ${a.proposed_response.action}\nPrerequisites: ${a.proposed_response.prerequisites.joinToString()}")
                                }
                                if(e.event_type=="question") TextButton(onClick={answerTo=e.event_id; tab="Report"}) { Text("Answer this question") }
                            } }
                        }
                    }
                }
                HorizontalDivider(Modifier.padding(vertical=12.dp)); Text("Execution log",style=MaterialTheme.typography.titleMedium)
                logs.take(12).forEach { Text(it,style=MaterialTheme.typography.bodySmall,modifier=Modifier.padding(vertical=4.dp)) }
            } }
            pair?.let { (endpoint,name,digits) -> AlertDialog(onDismissRequest={mesh.confirm(endpoint,false); pair=null},title={Text("Confirm mission peer")},text={Text("${name.take(12)}\nCompare on BOTH phones: $digits")},confirmButton={TextButton(onClick={mesh.confirm(endpoint,true); pair=null}) { Text("Digits match") }},dismissButton={TextButton(onClick={mesh.confirm(endpoint,false); pair=null}) { Text("Reject") }}) }
        } }
    }
    override fun onStop() { super.onStop(); if(::mesh.isInitialized) mesh.stop() }
    override fun onDestroy() { if(::store.isInitialized) { CoroutineScope(Dispatchers.IO).launch { agent.close(); store.db.close() } }; super.onDestroy() }
}
