import base64
import hashlib
import hmac
import json
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from .models import Envelope

def load_json(path: str):
    return json.loads(Path(path).read_text()) if path and Path(path).exists() else {}

def verify(envelope: Envelope, trust: dict):
    raw, sig, event = envelope.decoded()
    if event.event_type == 'approval':
        raise ValueError('only central authenticated approval is allowed')
    encoded = trust.get('devices', {}).get(event.origin_device_id)
    if trust.get('mission_id') != event.mission_id or not encoded:
        raise ValueError('unauthorized origin')
    der = base64.b64decode(encoded, validate=True)
    if hashlib.sha256(der).hexdigest()[:32] != event.origin_device_id:
        raise ValueError('key identity mismatch')
    key = serialization.load_der_public_key(der)
    if not isinstance(key, ec.EllipticCurvePublicKey) or not isinstance(key.curve, ec.SECP256R1):
        raise ValueError('P-256 key required')
    key.verify(sig, raw, ec.ECDSA(hashes.SHA256()))
    return event.model_dump(mode='json')

def token_role(token: str, auth: dict):
    digest = hashlib.sha256(token.encode()).hexdigest()
    for entry in auth.get('tokens', []):
        if hmac.compare_digest(digest, entry['sha256']):
            return entry
    return None
