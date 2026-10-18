#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
adb_path="${ADB:-adb}"
"$adb_path" devices -l
"$adb_path" install -r artifacts/RescueMesh-debug.apk
"$adb_path" shell am start -n org.rescuemesh/.MainActivity
