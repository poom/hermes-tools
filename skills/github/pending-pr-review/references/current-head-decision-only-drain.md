# Current-head decision-only drain runs

Use this reference when a scheduled `pending-pr-review` drain discovers PRs that are still returned by the raw pending-review query, but each PR already has a formal Poom review decision on the live head.

## Pattern

1. Fetch the live queue with `scripts/list_pending_prs.sh --stats-json` and save the JSON to a temp file before parsing.
2. For each listed PR, create/reuse the deterministic PR Discord channel as usual.
3. Before launching rmux/Codex/Claude reviewer lanes, fetch live PR state and pulls reviews:
   - `gh pr view ... --json headRefOid,reviewDecision,mergeStateStatus,...`
   - `gh api repos/OWNER/REPO/pulls/PR/reviews --paginate > reviews.json`
4. If Poom has `APPROVED` or `CHANGES_REQUESTED` where `commit_id == headRefOid`, skip rmux reviewer lanes and skip GitHub posting.
5. Still update PR review memory with:
   - live head SHA
   - review id/state/submitted_at/commit_id
   - reviewDecision and merge/process snapshot
   - Discord channel used for reporting
   - a fresh top status board if the saved `Head reviewed:` line is stale; do not let an older memory head override the pulls-reviews `commit_id == headRefOid` proof.
6. Send exactly one per-PR user-facing message to the PR channel and one compact parent/fallback index line.
7. Re-list the queue after each PR and at the end.
8. When the final re-list still contains only duplicate-gated/process-blocked PRs, send a compact parent/fallback recap saying “no unreviewed PRs remain” and listing the still-raw-pending PRs with their current-head review ids. This recap is separate from the per-PR message and should not use the exact empty-queue string.

## Reporting language

If the final live queue still contains only PRs with verified current-head Poom decisions, do **not** send the exact empty-queue string. Use language like:

```text
Pending PR review drain complete: no unreviewed PRs remain.

Raw queue still lists 2 PRs, both with verified current-head Poom decisions:
- repo #123 — current-head APPROVED review id 111; still blocked by policy/process gate.
- repo #456 — current-head CHANGES_REQUESTED review id 222; still blocked by existing requested changes.

No duplicate GitHub reviews were posted.
```

Reserve `No pending PRs — queue is clear ✅` for an actually empty script result.

## Concrete examples

- A PR with current-head Poom `CHANGES_REQUESTED` can remain listed because the requested-change blocker is still unresolved. Report `already reviewed — Needs changes remains current`; do not rerun reviewer lanes or repost another request-changes review.
- A PR with current-head Poom `APPROVED` can remain listed because `mergeStateStatus`/Policy Bot/checks are still blocked or pending. Report `already reviewed — Approve remains current`; do not duplicate approval.
- If a review body quotes an older/intermediate SHA but the pulls reviews API record has `commit_id == headRefOid`, trust the formal review record for duplicate-gate purposes. Mention the body/commit distinction in memory if it could otherwise confuse future runs.
