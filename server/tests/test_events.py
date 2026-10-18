import base64
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from rescuemesh.security import verify
from rescuemesh import service
from rescuemesh.models import Envelope
from rescuemesh.store import SQLiteStore

def ingest(rig, envelope, store=None):
    event=verify(envelope,rig['trust']); store=store or rig['store']
    return store.mutate(lambda s:service.ingest(s,[event],[envelope.model_dump()],rig['device']))

def test_duplicate_out_of_order_and_gaps(rig):
    late=rig['make'](seq=10); early=rig['make'](seq=1)
    ingest(rig,late); ingest(rig,late); ingest(rig,early)
    state=rig['store'].read()
    assert len(state['events'])==2 and len(state['receipts'])==2
    assert {r['event']['origin_sequence'] for r in state['events'].values()}=={1,10}

def test_restart_pending_and_three_store_forward_simulation(rig,tmp_path):
    # SIMULATED transport only: separate persistent stores, real signature verification.
    a=SQLiteStore(str(tmp_path/'A.db')); b=SQLiteStore(str(tmp_path/'B.db')); c=SQLiteStore(str(tmp_path/'C.db'))
    e=rig['make'](); ingest(rig,e,a)
    # Disconnect/crash before ACK: B commits first, then loses process/connection.
    ingest(rig,e,b); b=SQLiteStore(str(tmp_path/'B.db'))
    assert len(b.read()['events'])==1
    missing=set(b.read()['events'])-set(c.read()['events'])
    for eid in missing: ingest(rig,Envelope(**b.read()['events'][eid]['envelope']),c)
    ingest(rig,e,b); ingest(rig,e,c)
    assert len(c.read()['events'])==1

def test_invalid_signature_and_unenrolled_origin(rig):
    e=rig['make']; bad=e(); bad.signature_b64=base64.b64encode(b'x'*70).decode()
    with pytest.raises(Exception): verify(bad,rig['trust'])
    with pytest.raises(ValueError,match='unauthorized'): verify(e(),{'mission_id':'synthetic-flood-01','devices':{}})
    assert not rig['store'].read()['events']

def test_signed_original_bytes_and_tampering(rig):
    e=rig['make'](text='Synthetic: विद्यालय — café')
    assert verify(e,rig['trust'])['payload']['text'].endswith('café')
    data=json.loads(base64.b64decode(e.event_b64)); rebuilt=json.dumps(data,separators=(',',':')).encode()
    e.event_b64=base64.b64encode(rebuilt).decode()
    with pytest.raises(Exception): verify(e,rig['trust'])

def test_sequence_collision_rolls_back_batch(rig):
    one,two=rig['make'](1),rig['make'](1)
    v=[verify(x,rig['trust']) for x in [one,two]]
    with pytest.raises(ValueError,match='sequence collision'):
        rig['store'].mutate(lambda s:service.ingest(s,v,[one.model_dump(),two.model_dump()],rig['device']))
    assert not rig['store'].read()['events']

def test_conflicting_evidence_stays_visible(rig):
    for n,v in enumerate(['yes','no'],1): ingest(rig,rig['make'](seq=n,value=v))
    g=service.incidents(rig['store'].read())[0]
    assert len(g['evidence'])==2 and len(g['conflicts'])==1
    assert set(g['conflicts'][0]['values'])=={'yes','no'}

def test_unknown_then_specific_claim_is_not_a_contradiction(rig):
    for n,v in enumerate(['unknown','no'],1): ingest(rig,rig['make'](seq=n,value=v))
    g=service.incidents(rig['store'].read())[0]
    assert len(g['evidence'])==2 and g['conflicts']==[]

def test_stale_approval_rejected(rig):
    ingest(rig,rig['make']())
    g=service.incidents(rig['store'].read())[0]
    a=rig['assessment']([e['event_id'] for e in g['evidence']])
    p=rig['store'].mutate(lambda s:service.save_proposal(s,g['id'],g['evidence_revision'],a,'schema test fixture','not a model'))
    ingest(rig,rig['make'](seq=2,value='no'))
    with pytest.raises(ValueError,match='stale'):
        rig['store'].mutate(lambda s:service.approve(s,p['id'],p['evidence_revision'],'test-coordinator'))
    assert not rig['store'].read()['assignments']

def test_concurrent_resource_assignment_transaction(rig):
    proposals=[]
    for n in range(2):
        ingest(rig,rig['make'](seq=n+1,incident=f'incident-{n}'))
        g=next(g for g in service.incidents(rig['store'].read()) if g['id']==f'incident-{n}')
        a=rig['assessment']([e['event_id'] for e in g['evidence']])
        proposals.append(rig['store'].mutate(lambda s:service.save_proposal(s,g['id'],g['evidence_revision'],a,'schema test fixture','none')))
    def attempt(p):
        try: rig['store'].mutate(lambda s:service.approve(s,p['id'],p['evidence_revision'],'coordinator')); return True
        except ValueError: return False
    with ThreadPoolExecutor(max_workers=2) as pool: outcomes=list(pool.map(attempt,proposals))
    assert sum(outcomes)==1 and len(rig['store'].read()['assignments'])==1

def test_evidence_changed_while_model_running(rig):
    ingest(rig,rig['make']()); g=service.incidents(rig['store'].read())[0]
    ingest(rig,rig['make'](seq=2,value='no'))
    with pytest.raises(ValueError,match='changed during inference'):
        rig['store'].mutate(lambda s:service.save_proposal(s,g['id'],g['evidence_revision'],rig['assessment']([g['evidence'][0]['event_id']]),'fixture','none'))

def test_central_approval_is_signed_event_and_identity_survives_restart(rig):
    from cryptography.hazmat.primitives import hashes,serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    ingest(rig,rig['make']()); g=service.incidents(rig['store'].read())[0]
    p=rig['store'].mutate(lambda s:service.save_proposal(s,g['id'],g['evidence_revision'],rig['assessment']([g['evidence'][0]['event_id']]),'schema test fixture','none'))
    a=rig['store'].mutate(lambda s:service.approve(s,p['id'],p['evidence_revision'],'test-coordinator'))
    reopened=SQLiteStore(rig['store'].path); state=reopened.read(); record=state['events'][a['approval_event_id']]
    raw=base64.b64decode(record['envelope']['event_b64']); key=serialization.load_der_public_key(base64.b64decode(record['origin_public_key']))
    key.verify(base64.b64decode(record['envelope']['signature_b64']),raw,ec.ECDSA(hashes.SHA256()))
    assert json.loads(raw)['event_type']=='approval'
    assert state['central_signer']==rig['store'].read()['central_signer']
    assert reopened.mutate(lambda s:service.approve(s,p['id'],p['evidence_revision'],'test-coordinator'))==a
    assert len([r for r in state['events'].values() if r['event']['event_type']=='approval'])==1

def test_reject_duplicate_json_keys(rig):
    raw=base64.b64decode(rig['make']().event_b64).replace(b'"schema_version": 1',b'"schema_version": 1, "schema_version": 1')
    with pytest.raises(ValueError,match='duplicate JSON key'): verify(rig['make'](raw=raw),rig['trust'])
