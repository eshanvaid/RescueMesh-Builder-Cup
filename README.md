# RescueMesh

**Double Descent · Google AI Builder Cup · Team lead: Eshan Vaid**

RescueMesh helps responders preserve incident evidence when internet access is unavailable. One Android application combines observer, relay and gateway roles. A web dashboard brings original reports, contradictions, proposed responses and human approvals into one view. All example data is synthetic.

## Prototype status

The Android APK compiles, and the backend/dashboard run locally. Automated tests cover signed event ingestion, duplicate and out-of-order delivery, persistence, conflicting evidence and transactional approval safeguards. Physical Gemma inference, Nearby radio transfers, live Firestore/Gemini and Cloud Run deployment remain unverified. Integration code is present; these are separate acceptance gates.

The local preview contains four host-generated, signed observations across River School, East Bridge and Hill Clinic. **Transport is simulated; no model output is seeded.** Explicit structured claims reveal the demonstrated conflict without AI inference. Google Gemini calls require project access and authenticated coordinator login; failures are shown without fabricated output.

## Run locally

Requires Python 3.11+, Node 22+ and npm.

```bash
python3 -m venv .venv
.venv/bin/pip install -r server/requirements.txt
npm ci --prefix web
./scripts/dev.sh
```

Open http://localhost:8080. Public reads need no login. For local coordinator access, use the generated token in `local-demo/coordinator-token.txt`; never publish that file. Environment files are not loaded automatically: export the settings you need from `.env.example`.

## Android

Use JDK 21, Android SDK Platform 35 and Build Tools 35.0.0. The wrapper pins Gradle 8.11.1; the build pins AGP 8.9.2, Kotlin 2.4.0, Nearby 19.5.1 and LiteRT-LM 0.18.0.

```bash
python3 scripts/bootstrap_android.py
./android/gradlew -p android :app:testDebugUnitTest :app:assembleDebug :app:lintDebug
./scripts/install_apk.sh
```

Alternatively, install the SDK in Android Studio and set `ANDROID_HOME` or `android/local.properties`. The APK requires Android 8/API 26 or newer. CI publishes a debug APK under **RescueMesh-debug-APK**. Download/import the exact CPU Gemma artifact specified in [model-artifacts.json](contracts/model-artifacts.json); weights are not bundled. Model-free devices can store and relay events. Hardware setup and honest result capture are documented in [device testing](docs/device-test.md).

## Google services

| Service | Role | Current verification |
|---|---|---|
| Google Gemma + LiteRT-LM | Offline structured assessment, evidence citations and follow-up questions | Android integration compiles; device inference pending |
| Nearby Connections | Foreground authenticated peer exchange | Compiles; physical radio acceptance pending |
| Cloud Run | One container serves FastAPI and React | Container previously tested in CI; deployment pending |
| Firestore Native | Durable mission events, projections, proposals and approval transactions | Adapter implemented; live-cloud test pending |
| Gemini through Google Gen AI SDK | Reassess combined evidence and draft responses | Integration implemented; real model call pending |
| Google Identity Services | Allowlisted coordinator login | Integration implemented; deployed OAuth test pending |
| Secret Manager | Runtime trust manifest and gateway token hashes | Deployment configuration prepared |

Firestore is part of the Firebase ecosystem; this prototype does **not** use Firebase Hosting, Firebase Authentication or Firebase AI Logic.

## Deploy on Google Cloud

Follow [the Cloud Shell deployment guide](docs/deployment.md). A billed project is required. The deployment script provisions a dedicated runtime identity and bounded scaling; the public preview can be deployed before coordinator OAuth is configured. [Google source references](docs/sources.md) identify the SDKs and APIs used.

## Validate

```bash
.venv/bin/python -m pytest -q
npm run build --prefix web
./android/gradlew -p android :app:testDebugUnitTest :app:assembleDebug :app:lintDebug
# Requires a connected device or emulator:
./android/gradlew -p android :app:connectedDebugAndroidTest
```

See [validation](docs/validation.md), [architecture](docs/architecture.md), [event contract](contracts/README.md) and the separate [model evaluation set](evals/README.md).

## Boundaries

One mission, three locations, 250 events/750 KiB cloud state, two assignable resources and 24 source events per inference. Nearby encrypts each connection; relays can read payloads. A model proposes; a human approves. No autonomous dispatch, medical triage, route safety certification, background mesh, iOS or voice. Photo inference is deferred until the text runtime passes physical testing.

Public visibility is not a license grant. Third-party SDKs and model weights retain their own terms; review [dependency notices](docs/dependencies.md).
