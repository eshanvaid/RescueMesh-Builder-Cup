#!/usr/bin/env python3
"""Upload signed synthetic observations through the real authenticated sync API."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--dir', default='local-demo')
    args = parser.parse_args()
    parsed = urlparse(args.url)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
        parser.error('--url must be an HTTPS service origin without credentials, path or query')
    target = Path(args.dir)
    body = (target / 'seed-events.json').read_bytes()
    token = (target / 'gateway-token.txt').read_text().strip()
    req = Request(args.url.rstrip('/') + '/api/sync', data=body, method='POST', headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    try:
        with urlopen(req, timeout=60) as response:
            result = json.load(response)
    except HTTPError as exc:
        raise SystemExit(f'Seed upload failed: HTTP {exc.code}; credentials were not printed.') from None
    print(json.dumps({'synthetic_host_upload': True, 'transport': 'host HTTPS, not Nearby', 'result': result}, indent=2))

if __name__ == '__main__':
    main()
