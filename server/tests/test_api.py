import hashlib
import pytest
from fastapi.testclient import TestClient
from rescuemesh.main import create_app
from rescuemesh.models import validate_assessment
from rescuemesh import service, ai
from test_events import ingest

@pytest.fixture
def api(rig,monkeypatch):
    monkeypatch.setenv('RESCUEMESH_LOCAL_AUTH','true'); monkeypatch.delenv('K_SERVICE',raising=False); monkeypatch.delenv('GOOGLE_CLOUD_PROJECT',raising=False)
    auth={'tokens':[{'sha256':hashlib.sha256(b'gateway-test').hexdigest(),'role':'gateway','device_id':rig['device']},{'sha256':hashlib.sha256(b'coord-test').hexdigest(),'role':'coordinator','actor':'test-coordinator'}]}
    return TestClient(create_app(rig['store'],rig['trust'],auth))

def test_public_read_authenticated_writes(api,rig):
    assert api.get('/api/incidents').status_code==200
    assert api.post('/api/sync',json={'events':[rig['make']().model_dump()]}).status_code==401
    assert api.post('/api/incidents/no/reassess',headers={'Authorization':'Bearer gateway-test'}).status_code==403
    assert api.post('/api/sync',json={'events':[rig['make']().model_dump()]},headers={'Authorization':'Bearer coord-test'}).status_code==403

def test_repeated_cloud_uploads(api,rig):
    payload={'events':[rig['make']().model_dump()]}; headers={'Authorization':'Bearer gateway-test'}
    for _ in range(3):
        response=api.post('/api/sync',json=payload,headers=headers)
        assert response.status_code==200 and response.json()['durable'] is True
    g=api.get('/api/incidents').json()['incidents'][0]
    assert len(g['evidence'])==1

def test_api_invalid_signature_and_device_approval(api,rig):
    e=rig['make'](); e.signature_b64='eA=='
    assert api.post('/api/sync',json={'events':[e.model_dump()]},headers={'Authorization':'Bearer gateway-test'}).status_code==422
    approval=rig['make'](event_type='approval')
    assert api.post('/api/sync',json={'events':[approval.model_dump()]},headers={'Authorization':'Bearer gateway-test'}).status_code==422

def test_missing_inference_honest_failure(api,rig):
    ingest(rig,rig['make']())
    response=api.post('/api/incidents/test-incident/reassess',headers={'Authorization':'Bearer coord-test'})
    assert response.status_code==503 and 'evidence retained' in response.json()['detail']
    assert not rig['store'].read()['proposals']

def test_api_approval_authenticated_and_prerequisites(api,rig):
    ingest(rig,rig['make']()); g=service.incidents(rig['store'].read())[0]
    p=rig['store'].mutate(lambda s:service.save_proposal(s,g['id'],g['evidence_revision'],rig['assessment']([g['evidence'][0]['event_id']]),'schema test fixture','none'))
    path=f"/api/proposals/{p['id']}/approve"; body={'evidence_revision':p['evidence_revision'],'prerequisites_confirmed':True}
    assert api.post(path,json=body).status_code==401
    assert api.post(path,json=body,headers={'Authorization':'Bearer gateway-test'}).status_code==403
    assert api.post(path,json=dict(body,prerequisites_confirmed=False),headers={'Authorization':'Bearer coord-test'}).status_code==422
    for _ in range(2): assert api.post(path,json=body,headers={'Authorization':'Bearer coord-test'}).status_code==200
    assert len(rig['store'].read()['approvals'])==1
    assert rig['store'].read()['central_signer'] not in api.get('/api/incidents').text

def test_no_local_coordinator_on_cloud_run(rig,monkeypatch):
    monkeypatch.setenv('RESCUEMESH_LOCAL_AUTH','true'); monkeypatch.setenv('K_SERVICE','rescuemesh')
    auth={'tokens':[{'sha256':hashlib.sha256(b'coord').hexdigest(),'role':'coordinator'}]}
    api=TestClient(create_app(rig['store'],rig['trust'],auth))
    assert api.get('/api/health').json()['local_auth'] is False
    assert api.post('/api/incidents/x/reassess',headers={'Authorization':'Bearer coord'}).status_code==401

def test_hallucinated_citation_rejected(rig):
    a=rig['assessment'](['00000000-0000-4000-8000-000000000001'])
    with pytest.raises(ValueError,match='unknown'): validate_assessment(a,[{'event_id':'00000000-0000-4000-8000-000000000002'}])

def test_batch_body_bound(api):
    assert api.post('/api/sync',content=b'x'*512001).status_code==413

def test_bounded_ai_repair_and_citations(rig,monkeypatch):
    import asyncio
    from types import SimpleNamespace
    ingest(rig,rig['make']()); evidence=service.incidents(rig['store'].read())[0]['evidence']; calls=[]
    valid=rig['assessment']([evidence[0]['event_id']])
    async def generate(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(text='invalid JSON' if len(calls)==1 else valid.model_dump_json())
    async def close(): pass
    fake=SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate),aclose=close))
    monkeypatch.setattr(ai,'client',lambda:fake)
    result,model=asyncio.run(ai.reassess(evidence))
    assert result==valid and len(calls)==2
    assert 'untrusted' in calls[0]['config'].system_instruction
    assert model=='gemini-3.8-flash'
