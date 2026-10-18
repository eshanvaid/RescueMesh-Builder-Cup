#!/usr/bin/env python3
"""Host-generated, signed SYNTHETIC observations. No model output, no radio claim."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import uuid
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'server'))
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from rescuemesh.models import MISSION, Envelope
from rescuemesh.security import verify
from rescuemesh.store import SQLiteStore
from rescuemesh import service

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--dir',default='local-demo'); parser.add_argument('--cloud-bootstrap',action='store_true',help='Also export signed observations and gateway-only cloud authentication'); args=parser.parse_args(); target=Path(args.dir); target.mkdir(exist_ok=True)
    if (target/'auth.json').exists():
        raise SystemExit('Existing demo detected; refusing to rotate identities/tokens. Use a fresh --dir or remove local-demo explicitly.')
    keys=[ec.generate_private_key(ec.SECP256R1()) for _ in range(3)]; devices={}; ids=[]
    for key in keys:
        der=key.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo); identity=hashlib.sha256(der).hexdigest()[:32]; devices[identity]=base64.b64encode(der).decode(); ids.append(identity)
    trust={'mission_id':MISSION,'devices':devices}; (target/'trust.json').write_text(json.dumps(trust,indent=2))
    coordinator=secrets.token_urlsafe(32); gateway=secrets.token_urlsafe(32)
    auth={'tokens':[{'sha256':hashlib.sha256(coordinator.encode()).hexdigest(),'role':'coordinator','actor':'local-synthetic-coordinator'},{'sha256':hashlib.sha256(gateway.encode()).hexdigest(),'role':'gateway','device_id':ids[2]}]}
    (target/'auth.json').write_text(json.dumps(auth,indent=2)); (target/'coordinator-token.txt').write_text(coordinator+'\n'); (target/'gateway-token.txt').write_text(gateway+'\n')
    for name in ['auth.json','coordinator-token.txt','gateway-token.txt']: os.chmod(target/name,0o600)
    store=SQLiteStore(str(target/'rescuemesh.db'))
    scenarios=[
        (0,1,'school-01','river-school','Synthetic host seed: six people are waiting on the upper floor of River School. Rising water at the entrance. No injuries reported. A responder reports the north footpath is clear of water from this side; end-to-end route safety is unverified.','north-footpath','passable','reported clear'),
        (1,1,'school-01','river-school','Synthetic host seed: from the east side I see water covering the north footpath; it is blocked. I cannot verify the school entrance or water depth.','north-footpath','passable','blocked'),
        (0,2,'bridge-01','east-bridge','Synthetic host seed: debris beside East Bridge. A resident reports damage to the deck. Structural condition and route safety are unverified.','bridge-deck','condition','reported damaged'),
        (1,2,'clinic-01','hill-clinic','Synthetic host seed: Hill Clinic requests drinking water for twelve people. Access road condition and available supplies are unverified.','clinic','water stock','unknown'),
    ]
    envelopes=[]
    for origin,seq,iid,location,text,subject,predicate,value in scenarios:
        event={'schema_version':1,'event_id':str(uuid.uuid4()),'mission_id':MISSION,'origin_device_id':ids[origin],'origin_sequence':seq,'event_type':'observation','created_at':'2026-10-14T04:00:00Z','referenced_event_ids':[],'payload':{'incident_id':iid,'location_id':location,'text':text,'claims':[{'subject':subject,'predicate':predicate,'value':value}]}}
        raw=json.dumps(event,ensure_ascii=False).encode(); env=Envelope(event_b64=base64.b64encode(raw).decode(),signature_b64=base64.b64encode(keys[origin].sign(raw,ec.ECDSA(hashes.SHA256()))).decode())
        envelopes.append(env.model_dump())
        verified=verify(env,trust); store.mutate(lambda state:service.ingest(state,[verified],[env.model_dump()],ids[2]))
    if args.cloud_bootstrap:
        (target/'cloud-auth.json').write_text(json.dumps({'tokens':[auth['tokens'][1]]},indent=2))
        (target/'seed-events.json').write_text(json.dumps({'events':envelopes}))
        os.chmod(target/'cloud-auth.json',0o600)
        os.chmod(target/'seed-events.json',0o600)
    (target/'transport-disclosure.txt').write_text('Signed observations generated on the host; transport SIMULATED. No local Gemma or Gemini inference ran. No proposals or model outputs seeded.\n')
    print(f'Created {len(scenarios)} signed synthetic observations in {target}. No model output seeded. Coordinator token: {target}/coordinator-token.txt (not printed).')

if __name__=='__main__': main()
