# Release Please PR current-main conflict check

Use this when reviewing PRs that modify `release-please-config.json`, `.release-please-manifest.json`, release workflows, or component/package release metadata.

## Why

A PR can pass all local validation and still be unmergeable after `main` advances. Release Please manifests are especially prone to stale-root-version conflicts: the PR adds a new component entry while current `main` bumps the existing root package version.

Example pattern from Tools #189:

- PR head `.release-please-manifest.json`:

```json
{
  ".": "0.21.1",
  "codex-telemetry": "0.1.0"
}
```

- current `origin/main`:

```json
{
  ".": "0.21.2"
}
```

The correct post-sync manifest should preserve both:

```json
{
  ".": "0.21.2",
  "codex-telemetry": "0.1.0"
}
```

## Required review steps

From the PR checkout:

```bash
git fetch origin main --quiet
printf 'head=%s\n' "$(git rev-parse HEAD)"
printf 'origin_main=%s\n' "$(git rev-parse origin/main)"
if git merge-base --is-ancestor origin/main HEAD; then
  echo 'trunk_fresh=yes'
else
  echo 'trunk_fresh=no'
  git log --oneline --left-right --cherry-pick origin/main...HEAD | head -20
fi

BASE=$(git merge-base origin/main HEAD)
git merge-tree "$BASE" origin/main HEAD | sed -n '1,260p'
```

Also compare the manifest directly:

```bash
echo 'origin/main:'; git show origin/main:.release-please-manifest.json
echo 'HEAD:'; git show HEAD:.release-please-manifest.json
git diff --unified=80 origin/main..HEAD -- .release-please-manifest.json release-please-config.json .github/workflows/release.yaml
```

## Decision rule

- If `merge-tree` reports a conflict in `.release-please-manifest.json`, request changes even if tests/checks pass.
- The fix is normally to sync `main` and preserve the current root package version from `main` while keeping the new component entry from the PR.
- Distinguish this from an implementation blocker: independent reviewer lanes may approve the code changes, but the formal review should still block on the live merge conflict/stale manifest state.
