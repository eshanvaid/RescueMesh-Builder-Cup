#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python -m pytest -q
npm run build --prefix web
android/gradlew -p android :app:testDebugUnitTest :app:assembleDebug :app:lintDebug
