#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${GCP_PROJECT:?Set the billed project ID explicitly}"
: "${GCP_REGION:?Set a region explicitly, for example us-central1}"
command -v gcloud >/dev/null
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -r server/requirements.txt
fi
# Generate once; subsequent runs preserve issued identities and token hashes.
if [[ ! -f local-demo/auth.json ]]; then
  .venv/bin/python scripts/seed_demo.py --cloud-bootstrap
fi
if [[ ! -f local-demo/cloud-auth.json || ! -f local-demo/seed-events.json ]]; then
  printf '%s\n' 'Existing local-demo lacks the cloud bundle. Back it up and use a fresh clone/directory; do not rotate an already deployed mission silently.' >&2
  exit 1
fi
export TRUST_FILE="$PWD/local-demo/trust.json"
export AUTH_FILE="$PWD/local-demo/cloud-auth.json"
./scripts/deploy.sh
url=$(gcloud run services describe "${RESCUEMESH_SERVICE:-rescuemesh}" --project="$GCP_PROJECT" --region="$GCP_REGION" --format='value(status.url)')
.venv/bin/python scripts/upload_seed.py --url "$url"
.venv/bin/python scripts/smoke_deployed.py --url "$url"
printf '\nPrototype URL: %s\n' "$url"
printf '%s\n' 'Host-generated signed synthetic reports uploaded. No phone relay or model inference is implied.'
