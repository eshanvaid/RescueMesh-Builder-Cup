import base64
import hashlib
import json
import uuid
import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from rescuemesh.models import MISSION, Envelope, Assessment
from rescuemesh.store import SQLiteStore

@pytest.fixture
def rig(tmp_path):
    key = ec.generate_private_key(ec.SECP256R1())
    der = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    device = hashlib.sha256(der).hexdigest()[:32]
    trust = {'mission_id': MISSION, 'devices': {device: base64.b64encode(der).decode()}}
    def make(seq=1, text='Synthetic: people waiting, access unknown.', value='unknown', incident='test-incident', event_type='observation', raw=None):
        event = {'schema_version': 1, 'event_id': str(uuid.uuid4()), 'mission_id': MISSION, 'origin_device_id': device, 'origin_sequence': seq, 'event_type': event_type, 'created_at': '2026-10-14T04:00:00Z', 'referenced_event_ids': [], 'payload': {'incident_id': incident, 'location_id': 'river-school', 'text': text, 'claims': [{'subject': 'access', 'predicate': 'passable', 'value': value}]}}
        b = raw if raw is not None else json.dumps(event, ensure_ascii=False, indent=1).encode()
        return Envelope(event_b64=base64.b64encode(b).decode(), signature_b64=base64.b64encode(key.sign(b, ec.ECDSA(hashes.SHA256()))).decode())
    def assessment(ids, resource='rescue-team-1'):
        # Schema/approval test fixture authored by tests; NOT a model output or showcased scenario.
        return Assessment.model_validate({'observed_facts': [{'text': 'Reported presence of people', 'supporting_event_ids': ids}], 'uncertain_or_conflicting_claims': [{'text': 'Access is unverified', 'supporting_event_ids': ids}], 'missing_information': ['Route condition'], 'next_question': 'Can you report water depth from your current safe position?', 'proposed_response': {'action': 'Stage a team while access is verified by responders.', 'prerequisites': ['Coordinator confirms route condition'], 'resource_id': resource, 'supporting_event_ids': ids}})
    return {'key': key, 'device': device, 'trust': trust, 'make': make, 'assessment': assessment, 'store': SQLiteStore(str(tmp_path/'state.db'))}
