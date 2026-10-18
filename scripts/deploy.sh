#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${GCP_PROJECT:?Set GCP_PROJECT to the designated project}"
: "${GCP_REGION:?Set GCP_REGION, for example us-central1}"
# Public browsing can be deployed before coordinator OAuth is configured.
export GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID:-}"
export COORDINATOR_EMAILS="${COORDINATOR_EMAILS:-}"
if [[ -n "$GOOGLE_CLIENT_ID" && -z "$COORDINATOR_EMAILS" ]] || [[ -z "$GOOGLE_CLIENT_ID" && -n "$COORDINATOR_EMAILS" ]]; then
  printf '%s\n' 'Set GOOGLE_CLIENT_ID and COORDINATOR_EMAILS together, or leave both empty for public read-only access.' >&2
  exit 1
fi
: "${TRUST_FILE:?Set TRUST_FILE to the authorized phones trust.json}"
: "${AUTH_FILE:?Set AUTH_FILE to gateway-only auth.json}"
command -v gcloud >/dev/null
# Refuse local coordinator credentials in the deployed authentication secret.
python3 - "$AUTH_FILE" <<'PY'
import json,sys
data=json.load(open(sys.argv[1])); assert data['tokens'] and all(t['role']=='gateway' for t in data['tokens']), 'Cloud auth.json must contain gateway tokens only'
PY
service="${RESCUEMESH_SERVICE:-rescuemesh}"
runtime="rescuemesh-runtime@${GCP_PROJECT}.iam.gserviceaccount.com"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com firestore.googleapis.com aiplatform.googleapis.com secretmanager.googleapis.com --project="$GCP_PROJECT"
if ! gcloud iam service-accounts describe "$runtime" --project="$GCP_PROJECT" >/dev/null 2>&1; then
  gcloud iam service-accounts create rescuemesh-runtime --display-name="RescueMesh bounded demo runtime" --project="$GCP_PROJECT"
fi
for role in roles/datastore.user roles/aiplatform.user; do
  gcloud projects add-iam-policy-binding "$GCP_PROJECT" --member="serviceAccount:$runtime" --role="$role" --condition=None >/dev/null
done
# Provision Firestore Native in the chosen immutable region only if not already present.
if ! gcloud firestore databases describe --database='(default)' --project="$GCP_PROJECT" >/dev/null 2>&1; then
  gcloud firestore databases create --database='(default)' --location="$GCP_REGION" --type=firestore-native --project="$GCP_PROJECT"
fi
for name in trust auth; do
  if ! gcloud secrets describe "rescuemesh-$name" --project="$GCP_PROJECT" >/dev/null 2>&1; then
    gcloud secrets create "rescuemesh-$name" --replication-policy=automatic --project="$GCP_PROJECT"
  fi
  if [[ "$name" == trust ]]; then source_file="$TRUST_FILE"; else source_file="$AUTH_FILE"; fi
  gcloud secrets versions add "rescuemesh-$name" --data-file="$source_file" --project="$GCP_PROJECT" >/dev/null
  gcloud secrets add-iam-policy-binding "rescuemesh-$name" --member="serviceAccount:$runtime" --role=roles/secretmanager.secretAccessor --project="$GCP_PROJECT" >/dev/null
done
# YAML avoids comma parsing in coordinator email lists; only non-secret config is included.
config_file=$(mktemp)
trap 'rm -f "$config_file"' EXIT
GCP_PROJECT="$GCP_PROJECT" GOOGLE_CLIENT_ID="$GOOGLE_CLIENT_ID" COORDINATOR_EMAILS="$COORDINATOR_EMAILS" python3 - "$config_file" <<'PY'
import json,os,sys
# JSON is valid YAML; no credentials are included here.
values={'GOOGLE_CLOUD_PROJECT':os.environ['GCP_PROJECT'],'GOOGLE_CLOUD_LOCATION':'global','GEMINI_MODEL':os.getenv('GEMINI_MODEL','gemini-3.8-flash'),'GOOGLE_CLIENT_ID':os.environ['GOOGLE_CLIENT_ID'],'COORDINATOR_EMAILS':os.environ['COORDINATOR_EMAILS'],'RESCUEMESH_STORE':'firestore','RESCUEMESH_LOCAL_AUTH':'false','RESCUEMESH_TRUST_FILE':'/secrets/trust/manifest.json','RESCUEMESH_AUTH_FILE':'/secrets/auth/gateways.json'}
json.dump(values,open(sys.argv[1],'w'))
PY
gcloud run deploy "$service" --source=. --project="$GCP_PROJECT" --region="$GCP_REGION" --service-account="$runtime" --allow-unauthenticated --min-instances=0 --max-instances=2 --concurrency=8 --cpu=1 --memory=512Mi --timeout=90 --env-vars-file="$config_file" --set-secrets="/secrets/trust/manifest.json=rescuemesh-trust:latest,/secrets/auth/gateways.json=rescuemesh-auth:latest" --quiet
url=$(gcloud run services describe "$service" --project="$GCP_PROJECT" --region="$GCP_REGION" --format='value(status.url)')
curl --fail --silent --show-error "$url/api/health"
curl --fail --silent --show-error "$url/api/incidents" >/dev/null
printf '\nDashboard: %s\nAdd this origin to the OAuth web client before coordinator login.\n' "$url"
