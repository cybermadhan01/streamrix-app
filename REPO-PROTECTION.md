# Lock this repository to CI-only writes

Run these once (you are already authenticated as `cybermadhan01`):

```powershell
gh api -X PUT repos/cybermadhan01/streamrix-app/branches/main/protection `
  -H "Accept: application/vnd.github+json" `
  -f required_status_checks=null `
  -f 'enforce_admins=true' `
  -f required_pull_request_reviews=null `
  -f 'restrictions[users][]=' `
  -f 'restrictions[teams][]=' `
  -f 'restrictions[apps][]=github-actions' `
  -f 'allow_force_pushes=false' `
  -f 'allow_deletions=false' `
  -f 'block_creations=true' `
  -f 'required_conversation_resolution=false'
```

What this does:

- `restrictions[apps][]=github-actions` — **only the GitHub Actions bot can
  push to `main`**. No developer account can push code.
- `enforce_admins=true` — even the repository owner is blocked.
- `allow_force_pushes=false`, `allow_deletions=false`, `block_creations=true`
  — no history rewrites, no branch deletes.
- `required_pull_request_reviews=null` — the CI bot commits the refreshed
  `download-links.json` directly, so a PR gate would block it.

## Verify

```powershell
gh api repos/cybermadhan01/streamrix-app/branches/main/protection --jq '.restrictions'
```

Expected: `apps: ["github-actions"]`, empty `users` and `teams`.

## Temporarily editing the workflow

Because humans cannot push to `main`, edit workflow files on a side branch,
open a PR, then temporarily remove protection, merge, and re-apply the command
above. This is intentional: it makes an unreviewed push to the release repo
impossible.

## Also remove other write paths

```powershell
# No outside collaborators (owner only)
gh api repos/cybermadhan01/streamrix-app/collaborators --jq '.[].login'
```

An empty list means no developer account has write access.
