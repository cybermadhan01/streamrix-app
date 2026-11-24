# StreamRix — build-only release repository

**This repository is not a source-code repository.**

It exists for one purpose: run GitHub Actions to build the StreamRix apps for
every supported platform and publish the binaries as GitHub Releases.

## Rules

| What | Allowed? |
| --- | --- |
| Application source code committed here | ❌ Never |
| Developers pushing to `main` | ❌ Blocked by branch protection |
| Manual **Actions → Build All Platforms → Run workflow** | ✅ Yes |
| Automatic trigger from the private source repository | ✅ Yes (`workflow_dispatch` via API) |
| GitHub Actions bot publishing releases / `download-links.json` | ✅ Yes (the only writer) |

## What gets built

| Platform | Artifact |
| --- | --- |
| Windows | `StreamRix-Setup.exe`, `StreamRix.exe` |
| Android phone / tablet | `streamrix.apk` |
| Android TV / Fire TV | `streamrix.apk` |
| LG webOS TV | `streamrix.ipk` |
| macOS | `StreamRix.dmg`, `StreamRix-Mac.zip` |
| Linux | `streamrix.deb`, `StreamRix.AppImage`, `StreamRix-Linux.tar.gz` |

The binaries are native wrappers around the already-live web application at
`https://streamrix.site/player.html`, so no private source is needed to build
them. Branding files are downloaded from the live site at build time.

## Trigger a build

1. Open **Actions**.
2. Select **StreamRix — Build All Platforms**.
3. Click **Run workflow**. Optionally enter a version tag like `v1.0.2`.

Every successful build creates a release at
`https://github.com/cybermadhan01/streamrix-app/releases/latest` with stable
filenames. `download-links.json` is committed once and never needs editing: it
points at GitHub's `releases/latest/download/...` URLs, so each new release
becomes the live download on streamrix.site immediately.

## Website integration

`download-links.json` is the only hand-off to the website. The site loads it
through `download-links.js`, which is included on the home page and every other
page. Because the file URLs use GitHub's `releases/latest/download/...`
endpoint, a new build goes live on the site immediately — no HTML edits.

## Lockdown

See [REPO-PROTECTION.md](REPO-PROTECTION.md) for the one-time branch protection
that blocks every human push while still letting the CI bot write its manifest.
