"""The cloud bootstrap must not accidentally enable local coordinator tokens."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from rescuemesh.models import Envelope
from rescuemesh.security import verify
from rescuemesh.store import SQLiteStore
from rescuemesh import service


def test_cloud_bundle_is_gateway_only_and_preserves_signed_sources(tmp_path):
    script=Path(__file__).resolve().parents[2]/'scripts/seed_demo.py'
    target=tmp_path/'mission'
    subprocess.run([sys.executable,str(script),'--dir',str(target),'--cloud-bootstrap'],check=True,capture_output=True,text=True)
    auth=json.loads((target/'cloud-auth.json').read_text())
    trust=json.loads((target/'trust.json').read_text())
    batch=json.loads((target/'seed-events.json').read_text())
    gateway=(target/'gateway-token.txt').read_text().strip()
    coordinator=(target/'coordinator-token.txt').read_text().strip()
    assert len(auth['tokens'])==1
    assert auth['tokens'][0]['role']=='gateway'
    assert auth['tokens'][0]['sha256']==hashlib.sha256(gateway.encode()).hexdigest()
    assert auth['tokens'][0]['sha256']!=hashlib.sha256(coordinator.encode()).hexdigest()
    assert len(batch['events'])==4
    verified=[verify(Envelope.model_validate(e),trust) for e in batch['events']]
    store=SQLiteStore(str(tmp_path/'receiver.db'))
    for _ in range(2):
        store.mutate(lambda state:service.ingest(state,verified,batch['events'],auth['tokens'][0]['device_id']))
    incidents=service.incidents(store.read())
    assert len(incidents)==3
    assert sum(len(i['evidence']) for i in incidents)==4
    assert sum(len(i['conflicts']) for i in incidents)==1
    assert all(not i['proposals'] for i in incidents)
