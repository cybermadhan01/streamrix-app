#!/usr/bin/env bash
set -euo pipefail

expected=(
  "StreamRix-Setup.exe"
  "StreamRix.exe"
  "streamrix.apk"
  "streamrix.ipk"
  "StreamRix.dmg"
  "StreamRix-Mac.zip"
  "streamrix.deb"
  "StreamRix.AppImage"
  "StreamRix-Linux.tar.gz"
)

missing=0
cd artifacts
for f in "${expected[@]}"; do
  if [ ! -s "$f" ]; then
    echo "::error::Missing or empty artifact: $f"
    missing=1
  else
    printf '%-28s %10s bytes\n' "$f" "$(stat -c%s "$f")"
  fi
done

if [ "$missing" -ne 0 ]; then
  echo "::error::One or more platform builds produced no artifact."
  exit 1
fi

echo "[ok] All platform artifacts verified."
