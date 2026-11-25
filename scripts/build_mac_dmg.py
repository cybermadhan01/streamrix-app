import os
import shutil
import zipfile
import pycdlib

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
DOWNLOAD_DIR = os.path.join(PROJECT_ROOT, "download")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build", "mac")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

TARGET_URL = "https://streamrix.site/player.html"

def prepare_dirs():
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(DIST_DIR, exist_ok=True)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def build_mac_app():
    print("[>] Assembling StreamRix.app bundle for macOS...")
    app_dir = os.path.join(BUILD_DIR, "StreamRix.app")
    contents_dir = os.path.join(app_dir, "Contents")
    macos_dir = os.path.join(contents_dir, "MacOS")
    res_dir = os.path.join(contents_dir, "Resources")

    os.makedirs(macos_dir, exist_ok=True)
    os.makedirs(res_dir, exist_ok=True)

    # 1. Info.plist
    info_plist = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>StreamRix</string>
    <key>CFBundleDisplayName</key>
    <string>StreamRix</string>
    <key>CFBundleIdentifier</key>
    <string>com.streamrix.app</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleExecutable</key>
    <string>StreamRix</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSAllowsArbitraryLoads</key>
        <true/>
    </dict>
</dict>
</plist>"""
    with open(os.path.join(contents_dir, "Info.plist"), "w", encoding="utf-8") as f:
        f.write(info_plist)

    # 2. Executable launcher script (StreamRix)
    launcher_sh = r"""#!/bin/bash
TARGET_URL="__TARGET_URL__"

# 1. Automatically ensure Desktop shortcut exists on macOS Desktop
DESKTOP_PATH="$HOME/Desktop/StreamRix.app"
CURRENT_APP="$(cd "$(dirname "$0")/../.." && pwd)"
if [ ! -e "$DESKTOP_PATH" ] && [ ! -L "$DESKTOP_PATH" ]; then
    ln -s "$CURRENT_APP" "$DESKTOP_PATH" 2>/dev/null || osascript -e "tell application \"Finder\" to make alias file to (POSIX file \"$CURRENT_APP\") at desktop" 2>/dev/null || true
fi

# 2. Native macOS Cocoa WebKit Player (100% Native StreamRix Dock Icon, Zero Browser Switch)
osascript -l JavaScript <<'EOF'
ObjC.import('Cocoa');
ObjC.import('WebKit');

try {
    var app = $.NSApplication.sharedApplication;
    app.setActivationPolicy($.NSApplicationActivationPolicyRegular);

    var rect = $.NSMakeRect(100, 100, 1280, 720);
    var mask = $.NSWindowStyleMaskTitled | $.NSWindowStyleMaskClosable | $.NSWindowStyleMaskMiniaturizable | $.NSWindowStyleMaskResizable;
    var window = $.NSWindow.alloc.initWithContentRectStyleMaskBackingDefer(rect, mask, $.NSBackingStoreBuffered, false);
    window.setTitle("StreamRix");
    window.center;

    var config = $.WKWebViewConfiguration.alloc.init;
    var webView = $.WKWebView.alloc.initWithFrameConfiguration(window.contentView.bounds, config);
    webView.autoresizingMask = $.NSViewWidthSizable | $.NSViewHeightSizable;
    window.contentView.addSubview(webView);

    var url = $.NSURL.URLWithString("__TARGET_URL__");
    var req = $.NSURLRequest.requestWithURL(url);
    webView.loadRequest(req);

    window.makeKeyAndOrderFront(null);
    app.activateIgnoringOtherApps(true);
    app.run;
} catch (e) {
    $.exit(1);
}
EOF

# 3. Fallback to isolated cinema shell window
if [ $? -ne 0 ]; then
    PROFILE_DIR="$HOME/Library/Application Support/StreamRix/Profile"
    mkdir -p "$PROFILE_DIR"
    FLAGS="--app=__TARGET_URL__ --user-data-dir=$PROFILE_DIR --window-size=1280,720 --enable-features=OverlayScrollbar,VaapiVideoDecoder"

    if [ -d "/Applications/Google Chrome.app" ]; then
        exec "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" $FLAGS
    elif [ -d "/Applications/Brave Browser.app" ]; then
        exec "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser" $FLAGS
    elif [ -d "/Applications/Microsoft Edge.app" ]; then
        exec "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge" $FLAGS
    else
        open "__TARGET_URL__"
    fi
fi
""".replace("__TARGET_URL__", TARGET_URL)
    launcher_file = os.path.join(macos_dir, "StreamRix")
    with open(launcher_file, "w", encoding="utf-8", newline="\n") as f:
        f.write(launcher_sh)

    # 3. Copy AppIcon.icns
    icns_src = os.path.join(ASSETS_DIR, "icons", "AppIcon.icns")
    if os.path.exists(icns_src):
        shutil.copy2(icns_src, os.path.join(res_dir, "AppIcon.icns"))

    # 4. Copy Offline Fallback & Branding into Resources
    offline_dst = os.path.join(res_dir, "offline")
    os.makedirs(offline_dst, exist_ok=True)
    offline_src = os.path.join(ASSETS_DIR, "offline")
    if os.path.exists(offline_src):
        for f in os.listdir(offline_src):
            shutil.copy2(os.path.join(offline_src, f), os.path.join(offline_dst, f))

    branding_dst = os.path.join(res_dir, "branding")
    os.makedirs(branding_dst, exist_ok=True)
    branding_src = os.path.join(ASSETS_DIR, "branding")
    if os.path.exists(branding_src):
        for f in os.listdir(branding_src):
            shutil.copy2(os.path.join(branding_src, f), os.path.join(branding_dst, f))

    images_dst = os.path.join(res_dir, "images")
    os.makedirs(images_dst, exist_ok=True)
    images_src = os.path.join(ASSETS_DIR, "images")
    if os.path.exists(images_src):
        for f in os.listdir(images_src):
            if f.endswith((".png", ".jpg", ".webp")):
                shutil.copy2(os.path.join(images_src, f), os.path.join(images_dst, f))

    print(f"[✓] StreamRix.app bundle built.")
    return app_dir

def build_dmg(app_dir):
    print("[>] Building StreamRix.dmg disk image...")
    dmg_path = os.path.join(DIST_DIR, "StreamRix.dmg")
    website_dmg = os.path.join(DOWNLOAD_DIR, "StreamRix.dmg")

    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60', vol_ident='StreamRix')

    base_dir = BUILD_DIR
    for root, dirs, files in os.walk(app_dir):
        rel_root = os.path.relpath(root, base_dir)
        udf_dir = "/" + rel_root.replace("\\", "/")
        if udf_dir != "/":
            iso.add_directory(udf_path=udf_dir)
        for f in files:
            src_file = os.path.join(root, f)
            rel_file = os.path.relpath(src_file, base_dir)
            udf_path = "/" + rel_file.replace("\\", "/")
            iso.add_file(src_file, udf_path=udf_path)

    readme_path = os.path.join(BUILD_DIR, "INSTALL_INSTRUCTIONS.txt")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("StreamRix for macOS\n\nTo install, drag StreamRix.app into your /Applications folder.\nLaunch StreamRix to enjoy sovereign high-definition streaming.\n")
    iso.add_file(readme_path, udf_path="/INSTALL_INSTRUCTIONS.txt")

    iso.write(dmg_path)
    iso.close()

    shutil.copy2(dmg_path, website_dmg)
    size_mb = os.path.getsize(dmg_path) / (1024 * 1024)
    print(f"[✓] StreamRix.dmg disk image built ({size_mb:.2f} MB)")
    return dmg_path

def build_mac_zip(app_dir):
    print("[>] Packaging StreamRix-Mac.zip...")
    zip_path = os.path.join(DIST_DIR, "StreamRix-Mac.zip")
    website_zip = os.path.join(DOWNLOAD_DIR, "StreamRix-Mac.zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(app_dir):
            for f in files:
                p = os.path.join(root, f)
                arcname = os.path.relpath(p, BUILD_DIR).replace("\\", "/")
                z.write(p, arcname)

    shutil.copy2(zip_path, website_zip)
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"[✓] StreamRix-Mac.zip bundle built ({size_mb:.2f} MB)")
    return zip_path

def main():
    prepare_dirs()
    app = build_mac_app()
    build_dmg(app)
    build_mac_zip(app)

if __name__ == "__main__":
    main()
