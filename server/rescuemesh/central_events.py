"""Central approval origins persist with mission state; never returned by public APIs."""
import base64
import hashlib
import json
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from .models import Event, Payload, Claim, MISSION

def approval_event(state, approval, proposal, location_id, created_at, event_id):
    # SQLite is private local development storage; Firestore protects this document through IAM.
    # A production signing service/Secret Manager key lifecycle is beyond this bounded demo.
    if not state.get('central_signer'):
        key=ec.generate_private_key(ec.SECP256R1())
        state['central_signer']=base64.b64encode(key.private_bytes(serialization.Encoding.DER,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())).decode()
        state['central_sequence']=0
    key=serialization.load_der_private_key(base64.b64decode(state['central_signer']),password=None)
    public=key.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)
    origin=hashlib.sha256(public).hexdigest()[:32]
    state['central_sequence']+=1
    event=Event(schema_version=1,event_id=event_id,mission_id=MISSION,origin_device_id=origin,origin_sequence=state['central_sequence'],event_type='approval',created_at=created_at,referenced_event_ids=proposal['assessment']['proposed_response']['supporting_event_ids'],payload=Payload(incident_id=approval['incident_id'],location_id=location_id,text=f"Authenticated coordinator {approval['actor']} approved proposal {proposal['id']}; prerequisites confirmed. Resource: {approval['resource_id']}.",claims=[Claim(subject=approval['resource_id'],predicate='assigned_to',value=approval['incident_id'])],provider='authenticated human coordinator',evidence_revision=approval['evidence_revision']))
    data=event.model_dump(mode='json'); raw=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode()
    if len(raw)>12288: raise ValueError('approval event exceeds bound')
    signature=key.sign(raw,ec.ECDSA(hashes.SHA256()))
    return {'event':data,'envelope':{'event_b64':base64.b64encode(raw).decode(),'signature_b64':base64.b64encode(signature).decode()},'origin_public_key':base64.b64encode(public).decode(),'received_at':created_at,'gateway_device_id':origin,'provenance':'central authenticated approval'}
