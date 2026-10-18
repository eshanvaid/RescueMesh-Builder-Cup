package org.rescuemesh

import kotlinx.serialization.*
import kotlinx.serialization.json.*
import java.security.*
import java.security.spec.X509EncodedKeySpec
import java.util.Base64
import java.time.Instant
import java.util.UUID
import com.fasterxml.jackson.core.JsonFactory
import com.fasterxml.jackson.core.StreamReadFeature

const val MISSION = "synthetic-flood-01"
val locations = linkedMapOf("river-school" to "River School", "east-bridge" to "East Bridge", "hill-clinic" to "Hill Clinic")
val wire = Json { ignoreUnknownKeys = false; encodeDefaults = true; explicitNulls = false }
fun ByteArray.b64(): String = Base64.getEncoder().encodeToString(this)
fun String.unb64(): ByteArray = Base64.getDecoder().decode(this)
fun ByteArray.sha256(): String = MessageDigest.getInstance("SHA-256").digest(this).joinToString("") { "%02x".format(it) }

@Serializable data class Claim(val subject: String, val predicate: String, val value: String)
@Serializable data class Fact(val text: String, val supporting_event_ids: List<String>)
@Serializable data class Response(val action: String, val prerequisites: List<String>, val resource_id: String, val supporting_event_ids: List<String>)
@Serializable data class Assessment(val observed_facts: List<Fact>, val uncertain_or_conflicting_claims: List<Fact>, val missing_information: List<String>, val next_question: String, val proposed_response: Response)
@Serializable data class EventPayload(val incident_id: String, val location_id: String, val text: String? = null, val claims: List<Claim> = emptyList(), val assessment: Assessment? = null, val provider: String? = null, val model: String? = null, val evidence_revision: String? = null, val receipt_event_ids: List<String> = emptyList())
@Serializable data class Event(val schema_version: Int = 1, val event_id: String, val mission_id: String = MISSION, val origin_device_id: String, val origin_sequence: Long, val event_type: String, val created_at: String, val referenced_event_ids: List<String>, val payload: EventPayload)
@Serializable data class Envelope(val event_b64: String, val signature_b64: String)
@Serializable data class Trust(val mission_id: String, val devices: Map<String,String>)
@Serializable data class Packet(val kind: String, val ids: List<String> = emptyList(), val events: List<Envelope> = emptyList(), val offset: Int = 0, val next: Int? = null, val nonce: String? = null, val device_id: String? = null, val signature: String? = null)

fun eventPackets(envelopes: List<Envelope>): List<Packet> {
    val packets=mutableListOf<Packet>(); var batch=emptyList<Envelope>()
    for(envelope in envelopes) {
        val candidate=batch+envelope
        if(candidate.size>2 || wire.encodeToString(Packet("events",events=candidate)).toByteArray().size>30000) {
            require(batch.isNotEmpty()) { "Single envelope exceeds packet bound" }
            packets.add(Packet("events",events=batch)); batch=listOf(envelope)
        } else batch=candidate
        require(wire.encodeToString(Packet("events",events=batch)).toByteArray().size<=30000)
    }
    if(batch.isNotEmpty()) packets.add(Packet("events",events=batch))
    return packets
}

fun parseEvent(raw: ByteArray): Event {
    require(raw.size <= 12288) { "Event exceeds 12 KiB" }
    JsonFactory.builder().enable(StreamReadFeature.STRICT_DUPLICATE_DETECTION).build().createParser(raw).use { while (it.nextToken() != null) {} }
    val utf8=Charsets.UTF_8.newDecoder().onMalformedInput(java.nio.charset.CodingErrorAction.REPORT).onUnmappableCharacter(java.nio.charset.CodingErrorAction.REPORT).decode(java.nio.ByteBuffer.wrap(raw)).toString()
    val e = wire.decodeFromString<Event>(utf8)
    require(e.schema_version == 1 && e.mission_id == MISSION)
    require(UUID.fromString(e.event_id).toString() == e.event_id); Instant.parse(e.created_at)
    require(e.origin_device_id.matches(Regex("[a-f0-9]{32}")) && e.origin_sequence in 1..9007199254740991L)
    require(e.event_type in setOf("observation","question","answer","assessment","proposal","approval","delivery-receipt"))
    require(e.event_type != "approval") { "Approvals require central coordinator" }
    require(e.referenced_event_ids.size <= 32); e.referenced_event_ids.forEach { require(UUID.fromString(it).toString() == it) }
    val p = e.payload
    require(p.incident_id.matches(Regex("[a-zA-Z0-9_-]{1,80}")) && p.location_id in locations)
    require(p.claims.size <= 8 && p.receipt_event_ids.size <= 32)
    p.claims.forEach { require(it.subject.length in 1..100 && it.predicate.length in 1..100 && it.value.length in 1..200) }
    p.text?.let { require(it.length in 1..2000) }
    p.provider?.let { require(it.length<=80) }; p.model?.let { require(it.length<=100) }
    if(e.event_type in setOf("observation","question","answer")) require(!p.text.isNullOrBlank())
    if(e.event_type == "answer") require(e.referenced_event_ids.isNotEmpty())
    if(e.event_type in setOf("assessment","proposal")) {
        require(p.assessment != null && !p.provider.isNullOrBlank() && !p.model.isNullOrBlank() && p.evidence_revision?.matches(Regex("[a-f0-9]{64}")) == true)
        validateAssessment(p.assessment, e.referenced_event_ids.toSet())
    }
    if(e.event_type == "delivery-receipt") require(p.receipt_event_ids.isNotEmpty())
    return e
}

fun verifyEnvelope(envelope: Envelope, trust: Trust): Event {
    val bytes = envelope.event_b64.unb64(); val e = parseEvent(bytes)
    require(trust.mission_id == e.mission_id)
    verifySignature(trust, e.origin_device_id, bytes, envelope.signature_b64)
    return e
}

fun verifySignature(trust: Trust, id: String, bytes: ByteArray, signature: String) {
    val keyBytes = (trust.devices[id] ?: error("Origin not enrolled in mission")).unb64()
    require(keyBytes.sha256().take(32) == id)
    val key = KeyFactory.getInstance("EC").generatePublic(X509EncodedKeySpec(keyBytes)) as java.security.interfaces.ECPublicKey
    val expected=AlgorithmParameters.getInstance("EC").apply { init(java.security.spec.ECGenParameterSpec("secp256r1")) }.getParameterSpec(java.security.spec.ECParameterSpec::class.java)
    require(key.params.curve==expected.curve && key.params.generator==expected.generator && key.params.order==expected.order && key.params.cofactor==expected.cofactor) { "P-256 key required" }
    val verifier = Signature.getInstance("SHA256withECDSA"); verifier.initVerify(key); verifier.update(bytes)
    require(verifier.verify(signature.unb64())) { "Invalid signature" }
}

fun revision(events: List<Event>): String = events.filter { it.event_type in setOf("observation","answer") }.map { it.event_id }.sorted().joinToString("\n").toByteArray().sha256()

fun validateAssessment(a: Assessment, ids: Set<String>) {
    require(ids.isNotEmpty())
    require(a.observed_facts.size <= 16 && a.uncertain_or_conflicting_claims.size in 1..16)
    (a.observed_facts + a.uncertain_or_conflicting_claims).forEach { f ->
        require(f.text.length in 1..600 && f.supporting_event_ids.size in 1..16 && f.supporting_event_ids.all { it in ids })
    }
    require(a.missing_information.size in 1..8 && a.missing_information.all { it.length in 1..600 } && a.next_question.length in 1..600)
    val p = a.proposed_response
    require(p.action.length in 1..1000 && p.prerequisites.size in 1..8 && p.prerequisites.all { it.length in 1..600 })
    require(p.resource_id in setOf("rescue-team-1","supply-van-1","none"))
    require(p.supporting_event_ids.size in 1..16 && p.supporting_event_ids.all { it in ids })
    require(listOf("route is safe","bridge is safe","building is safe").none { it in p.action.lowercase() }) { "Safety must remain unconfirmed" }
}
