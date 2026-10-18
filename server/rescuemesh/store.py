"""Same transactional state machine for SQLite and bounded Firestore demo mission."""
import copy
import json
import sqlite3
from pathlib import Path
from .models import MISSION

def initial():
    return {'events': {}, 'proposals': {}, 'approvals': {}, 'assignments': {}, 'receipts': []}

def capacity(state):
    if len(state['events']) > 250 or len(json.dumps(state).encode()) > 750_000:
        raise ValueError('demo mission capacity reached; archive/reset explicitly')

class SQLiteStore:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS missions (id TEXT PRIMARY KEY, state TEXT NOT NULL)')
            db.execute('INSERT OR IGNORE INTO missions VALUES (?,?)', (MISSION, json.dumps(initial())))

    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA synchronous=FULL')
        return db

    def read(self):
        with self.connect() as db:
            return json.loads(db.execute('SELECT state FROM missions WHERE id=?', (MISSION,)).fetchone()[0])

    def mutate(self, fn):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            state = json.loads(db.execute('SELECT state FROM missions WHERE id=?', (MISSION,)).fetchone()[0])
            result = fn(state)
            capacity(state)
            db.execute('UPDATE missions SET state=? WHERE id=?', (json.dumps(state), MISSION))
            return copy.deepcopy(result)

class FirestoreStore:
    def __init__(self, project):
        from google.cloud import firestore
        self.fs = firestore
        self.client = firestore.Client(project=project)
        self.ref = self.client.collection('rescuemesh_missions').document(MISSION)

    def read(self):
        snapshot = self.ref.get(timeout=10)
        return snapshot.to_dict() if snapshot.exists else initial()

    def mutate(self, fn):
        @self.fs.transactional
        def update(tx):
            snapshot = self.ref.get(transaction=tx,timeout=10)
            state = snapshot.to_dict() if snapshot.exists else initial()
            result = fn(state)
            capacity(state)
            tx.set(self.ref, state)
            return result
        return update(self.client.transaction(max_attempts=3))
