# Certification-only tests/CI PRs with stale production-change history

Use this reference when a PR is intended to certify current behavior only: no production code changes in the **net PR diff**, only tests and CI.

## Review pattern

1. Treat the live `base...HEAD` diff as authoritative, not commit history or stale bot review text.
   - Earlier branch commits may have modified production files and later been absorbed by/rebased onto `main`.
   - Copilot/agent comments from older commits may still describe production files that are no longer in the net diff.
2. Fetch the actual base ref and PR ref, then verify both GitHub and local views:
   ```bash
   BASE=$(gh pr view PR_URL --json baseRefName --jq .baseRefName)
   git fetch origin "$BASE:refs/remotes/origin/$BASE" +pull/PR_NUMBER/head:refs/remotes/origin/pr-PR_NUMBER
   git diff --name-status refs/remotes/origin/$BASE...refs/remotes/origin/pr-PR_NUMBER
   git diff --stat refs/remotes/origin/$BASE...refs/remotes/origin/pr-PR_NUMBER
   ```
3. Explicitly check for production drift:
   ```bash
   git diff --name-only refs/remotes/origin/$BASE...HEAD \
     | grep -Ev '^(tests/|\.github/workflows/)' || true
   git diff --check refs/remotes/origin/$BASE...HEAD
   ```
   If the output is empty except expected test/CI paths, state that the current net diff is certification-only.
4. Still review tests/CI quality:
   - Tests should lock current behavior rather than import helper logic that could drift with future production changes.
   - External services should be monkeypatched or fixture-backed.
   - CI should install repo requirements and run the same test command on relevant Python versions.
5. If local host lacks project dependencies, use `uv run --python <ci-version> --with-requirements requirements.txt --with pytest pytest -q` as a narrow local validation path before relying only on remote CI.

## Reporting wording

Use wording like:

> The branch history/stale bot comments mention earlier production-file edits, but the current net PR diff against `<base>` contains only `<test/CI paths>`. No production-code drift is present on current head `<sha>`.

## Approval conditions

Approve when:
- Current net diff is tests/CI only.
- Added tests reasonably certify the stated current behavior.
- Local or remote CI is green.
- Any remaining caveat is only coverage depth (smoke/certification vs exhaustive proof), not production drift.
