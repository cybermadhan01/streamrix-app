#!/usr/bin/env bash
# Branding is pulled from the LIVE site so no application source or media needs
# to be stored in this build-only repository.
set -uo pipefail

mkdir -p assets/icons assets/branding assets/offline assets/images

fetch() {
  local url="$1" out="$2"
  if curl -fsSL --max-time 30 "$url" -o "$out"; then
    echo "[ok] $out"
  else
    rm -f "$out"
    echo "[skip] $out (not available on live site)"
    return 1
  fi
}

fetch "https://streamrix.site/assets/icons/icon-512.png" "assets/icons/icon-512.png"
fetch "https://streamrix.site/assets/icons/streamrix-icon.png" "assets/icons/streamrix-icon.png"
fetch "https://streamrix.site/assets/icons/AppIcon.icns" "assets/icons/AppIcon.icns"
fetch "https://streamrix.site/favicon_clean.ico" "favicon_clean.ico"

if ! fetch "https://streamrix.site/STREAMRIX-LOGO.png" "STREAMRIX-LOGO.png"; then
  if fetch "https://streamrix.site/STREAMRIX-LOGO.webp" "STREAMRIX-LOGO.webp"; then
    python3 -c "from PIL import Image; Image.open('STREAMRIX-LOGO.webp').convert('RGBA').save('STREAMRIX-LOGO.png')"
  fi
fi

exit 0
