import os
import io
import time
import shutil
import tarfile

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
DOWNLOAD_DIR = os.path.join(PROJECT_ROOT, "download")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build", "linux")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

TARGET_URL = "https://streamrix.site/player.html"

def prepare_dirs():
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(DIST_DIR, exist_ok=True)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def write_ar_archive(out_path, files):
    """Writes a standard Unix AR archive (used by Debian .deb packages)."""
    with open(out_path, "wb") as ar:
        ar.write(b"!<arch>\n")
        for filename, data in files:
            name_str = f"{filename:<16}"
            mtime_str = f"{int(time.time()):<12}"
            uid_str = f"{0:<6}"
            gid_str = f"{0:<6}"
            mode_str = f"{'100644':<8}"
            size_str = f"{len(data):<10}"
            header = f"{name_str}{mtime_str}{uid_str}{gid_str}{mode_str}{size_str}`\n".encode("ascii")
            ar.write(header)
            ar.write(data)
            if len(data) % 2 != 0:
                ar.write(b"\n")

def build_deb():
    print("[>] Building streamrix.deb Debian/Ubuntu package...")
    
    deb_binary = b"2.0\n"

    control_content = """Package: streamrix
Version: 1.0.0
Architecture: amd64
Maintainer: StreamRix <streamrix@proton.me>
Installed-Size: 18432
Section: video
Priority: optional
Homepage: https://streamrix.site
Description: StreamRix Sovereign Entertainment Client
 StreamRix is an ultra-clean, hardware-accelerated sovereign entertainment client.
 Features live 4K/FHD streaming, TV remote navigation, and desktop integration.
"""
    control_io = io.BytesIO()
    with tarfile.open(fileobj=control_io, mode="w:gz") as tar:
        ti = tarfile.TarInfo("control")
        ti.size = len(control_content.encode("utf-8"))
        ti.mode = 0o644
        ti.mtime = int(time.time())
        tar.addfile(ti, io.BytesIO(control_content.encode("utf-8")))
    control_tar_gz = control_io.getvalue()

    launcher_sh = f"""#!/bin/bash
TARGET_URL="{TARGET_URL}"

# 1. Automatically ensure Desktop shortcut & App menu entry exist
APPS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPS_DIR"
if [ -f "/usr/share/applications/streamrix.desktop" ] && [ ! -f "$APPS_DIR/streamrix.desktop" ]; then
    cp /usr/share/applications/streamrix.desktop "$APPS_DIR/" 2>/dev/null || true
    chmod +x "$APPS_DIR/streamrix.desktop" 2>/dev/null || true
fi

DESKTOP_DIR="${{XDG_DESKTOP_DIR:-$HOME/Desktop}}"
if [ -d "$DESKTOP_DIR" ] && [ ! -f "$DESKTOP_DIR/streamrix.desktop" ]; then
    cp /usr/share/applications/streamrix.desktop "$DESKTOP_DIR/" 2>/dev/null || true
    chmod +x "$DESKTOP_DIR/streamrix.desktop" 2>/dev/null || true
fi

# 2. Try native GTK WebKit player first (100% native window, zero browser process, permanent StreamRix dock icon)
if command -v python3 &> /dev/null; then
    python3 -c "
import sys
try:
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('WebKit2', '4.0')
    from gi.repository import Gtk, WebKit2
    
    win = Gtk.Window(title='StreamRix')
    win.set_wmclass('streamrix', 'streamrix')
    win.set_role('streamrix-player')
    win.set_default_size(1280, 720)
    win.connect('destroy', Gtk.main_quit)
    try:
        win.set_icon_from_file('/usr/share/pixmaps/streamrix.png')
    except: pass
    
    view = WebKit2.WebView()
    s = view.get_settings()
    s.set_enable_developer_extras(False)
    s.set_enable_media_stream(True)
    s.set_enable_mediasource(True)
    view.load_uri('$TARGET_URL')
    
    win.add(view)
    win.show_all()
    Gtk.main()
    sys.exit(0)
except Exception:
    sys.exit(1)
" && exit 0
fi

# 3. Fallback to isolated cinema shell window
# 3. Try native GTK WebKit player first (100% native window, zero browser process, permanent StreamRix dock icon)
if command -v python3 &> /dev/null; then
    python3 -c "
import sys
try:
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('WebKit2', '4.0')
    from gi.repository import Gtk, WebKit2
    
    win = Gtk.Window(title='StreamRix')
    win.set_wmclass('streamrix', 'streamrix')
    win.set_role('streamrix-player')
    win.set_default_size(1280, 720)
    win.connect('destroy', Gtk.main_quit)
    try:
        win.set_icon_from_file('$HERE/streamrix.png')
    except: pass
    
    view = WebKit2.WebView()
    s = view.get_settings()
    s.set_enable_developer_extras(False)
    s.set_enable_media_stream(True)
    s.set_enable_mediasource(True)
    view.load_uri('$TARGET_URL')
    
    win.add(view)
    win.show_all()
    Gtk.main()
    sys.exit(0)
except Exception:
    sys.exit(1)
" && exit 0
fi

PROFILE_DIR="$HOME/.config/streamrix/profile"
mkdir -p "$PROFILE_DIR"
FLAGS="--app=$TARGET_URL --class=streamrix --name=streamrix --user-data-dir=$PROFILE_DIR --window-size=1280,720 --enable-features=OverlayScrollbar,VaapiVideoDecoder"

if command -v google-chrome &> /dev/null; then
    exec google-chrome $FLAGS
elif command -v chromium-browser &> /dev/null; then
    exec chromium-browser $FLAGS
elif command -v chromium &> /dev/null; then
    exec chromium $FLAGS
elif command -v brave-browser &> /dev/null; then
    exec brave-browser $FLAGS
elif command -v microsoft-edge &> /dev/null; then
    exec microsoft-edge $FLAGS
else
    xdg-open "$TARGET_URL"
fi
"""

    desktop_entry = """[Desktop Entry]
Version=1.0
Name=StreamRix
Comment=StreamRix - Stream Movies, Anime & Live TV Effortlessly
GenericName=Streaming Media Player
Exec=/usr/bin/streamrix %U
Icon=/usr/share/pixmaps/streamrix.png
Terminal=false
Type=Application
Categories=AudioVideo;Video;Player;TV;
Keywords=streaming;movies;tv;live;anime;cinema;
StartupWMClass=streamrix
X-GNOME-WM-Class=streamrix
StartupNotify=true
"""

    icon_512_path = os.path.join(ASSETS_DIR, "icons", "icon-512.png")
    if not os.path.exists(icon_512_path):
        # Minimal valid 1x1 PNG so CI never fails on a missing source asset.
        import base64
        icon_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg=="
        )
    else:
        with open(icon_512_path, "rb") as f:
            icon_bytes = f.read()

    data_io = io.BytesIO()
    with tarfile.open(fileobj=data_io, mode="w:gz") as tar:
        for d in ["usr", "usr/bin", "usr/share", "usr/share/applications", "usr/share/pixmaps", "usr/share/icons", "usr/share/icons/hicolor", "usr/share/icons/hicolor/512x512", "usr/share/icons/hicolor/512x512/apps", "opt", "opt/streamrix"]:
            ti = tarfile.TarInfo(d)
            ti.type = tarfile.DIRTYPE
            ti.mode = 0o755
            ti.mtime = int(time.time())
            tar.addfile(ti)

        ti = tarfile.TarInfo("usr/bin/streamrix")
        ti.size = len(launcher_sh.encode("utf-8"))
        ti.mode = 0o755
        ti.mtime = int(time.time())
        tar.addfile(ti, io.BytesIO(launcher_sh.encode("utf-8")))

        ti = tarfile.TarInfo("usr/share/applications/streamrix.desktop")
        ti.size = len(desktop_entry.encode("utf-8"))
        ti.mode = 0o644
        ti.mtime = int(time.time())
        tar.addfile(ti, io.BytesIO(desktop_entry.encode("utf-8")))

        ti = tarfile.TarInfo("usr/share/pixmaps/streamrix.png")
        ti.size = len(icon_bytes)
        ti.mode = 0o644
        ti.mtime = int(time.time())
        tar.addfile(ti, io.BytesIO(icon_bytes))

        ti = tarfile.TarInfo("usr/share/icons/hicolor/512x512/apps/streamrix.png")
        ti.size = len(icon_bytes)
        ti.mode = 0o644
        ti.mtime = int(time.time())
        tar.addfile(ti, io.BytesIO(icon_bytes))

        # Bundle branding, offline shell, and images into /opt/streamrix/
        for folder_name in ["offline", "branding", "images"]:
            f_dir = os.path.join(ASSETS_DIR, folder_name)
            if os.path.exists(f_dir):
                target_base = f"opt/streamrix/{folder_name}"
                ti = tarfile.TarInfo(target_base)
                ti.type = tarfile.DIRTYPE
                ti.mode = 0o755
                ti.mtime = int(time.time())
                tar.addfile(ti)
                for item in os.listdir(f_dir):
                    item_path = os.path.join(f_dir, item)
                    if os.path.isfile(item_path):
                        with open(item_path, "rb") as fl:
                            fl_bytes = fl.read()
                        ti = tarfile.TarInfo(f"{target_base}/{item}")
                        ti.size = len(fl_bytes)
                        ti.mode = 0o644
                        ti.mtime = int(time.time())
                        tar.addfile(ti, io.BytesIO(fl_bytes))

    data_tar_gz = data_io.getvalue()

    deb_path = os.path.join(DIST_DIR, "streamrix.deb")
    website_deb = os.path.join(DOWNLOAD_DIR, "streamrix.deb")

    write_ar_archive(deb_path, [
        ("debian-binary", deb_binary),
        ("control.tar.gz", control_tar_gz),
        ("data.tar.gz", data_tar_gz)
    ])

    shutil.copy2(deb_path, website_deb)
    size_mb = os.path.getsize(deb_path) / (1024 * 1024)
    print(f"[✓] streamrix.deb package built ({size_mb:.2f} MB)")
    return deb_path

def build_appimage():
    print("[>] Building StreamRix.AppImage universal package...")
    
    appdir = os.path.join(BUILD_DIR, "AppDir")
    os.makedirs(appdir, exist_ok=True)

    apprun_sh = f"""#!/bin/bash
HERE="$(dirname "$(readlink -f "${{0}}")")"
TARGET_URL="{TARGET_URL}"

# 1. Automatically register icon in user icon theme
ICON_DIR="$HOME/.local/share/icons/hicolor/512x512/apps"
mkdir -p "$ICON_DIR"
cp "$HERE/streamrix.png" "$ICON_DIR/streamrix.png" 2>/dev/null || true

# 2. Automatically register desktop entry in applications menu
APPS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPS_DIR"
cat <<EOF > "$APPS_DIR/streamrix.desktop"
[Desktop Entry]
Name=StreamRix
Comment=StreamRix - Stream Movies, Anime & Live TV Effortlessly
Exec="$HERE/AppRun"
Icon=streamrix
Terminal=false
Type=Application
Categories=AudioVideo;Video;Player;TV;
StartupWMClass=streamrix
EOF
chmod +x "$APPS_DIR/streamrix.desktop" 2>/dev/null || true

# 3. Automatically create Desktop shortcut on user desktop
DESKTOP_DIR="${{XDG_DESKTOP_DIR:-$HOME/Desktop}}"
if [ -d "$DESKTOP_DIR" ] && [ ! -f "$DESKTOP_DIR/StreamRix.desktop" ]; then
    cp "$APPS_DIR/streamrix.desktop" "$DESKTOP_DIR/StreamRix.desktop" 2>/dev/null || true
    chmod +x "$DESKTOP_DIR/StreamRix.desktop" 2>/dev/null || true
fi

# 3. Try native GTK WebKit player first (100% native window, zero browser process, permanent StreamRix dock icon)
if command -v python3 &> /dev/null; then
    python3 -c "
import sys
try:
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('WebKit2', '4.0')
    from gi.repository import Gtk, WebKit2
    
    win = Gtk.Window(title='StreamRix')
    win.set_wmclass('streamrix', 'streamrix')
    win.set_role('streamrix-player')
    win.set_default_size(1280, 720)
    win.connect('destroy', Gtk.main_quit)
    try:
        win.set_icon_from_file('$HERE/streamrix.png')
    except: pass
    
    view = WebKit2.WebView()
    s = view.get_settings()
    s.set_enable_developer_extras(False)
    s.set_enable_media_stream(True)
    s.set_enable_mediasource(True)
    view.load_uri('$TARGET_URL')
    
    win.add(view)
    win.show_all()
    Gtk.main()
    sys.exit(0)
except Exception:
    sys.exit(1)
" && exit 0
fi

PROFILE_DIR="$HOME/.config/streamrix/profile"
mkdir -p "$PROFILE_DIR"
FLAGS="--app=$TARGET_URL --class=streamrix --name=streamrix --user-data-dir=$PROFILE_DIR --window-size=1280,720 --enable-features=OverlayScrollbar,VaapiVideoDecoder"

if command -v google-chrome &> /dev/null; then
    exec google-chrome $FLAGS
elif command -v chromium-browser &> /dev/null; then
    exec chromium-browser $FLAGS
elif command -v chromium &> /dev/null; then
    exec chromium $FLAGS
elif command -v brave-browser &> /dev/null; then
    exec brave-browser $FLAGS
elif command -v microsoft-edge &> /dev/null; then
    exec microsoft-edge $FLAGS
else
    xdg-open "$TARGET_URL"
fi
"""
    with open(os.path.join(appdir, "AppRun"), "w", encoding="utf-8", newline="\n") as f:
        f.write(apprun_sh)

    desktop_entry = """[Desktop Entry]
Name=StreamRix
Comment=StreamRix - Stream Movies, Anime & Live TV Effortlessly
Exec=AppRun
Icon=streamrix
Terminal=false
Type=Application
Categories=AudioVideo;Video;Player;TV;
StartupWMClass=streamrix
"""
    with open(os.path.join(appdir, "streamrix.desktop"), "w", encoding="utf-8", newline="\n") as f:
        f.write(desktop_entry)

    icon_src = os.path.join(ASSETS_DIR, "icons", "icon-512.png")
    icon_dst = os.path.join(appdir, "streamrix.png")
    if os.path.exists(icon_src):
        shutil.copy2(icon_src, icon_dst)
    else:
        from PIL import Image
        img = Image.new("RGBA", (512, 512), color=(0, 173, 239, 255))
        img.save(icon_dst)

    appdir_assets = os.path.join(appdir, "assets")
    os.makedirs(appdir_assets, exist_ok=True)
    for folder in ["offline", "branding", "images"]:
        src_f = os.path.join(ASSETS_DIR, folder)
        dst_f = os.path.join(appdir_assets, folder)
        if os.path.exists(src_f):
            shutil.copytree(src_f, dst_f, dirs_exist_ok=True)

    appimage_tar = os.path.join(BUILD_DIR, "appdir.tar.gz")
    with tarfile.open(appimage_tar, "w:gz") as tar:
        for item in os.listdir(appdir):
            p = os.path.join(appdir, item)
            tar.add(p, arcname=item)

    with open(appimage_tar, "rb") as f:
        payload_data = f.read()

    runner_script = b"""#!/bin/sh
# StreamRix Standalone AppImage Runner
set -e
TMPDIR="${TMPDIR:-/tmp}/.streamrix_run_$$"
mkdir -p "$TMPDIR"
trap 'rm -rf "$TMPDIR"' EXIT INT TERM
ARCHIVE=$(awk '/^__ARCHIVE_FOLLOWS__/ {print NR + 1; exit 0; }' "$0")
tail -n+"$ARCHIVE" "$0" | tar -xz -C "$TMPDIR"
chmod +x "$TMPDIR/AppRun"
exec "$TMPDIR/AppRun" "$@"
exit 0
__ARCHIVE_FOLLOWS__
"""
    appimage_path = os.path.join(DIST_DIR, "StreamRix.AppImage")
    website_appimage = os.path.join(DOWNLOAD_DIR, "StreamRix.AppImage")

    with open(appimage_path, "wb") as f:
        f.write(runner_script)
        f.write(payload_data)

    shutil.copy2(appimage_path, website_appimage)
    size_mb = os.path.getsize(appimage_path) / (1024 * 1024)
    print(f"[✓] StreamRix.AppImage built ({size_mb:.2f} MB)")
    return appimage_path

def build_linux_tar():
    print("[>] Packaging StreamRix-Linux.tar.gz...")
    tar_path = os.path.join(DIST_DIR, "StreamRix-Linux.tar.gz")
    website_tar = os.path.join(DOWNLOAD_DIR, "StreamRix-Linux.tar.gz")

    appdir = os.path.join(BUILD_DIR, "AppDir")
    with tarfile.open(tar_path, "w:gz") as tar:
        for item in os.listdir(appdir):
            p = os.path.join(appdir, item)
            tar.add(p, arcname=f"StreamRix/{item}")

    shutil.copy2(tar_path, website_tar)
    size_mb = os.path.getsize(tar_path) / (1024 * 1024)
    print(f"[✓] StreamRix-Linux.tar.gz built ({size_mb:.2f} MB)")
    return tar_path

def main():
    prepare_dirs()
    build_deb()
    build_appimage()
    build_linux_tar()

if __name__ == "__main__":
    main()
