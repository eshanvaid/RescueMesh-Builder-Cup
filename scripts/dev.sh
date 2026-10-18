#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -d .venv ]]; then python3 -m venv .venv; .venv/bin/pip install -r server/requirements.txt; fi
if [[ ! -f local-demo/auth.json ]]; then .venv/bin/python scripts/seed_demo.py; fi
if [[ ! -d web/node_modules ]]; then npm ci --prefix web; fi
npm run build --prefix web
export RESCUEMESH_LOCAL_AUTH=true
export RESCUEMESH_STORE=sqlite
export RESCUEMESH_DB=local-demo/rescuemesh.db
export RESCUEMESH_TRUST_FILE=local-demo/trust.json
export RESCUEMESH_AUTH_FILE=local-demo/auth.json
exec .venv/bin/uvicorn rescuemesh.main:app --app-dir server --host 127.0.0.1 --port 8080
