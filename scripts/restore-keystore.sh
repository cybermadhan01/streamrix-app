#!/usr/bin/env bash
# Keeps the APK signing fingerprint identical across every CI run.
# Add repository secret ANDROID_KEYSTORE_B64 (base64 of the .keystore file).
set -euo pipefail

if [ -z "${ANDROID_KEYSTORE_B64:-}" ]; then
  echo "[info] No ANDROID_KEYSTORE_B64 secret - build script will generate a keystore."
  exit 0
fi

mkdir -p certs
printf '%s' "$ANDROID_KEYSTORE_B64" | base64 --decode > certs/streamrix-release.keystore
echo "[ok] Signing keystore restored."
