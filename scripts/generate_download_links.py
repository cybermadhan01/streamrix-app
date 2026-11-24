#!/usr/bin/env python3
"""Generate the single JSON manifest that every page of streamrix.site reads.

Stable URLs use GitHub's `releases/latest/download/<file>` endpoint, so a new
CI build instantly becomes the newest download without editing any HTML.
"""
import datetime
import hashlib
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ARTIFACTS = os.path.join(ROOT, "artifacts")
REPO = os.environ.get("GITHUB_REPOSITORY", "cybermadhan01/streamrix-app")
BASE = f"https://github.com/{REPO}/releases/latest/download/"
TAG = os.environ.get("RELEASE_TAG") or ""

FILES = [
    ("windows",         "StreamRix-Setup.exe",     "Windows installer",        "Windows"),
    ("windowsPortable", "StreamRix.exe",           "Windows portable app",     "Windows portable"),
    ("android",         "streamrix.apk",           "Android / phone / tablet", "Android"),
    ("tv",              "streamrix.apk",           "Android TV / Fire TV",     "Smart TV"),
    ("webos",           "streamrix.ipk",           "LG webOS TV",              "webOS TV"),
    ("mac",             "StreamRix.dmg",           "macOS disk image",         "macOS"),
    ("macZip",          "StreamRix-Mac.zip",       "macOS app bundle",         "macOS (ZIP)"),
    ("linux",           "streamrix.deb",           "Debian / Ubuntu package",  "Linux (DEB)"),
    ("linuxAppImage",   "StreamRix.AppImage",      "Universal Linux AppImage", "Linux (AppImage)"),
    ("linuxTar",        "StreamRix-Linux.tar.gz",  "Portable Linux tarball",   "Linux (tar.gz)"),
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    links = {}
    for key, filename, label, title in FILES:
        path = os.path.join(ARTIFACTS, filename)
        entry = {
            "url": BASE + filename,
            "file": filename,
            "label": label,
            "title": title,
        }
        if os.path.exists(path):
            entry["size"] = os.path.getsize(path)
            entry["sha256"] = sha256(path)
        links[key] = entry

    payload = {
        "generatedAt": datetime.datetime.now(datetime.timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "version": TAG or os.environ.get("GITHUB_RUN_NUMBER", ""),
        "releaseUrl": f"https://github.com/{REPO}/releases/latest",
        "baseUrl": BASE,
        "files": links,
    }

    out = os.path.join(ROOT, "download-links.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"[ok] Wrote {out}")


if __name__ == "__main__":
    main()
