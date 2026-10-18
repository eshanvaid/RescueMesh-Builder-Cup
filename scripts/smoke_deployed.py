#!/usr/bin/env python3
"""Read-only deployed checks and an unauthenticated write-denial check."""
import argparse
import json
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--url',required=True); args=parser.parse_args()
    parsed=urlparse(args.url)
    if parsed.scheme!='https' or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/'):
        parser.error('--url must be an HTTPS service origin')
    base=args.url.rstrip('/')
    def get(path):
        with urlopen(base+path,timeout=30) as r: return r.read()
    assert b'RescueMesh' in get('/'), 'Dashboard unavailable'
    health=json.loads(get('/api/health')); assert health['status']=='ok' and not health['local_auth'], 'Unsafe or unhealthy deployed configuration'
    assert health['store']=='FirestoreStore', 'Cloud preview must use durable Firestore'
    data=json.loads(get('/api/incidents')); assert len(data['locations'])==3 and len(data['incidents'])>=3, 'Synthetic seed missing'
    try:
        urlopen(Request(base+'/api/incidents/school-01/reassess',data=b'{}',headers={'Content-Type':'application/json'},method='POST'),timeout=30)
    except HTTPError as exc:
        assert exc.code==401, f'Expected 401, received {exc.code}'
    else:
        raise AssertionError('Unauthenticated write was accepted')
    print('PASS: dashboard, health, durable store, seeded incidents and unauthenticated write denial. Model/OAuth/phone acceptance remain separate.')

if __name__=='__main__': main()
