# Cutoff after duplicate-check and drafted request-changes body

Use this recovery pattern when a sequential RMUX pending-review run reaches the tool-call/runtime cutoff after:

1. A PR was fetched from the live pending queue.
2. Current `headRefOid` and live review state were checked.
3. The pulls reviews API was filtered and showed **no current-head formal `poom` decision**.
4. Reviewer lanes and/or parent synthesis produced a verdict.
5. A complete `review_body.md` was written.
6. The run stopped before `gh pr review`, verification, memory update, per-PR Discord delivery, or final live queue re-list.

## Final response at cutoff

Do **not** describe the PR as approved or requested-changes on GitHub. The only safe status is a proposed/drafted verdict.

Include:

- PR URL and number.
- Current head SHA that was checked.
- Whether a current-head `poom` decision was absent at that time.
- Reviewer lane status, including unavailable/transport failures.
- Draft verdict and blocker summary.
- Path to the saved `review_body.md`.
- `GitHub action: none posted`.
- `Per-PR/user-facing result: not sent` if Discord/send_message did not happen.
- `Final live queue clearance was not re-verified` unless a final re-list already occurred.

## Recovery run

Before posting the saved body, do not trust the old duplicate check blindly:

1. Re-fetch `gh pr view` and current `headRefOid`.
2. Re-fetch pulls reviews and filter for `user.login == "poom"`, `commit_id == headRefOid`, and `state in (APPROVED, CHANGES_REQUESTED)`.
3. If a current-head `poom` decision now exists, skip duplicate posting and report it as already reviewed/process-blocked as appropriate.
4. If the head changed, revalidate the draft against the new diff before posting.
5. If unchanged and no current-head `poom` decision exists, submit the saved full body with the appropriate formal action, then verify through the pulls reviews API.
6. Only after verification update review memory, send the per-PR Discord result, send the parent index/update, and re-list the live queue.

## Example wording

```text
Unfinished PR: EWA-Services/user-iam #194
- Head checked: <sha>
- Current-head poom decision at check time: none
- Draft verdict: REQUEST_CHANGES
- Draft body: /tmp/pending-pr-review-rmux/user-iam-194/review_body.md
- GitHub action: none posted
- Per-PR Discord result: not sent
- Recovery: re-fetch head + duplicate-review state before posting the saved body
- Final live queue clearance was not re-verified
```
