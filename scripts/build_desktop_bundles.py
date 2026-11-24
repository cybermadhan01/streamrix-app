import os
import zipfile
import tarfile
import shutil

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
DOWNLOAD_DIR = os.path.join(PROJECT_ROOT, "download")

os.makedirs(DIST_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def build_mac():
    mac_app_dir = os.path.join(PROJECT_ROOT, "build", "mac", "StreamRix.app", "Contents")
    os.makedirs(os.path.join(mac_app_dir, "MacOS"), exist_ok=True)
    os.makedirs(os.path.join(mac_app_dir, "Resources"), exist_ok=True)

    info_plist = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>StreamRix</string>
    <key>CFBundleIdentifier</key>
    <string>com.streamrix.app</string>
    <key>CFBundleName</key>
    <string>StreamRix</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>"""

    with open(os.path.join(mac_app_dir, "Info.plist"), "w", encoding="utf-8") as f:
        f.write(info_plist)

    mac_launcher = """#!/bin/bash
TARGET_URL="https://streamrix.site/player.html"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BRAVE="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
EDGE="/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"

if [ -f "$CHROME" ]; then
    exec "$CHROME" --app="$TARGET_URL" --window-size=1280,720
elif [ -f "$BRAVE" ]; then
    exec "$BRAVE" --app="$TARGET_URL" --window-size=1280,720
elif [ -f "$EDGE" ]; then
    exec "$EDGE" --app="$TARGET_URL" --window-size=1280,720
else
    open "$TARGET_URL"
fi
"""
    mac_bin = os.path.join(mac_app_dir, "MacOS", "StreamRix")
    with open(mac_bin, "w", encoding="utf-8", newline="\n") as f:
        f.write(mac_launcher)

    mac_zip = os.path.join(DIST_DIR, "StreamRix-Mac.zip")
    with zipfile.ZipFile(mac_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(os.path.join(PROJECT_ROOT, "build", "mac", "StreamRix.app")):
            for file in files:
                p = os.path.join(root, file)
                arcname = os.path.relpath(p, os.path.join(PROJECT_ROOT, "build", "mac"))
                z.write(p, arcname)

    shutil.copy2(mac_zip, os.path.join(DOWNLOAD_DIR, "StreamRix-Mac.zip"))
    print(f"[✓] macOS application bundle created: {mac_zip}")

def build_linux():
    linux_dir = os.path.join(PROJECT_ROOT, "build", "linux")
    os.makedirs(linux_dir, exist_ok=True)
    
    linux_sh = """#!/bin/bash
TARGET_URL="https://streamrix.site/player.html"

if command -v google-chrome &> /dev/null; then
    exec google-chrome --app="$TARGET_URL" --window-size=1280,720
elif command -v chromium &> /dev/null; then
    exec chromium --app="$TARGET_URL" --window-size=1280,720
elif command -v brave-browser &> /dev/null; then
    exec brave-browser --app="$TARGET_URL" --window-size=1280,720
elif command -v microsoft-edge &> /dev/null; then
    exec microsoft-edge --app="$TARGET_URL" --window-size=1280,720
else
    xdg-open "$TARGET_URL"
fi
"""
    with open(os.path.join(linux_dir, "streamrix.sh"), "w", encoding="utf-8", newline="\n") as f:
        f.write(linux_sh)

    desktop_entry = """[Desktop Entry]
Name=StreamRix
Comment=StreamRix Sovereign Entertainment
Exec=bash -c "$(dirname %k)/streamrix.sh"
Icon=streamrix
Terminal=false
Type=Application
Categories=AudioVideo;Video;Player;
"""
    with open(os.path.join(linux_dir, "streamrix.desktop"), "w", encoding="utf-8", newline="\n") as f:
        f.write(desktop_entry)

    linux_tar = os.path.join(DIST_DIR, "StreamRix-Linux.tar.gz")
    with tarfile.open(linux_tar, "w:gz") as tar:
        tar.add(os.path.join(linux_dir, "streamrix.sh"), arcname="StreamRix/streamrix.sh")
        tar.add(os.path.join(linux_dir, "streamrix.desktop"), arcname="StreamRix/streamrix.desktop")

    shutil.copy2(linux_tar, os.path.join(DOWNLOAD_DIR, "StreamRix-Linux.tar.gz"))
    print(f"[✓] Linux desktop bundle created: {linux_tar}")

if __name__ == "__main__":
    build_mac()
    build_linux()
