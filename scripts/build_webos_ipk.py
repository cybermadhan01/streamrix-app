import os
import shutil
import tarfile
import io
import json
from PIL import Image

def make_webos_ipk():
    app_id = "com.streamrix.app"
    version = "1.0.0"
    
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    webos_dir = os.path.join(project_root, "build", "webos")
    dist_dir = os.path.join(project_root, "dist")
    download_dir = os.path.join(project_root, "download")
    
    if os.path.exists(webos_dir):
        shutil.rmtree(webos_dir)
    os.makedirs(webos_dir, exist_ok=True)
    os.makedirs(dist_dir, exist_ok=True)
    os.makedirs(download_dir, exist_ok=True)

    print("1. Preparing webOS Hosted Shell assets...")
    
    # Generate webOS icons
    src_icon = os.path.join(project_root, "assets", "icons", "icon-192.png")
    if os.path.exists(src_icon):
        im = Image.open(src_icon)
        im.resize((80, 80), Image.Resampling.LANCZOS).save(os.path.join(webos_dir, "icon.png"))
        im.resize((130, 130), Image.Resampling.LANCZOS).save(os.path.join(webos_dir, "largeIcon.png"))
    
    # 2. Write official webOS appinfo.json (Pointing to live streamrix.site/player.html)
    appinfo = {
        "id": app_id,
        "version": version,
        "vendor": "StreamRix",
        "type": "web",
        "main": "https://streamrix.site/player.html",
        "title": "StreamRix",
        "icon": "icon.png",
        "largeIcon": "largeIcon.png",
        "requiredMemory": 64,
        "resolution": "1920x1080",
        "handlesRelaunch": True,
        "supportGpu": True,
        "supportTouch": False,
        "accessibility": {
            "supportsLargeText": True
        }
    }

    with open(os.path.join(webos_dir, "appinfo.json"), "w", encoding="utf-8") as f:
        json.dump(appinfo, f, indent=2)

    print("2. Packaging into webOS .ipk archive...")
    ipk_filename = "streamrix.ipk"
    dist_ipk_path = os.path.join(dist_dir, ipk_filename)
    download_ipk_path = os.path.join(download_dir, ipk_filename)

    debian_binary = b"2.0\n"

    # --- Control File ---
    control_content = f"""Package: {app_id}
Version: {version}
Section: misc
Priority: optional
Architecture: all
Maintainer: StreamRix <noreply@streamrix.site>
Description: StreamRix Sovereign Entertainment for LG webOS TV (Live TV, 4K Cinema, Anime Simulcast)
Installed-Size: 128
""".encode('utf-8')

    control_tar_io = io.BytesIO()
    with tarfile.open(fileobj=control_tar_io, mode='w:gz') as tar:
        ti = tarfile.TarInfo(name='./control')
        ti.size = len(control_content)
        ti.mode = 0o644
        tar.addfile(ti, io.BytesIO(control_content))
    control_tar_bytes = control_tar_io.getvalue()

    # --- Data File ---
    data_tar_io = io.BytesIO()
    with tarfile.open(fileobj=data_tar_io, mode='w:gz') as tar:
        base_prefix = f"./usr/palm/applications/{app_id}"
        for root, dirs, files in os.walk(webos_dir):
            rel_path = os.path.relpath(root, webos_dir)
            if rel_path == '.':
                dest_dir = base_prefix
            else:
                dest_dir = f"{base_prefix}/{rel_path.replace(os.sep, '/')}"
            
            for file in files:
                src_file = os.path.join(root, file)
                dest_file = f"{dest_dir}/{file}"
                tar.add(src_file, arcname=dest_file)

    data_tar_bytes = data_tar_io.getvalue()

    # --- AR Archive Packaging ---
    def ar_header(name, size):
        name_field = f"{name:<16}"
        mtime_field = f"{0:<12}"
        owner_field = f"{0:<6}"
        group_field = f"{0:<6}"
        mode_field = f"{100644:<8}"
        size_field = f"{size:<10}"
        trailer = "`\n"
        return (name_field + mtime_field + owner_field + group_field + mode_field + size_field + trailer).encode('ascii')

    def pad(b):
        return b if len(b) % 2 == 0 else b + b"\n"

    for out_path in [dist_ipk_path, download_ipk_path]:
        with open(out_path, 'wb') as f:
            f.write(b"!<arch>\n")
            f.write(ar_header("debian-binary", len(debian_binary)))
            f.write(pad(debian_binary))
            f.write(ar_header("control.tar.gz", len(control_tar_bytes)))
            f.write(pad(control_tar_bytes))
            f.write(ar_header("data.tar.gz", len(data_tar_bytes)))
            f.write(pad(data_tar_bytes))

        print(f"Generated webOS IPK: {out_path} ({os.path.getsize(out_path)} bytes)")

if __name__ == '__main__':
    make_webos_ipk()
