# GitHub Actions required-checks comment workflows

Use this when reviewing workflows that post or update PR comments showing required-check / Policy Bot `has_status` status.

## Concrete failure pattern

A POC workflow may appear to run successfully while posting a misleading comment such as:

```md
- ⬜ `ai-assistance-disclosure / AI Label Check` — missing
```

On the same head SHA, GitHub's check-runs API can show the check actually exists and failed. Treat this as a code blocker: the human-facing replacement for GitHub's native required-check UI is wrong.

## Review checklist

1. **Permissions match APIs used**
   - If the workflow calls `/commits/{sha}/check-runs`, require `checks: read`.
   - If it calls `/commits/{sha}/status` or statuses APIs, require `statuses: read`.
   - `contents: read` + `pull-requests: write` is not enough for status collection.
   - Do not let code swallow 401/403/5xx and render empty state as `missing`; fail the job or render an explicit collection failure.

2. **Policy Bot semantics are preserved**
   - `has_status.statuses` alone is not the full contract; inspect and honor `has_status.conclusions`.
   - Do not globally count `neutral` as passing when `.policy.yml` says `conclusions: [success]`.
   - Default conclusions, if omitted, should match Policy Bot behavior rather than guessed UI semantics.

3. **Event fan-out is safe**
   - `pull_request`, `check_suite.completed`, `check_run.completed`, and `status` can overlap for the same PR/head.
   - Require a PR/head-scoped `concurrency` group so two workers cannot both miss the marker comment and create duplicates.
   - Prefer no-oping when the rendered body is unchanged to reduce edited-comment churn and rate-limit pressure.

4. **Pagination is handled**
   - Check-runs, commit statuses, and issue comments can exceed `per_page=100` on busy repos, reruns, and matrix-heavy workflows.
   - Require `gh api --paginate` or explicit Link pagination before trusting a `missing` result.

5. **Current PR output is evidence**
   - If the workflow is intended to validate on its own PR, inspect the generated marker comment and compare it to live check-runs/statuses for the same head SHA.
   - A passing workflow check is insufficient if the comment content is wrong.

6. **Rollout scope matches the ticket**
   - For centrally synced templates, compare the ticket/PR body against sync manifest changes (for example `sync-workflow-files.yml`).
   - If the template is intentionally not synced in the POC, the PR/ticket should explicitly narrow scope or leave a follow-up; do not mark the original sync-rollout acceptance item done by implication.

## Useful commands

```bash
PR_URL=https://github.com/OWNER/REPO/pull/123
HEAD=$(gh pr view "$PR_URL" --json headRefOid --jq .headRefOid)

# Marker comment body
gh api repos/OWNER/REPO/issues/123/comments --paginate \
  --jq '.[] | select((.body // "") | startswith("<!-- required-checks-comment -->")) | {id,updated_at,body}'

# Check-run reality for a named required check
gh api "repos/OWNER/REPO/commits/$HEAD/check-runs?per_page=100" \
  --jq '.check_runs[] | select(.name=="REQUIRED CHECK NAME") | {name,status,conclusion,html_url,completed_at}'

# Base policy `has_status` contract
gh api repos/OWNER/REPO/contents/.policy.yml?ref=BASE --jq .content | base64 -d | grep -n -A12 -B4 has_status
```
