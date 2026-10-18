# Cloud Shell deployment

Deployment is prepared, not executed. A billed Google Cloud project and authorized deployment identity are required. Do not submit a localhost address or an unverified example URL as the prototype link.

## 1. Select a project

Open [Google Cloud Shell](https://shell.cloud.google.com/) in your own Google account. Create/select a project, attach billing and choose the Firestore region carefully: an existing database's location cannot be changed by this script.

```bash
git clone https://github.com/eshanvaid/RescueMesh-Builder-Cup.git
cd RescueMesh-Builder-Cup
export GCP_PROJECT='YOUR_ACTUAL_PROJECT_ID'
export GCP_REGION='us-central1'
gcloud config set project "$GCP_PROJECT"
gcloud billing projects describe "$GCP_PROJECT"
```

The account must be able to enable services, build/deploy Cloud Run, create the runtime identity, grant its scoped IAM roles, create Firestore and provision two Secret Manager secrets. The Cloud Build identity also needs build permissions. Consult [Google's current source-deployment prerequisites](https://docs.cloud.google.com/run/docs/deploying-source-code#required_roles). For the default Compute Engine build identity, an administrator can grant `roles/run.builder` to `PROJECT_NUMBER-compute@developer.gserviceaccount.com` on this project. An organization may select a different build identity; do not guess or grant broad runtime permissions to fix a build failure.

## 2. Deploy the public synthetic preview

```bash
chmod +x scripts/*.sh android/gradlew
./scripts/deploy_demo.sh
```

This generates a private local provisioning bundle, creates the Firestore-backed Cloud Run service, uploads four signed host-generated observations through authenticated HTTPS sync and runs deployed smoke checks. These reports are synthetic, with simulated phone transport and no seeded model assessments. The output's **Prototype URL** is the submission link only after the checks and incognito-browser review pass.

The deployed service uses Firestore, not ephemeral SQLite. Cloud Run's dedicated runtime account receives Datastore/AI roles plus access to two individual secrets. Public reads are allowed; sync, reassessment and approvals remain protected. Local coordinator tokens are rejected on Cloud Run. The script supports one demo deployment/mission per project; use a dedicated project to avoid replacing another deployment's secrets. Keep the generated `local-demo/` bundle private for repeat deployment; do not regenerate it after deployment without planning mission reprovisioning.

The preview alone does not demonstrate real AI reassessment or coordinator approval. Configure the next step before recording those capabilities.

## 3. Enable coordinator login and real Gemini

Create a **Web application** OAuth client in Google Auth Platform / APIs & Services Credentials. Configure the consent screen and authorized test users if required by your account. Add the exact Cloud Run HTTPS origin to **Authorized JavaScript origins**; no trailing route is needed. The app uses Google Identity Services ID tokens, not a redirect-based OAuth flow.

```bash
export GOOGLE_CLIENT_ID='YOUR_WEB_CLIENT_ID.apps.googleusercontent.com'
export COORDINATOR_EMAILS='YOUR_ALLOWLISTED_EMAIL'
export GEMINI_MODEL='gemini-3.8-flash'
./scripts/deploy_demo.sh
```

Only an email-verified ID token with this audience and an allowlisted email can reassess or approve. Gemini uses Application Default Credentials from the runtime service account. Confirm model access in this actual project; the configured model ID being documented does not establish entitlement. No fallback model is selected automatically. If you explicitly choose a different available Google model, record its real identity and use it consistently in configuration and the submission.

To probe locally from Cloud Shell, establish ADC using your own account if absent:

```bash
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT="$GCP_PROJECT"
export GOOGLE_CLOUD_LOCATION='global'
.venv/bin/python scripts/probe_gemini.py
```

## 4. Verify before submitting

```bash
export SERVICE_URL="$(gcloud run services describe rescuemesh --project="$GCP_PROJECT" --region="$GCP_REGION" --format='value(status.url)')"
.venv/bin/python scripts/smoke_deployed.py --url "$SERVICE_URL"
# Repeat the same seed upload: event IDs must not duplicate.
.venv/bin/python scripts/upload_seed.py --url "$SERVICE_URL"
```

Open `SERVICE_URL` in an incognito browser: the page must load without sign-in, show three incidents/four observations and preserve the two conflicting school reports. The conflict preview is explicit claim comparison, not a Gemini result. Sign in with the coordinator account, request a real Gemini reassessment, inspect its citations and prerequisites, and approve only if those prerequisites were actually verified for this synthetic exercise. Do not claim model or approval success if these checks fail. Confirm evidence survives a new service revision and remains available throughout evaluation.

## Operation during evaluation

Keep billing, the service, Firestore, secrets, model access and OAuth test users active. Keep the repository and video public/accessibly shared. Do not shut down or rotate configuration before evaluation finishes. The configuration allows 0–2 instances, concurrency 8, 512 MiB and a 90-second request timeout. These are capacity controls, not a spending cap; set billing alerts and monitor errors/quota. Cloud Build, Artifact Registry, Secret Manager, Firestore and model calls can incur charges.

If organization policy blocks public invocation, contact the project administrator or use an authorized project supporting public access. Do not substitute an authenticated-only URL for the required public prototype without the organizers' agreement.

## Official references

[Cloud Run source deployment](https://docs.cloud.google.com/run/docs/deploying-source-code), [public access](https://docs.cloud.google.com/run/docs/authenticating/public), [Firestore transactions](https://docs.cloud.google.com/firestore/native/docs/manage-data/transactions). This guide and scripts have been checked locally; actual deployment remains pending project access.
