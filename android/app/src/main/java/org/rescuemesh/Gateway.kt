package org.rescuemesh

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

class Gateway(private val store: EventStore) {
    private val client=OkHttpClient.Builder().callTimeout(30,TimeUnit.SECONDS).connectTimeout(10,TimeUnit.SECONDS).build()
    suspend fun sync(base: String, token: String): Int = withContext(Dispatchers.IO) {
        require(base.startsWith("https://")) { "Gateway requires HTTPS. Use scripts/dev-tunnel.sh for a phone on LAN." }
        require(token.isNotBlank()) { "Provision a per-device gateway token" }
        var uploaded=0
        repeat(16) {
            val rows=store.dao.pending()
            if(rows.isEmpty()) return@withContext uploaded
            val body=buildJsonObject { put("events",wire.encodeToJsonElement(rows.map { it.envelope() })) }
            val request=Request.Builder().url(base.trimEnd('/')+"/api/sync").header("Authorization","Bearer $token").post(body.toString().toRequestBody("application/json".toMediaType())).build()
            client.newCall(request).execute().use { response ->
                require(response.isSuccessful) { "Cloud sync ${response.code}: ${response.body?.string()?.take(250)}" }
                val result=wire.parseToJsonElement(response.body!!.string()).jsonObject
                require(result["durable"]?.jsonPrimitive?.boolean == true)
                val ids=result["accepted_event_ids"]!!.jsonArray.map { it.jsonPrimitive.content }
                require(ids.toSet() == rows.map { it.id }.toSet()) { "Invalid server acknowledgement" }
                store.dao.uploaded(ids); uploaded+=ids.size
            }
        }
        uploaded
    }
}
