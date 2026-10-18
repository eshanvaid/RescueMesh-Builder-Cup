package org.rescuemesh

import org.junit.Assert.*
import org.junit.Test
import kotlinx.serialization.json.*
import kotlinx.serialization.encodeToString

class ContractTest {
    @Test fun maximumSizeEventsSplitToFitTransportByteLimit() {
        val envelope=Envelope(ByteArray(12288).b64(),ByteArray(72).b64())
        val packets=eventPackets(listOf(envelope,envelope))
        assertEquals(2,packets.size)
        assertTrue(packets.all { wire.encodeToString(it).toByteArray().size<=30000 && it.events.size<=2 })
    }
    private fun fixture(): Pair<Envelope,Trust> {
        val root=wire.parseToJsonElement(javaClass.classLoader!!.getResourceAsStream("signature-test-vector.json")!!.bufferedReader().readText()).jsonObject
        return wire.decodeFromJsonElement<Envelope>(root["envelope"]!!) to wire.decodeFromJsonElement<Trust>(root["trust"]!!)
    }
    @Test fun verifiesPythonSignatureOverOriginalUnicodeBytes() {
        val (e,t)=fixture(); val event=verifyEnvelope(e,t)
        assertTrue(event.payload.text!!.contains("विद्यालय — café")); assertEquals(7L,event.origin_sequence)
    }
    @Test fun reserializedBytesFailSignatureVerification() {
        val (e,t)=fixture(); val normalized=wire.parseToJsonElement(e.event_b64.unb64().toString(Charsets.UTF_8)).toString().toByteArray().b64()
        assertThrows(Exception::class.java) { verifyEnvelope(e.copy(event_b64=normalized),t) }
    }
    @Test fun unenrolledDeviceRejected() {
        val (e,t)=fixture(); assertThrows(Exception::class.java) { verifyEnvelope(e,t.copy(devices=emptyMap())) }
    }
    @Test fun invalidSignatureRejected() {
        val (e,t)=fixture(); assertThrows(Exception::class.java) { verifyEnvelope(e.copy(signature_b64=ByteArray(70).b64()),t) }
    }
    @Test fun duplicateKeysRejected() {
        val (e,_)=fixture(); val raw=e.event_b64.unb64().toString(Charsets.UTF_8).replace("\"schema_version\": 1","\"schema_version\": 1, \"schema_version\": 1")
        assertThrows(Exception::class.java) { parseEvent(raw.toByteArray()) }
    }
    @Test fun approvalCannotBeCreatedOffline() {
        val (e,_)=fixture(); val raw=e.event_b64.unb64().toString(Charsets.UTF_8).replace("\"observation\"","\"approval\"")
        assertThrows(Exception::class.java) { parseEvent(raw.toByteArray()) }
    }
    @Test fun revisionIsOrderIndependentButIncludesSequenceGaps() {
        val (e,t)=fixture(); val one=verifyEnvelope(e,t); val two=one.copy(event_id="00000000-0000-4000-8000-000000000002",origin_sequence=1)
        assertEquals(revision(listOf(one,two)),revision(listOf(two,one))); assertNotEquals(revision(listOf(one)),revision(listOf(one,two)))
    }
    @Test fun unknownCitationAndResourceRejected() {
        val id="00000000-0000-4000-8000-000000000001"
        val valid=Assessment(listOf(Fact("Reported people",listOf(id))),listOf(Fact("Access unknown",listOf(id))),listOf("Access"),"What is the water depth?",Response("Stage supplies for review",listOf("Human verifies access"),"none",listOf(id)))
        validateAssessment(valid,setOf(id))
        assertThrows(Exception::class.java) { validateAssessment(valid,setOf("different-id")) }
        assertThrows(Exception::class.java) { validateAssessment(valid.copy(proposed_response=valid.proposed_response.copy(resource_id="arbitrary-resource")),setOf(id)) }
    }
}
