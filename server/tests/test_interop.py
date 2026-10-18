import json
from pathlib import Path
from rescuemesh.security import verify
from rescuemesh.models import Envelope

def test_shared_android_signature_vector():
    fixture=json.loads((Path(__file__).resolve().parents[2]/'contracts/signature-test-vector.json').read_text())
    event=verify(Envelope(**fixture['envelope']),fixture['trust'])
    assert 'विद्यालय — café' in event['payload']['text'] and event['origin_sequence']==7
