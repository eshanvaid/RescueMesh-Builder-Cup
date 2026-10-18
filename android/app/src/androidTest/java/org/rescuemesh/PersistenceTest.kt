package org.rescuemesh

import androidx.test.core.app.ApplicationProvider
import android.content.Context
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PersistenceTest {
    @Test fun roomRestartRetainsPendingEventsAndSequence() = runBlocking {
        val context=ApplicationProvider.getApplicationContext<Context>(); val dbName="persistence-instrumentation.db"
        context.deleteDatabase(dbName)
        val identity=Identity(); var store=EventStore(context,identity,dbName)
        val first=store.create("observation",EventPayload("instrumentation-only","river-school",text="Synthetic Room restart test"))
        store.db.close(); store=EventStore(context,identity,dbName)
        assertEquals(first.eventB64,store.dao.get(first.id)!!.eventB64)
        assertTrue(store.dao.pending().any { it.id==first.id })
        val second=store.create("observation",EventPayload("instrumentation-only","river-school",text="Synthetic second event"))
        assertEquals(first.sequence+1,second.sequence)
        store.db.close(); context.deleteDatabase(dbName)
    }
}
