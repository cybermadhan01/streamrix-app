# Lock this repository to CI-only writes

This is a **personal** repository, so classic branch protection cannot restrict
pushers. A repository **ruleset** is used instead. It is already applied with:

```
POST /repos/cybermadhan01/streamrix-app/rulesets
{
  "name": "CI-only writes",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [
    { "type": "creation" },
    { "type": "update", "parameters": { "update_allows_fetch_and_merge": false } },
    { "type": "deletion" },
    { "type": "non_fast_forward" }
  ],
  "bypass_actors": []
}
```

Effect on `main`:

- `update` — **nobody can push a commit**, including the repository owner.
- `creation` — no new branches from pushes.
- `deletion` — branch cannot be deleted.
- `non_fast_forward` — no history rewrites.
- `bypass_actors: []` — there is no back door for a developer account.

The CI workflow does **not** push to `main`. It only creates GitHub Releases,
which is separate from repository refs. This is why the lock can be total.

## Why no CI bypass is needed

`download-links.json` contains only `releases/latest/download/<filename>` URLs.
Those URLs always resolve to the newest release, so the manifest is static and
never has to be rewritten after a build.

## Verify

```powershell
gh api repos/cybermadhan01/streamrix-app/rulesets --jq '.[] | {name, enforcement, bypass_actors, rules: [.rules[].type]}'
```

## Temporarily editing the workflow

Because nobody can push to `main`, to change the CI files:

1. In GitHub UI, open **Settings → Rules → Rulesets → CI-only writes** and
   disable it.
2. Push your change / merge your PR.
3. Re-enable the ruleset.

This temporary, visible step is intentional — an unreviewed push to the
release repository is impossible while the ruleset is active.

## Also verify no other write paths

```powershell
gh api repos/cybermadhan01/streamrix-app/collaborators --jq '.[].login'
```

An empty list means no developer account has write access.
