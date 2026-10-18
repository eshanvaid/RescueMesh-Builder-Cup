#!/usr/bin/env python3
"""Combine Android exported public identities; mint per-device API sync credentials."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from rescuemesh.models import MISSION
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
import base64

p=argparse.ArgumentParser(); p.add_argument('identities',nargs='+'); p.add_argument('--out',default='local-demo/phones'); args=p.parse_args(); out=Path(args.out)
if out.exists(): raise SystemExit('Output already exists; choose a fresh directory to avoid invalidating trust/tokens.')
devices={}
for file in args.identities:
    identity=json.loads(Path(file).read_text()); assert identity['mission_id']==MISSION
    for did,pub in identity['devices'].items():
        raw=base64.b64decode(pub,validate=True); assert hashlib.sha256(raw).hexdigest()[:32]==did
        key=serialization.load_der_public_key(raw); assert isinstance(key,ec.EllipticCurvePublicKey) and isinstance(key.curve,ec.SECP256R1)
        devices[did]=pub
out.mkdir(parents=True); (out/'trust.json').write_text(json.dumps({'mission_id':MISSION,'devices':devices},indent=2)); tokens=[]
for did in devices:
    token=secrets.token_urlsafe(32); tokens.append({'sha256':hashlib.sha256(token.encode()).hexdigest(),'role':'gateway','device_id':did})
    path=out/f'{did}-sync-token.txt'; path.write_text(token+'\n'); os.chmod(path,0o600)
(out/'auth.json').write_text(json.dumps({'tokens':tokens},indent=2)); os.chmod(out/'auth.json',0o600)
print(f'Provisioned {len(devices)} phones. Import {out}/trust.json on ALL phones. Keep auth.json on the backend only; issue each phone its own token.')
