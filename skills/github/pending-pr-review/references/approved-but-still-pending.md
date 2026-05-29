# Current-head reviewed PRs that still appear in the pending-review queue

## Trigger

During a pending-review batch, `scripts/list_pending_prs.sh --json` may continue to list PRs after Poom has already submitted a formal decision on the current head:

- `APPROVE` on the current head, while the PR is still blocked by process/merge gates such as Policy Bot disapproval/error, stale AI-review refresh checks, being behind base, team review requests (for example `dev-all`) that remain open even after Poom approved, or other required checks.
- `CHANGES_REQUESTED` on the current head, while the PR remains raw-pending because the blocker is unresolved. Do not re-run or repost the same request-changes review unless the head changed, new evidence requires superseding, or the user explicitly asks for a re-review.

The inverse also happens: `reviewDecision` can be `APPROVED` because another reviewer/bot approved, while Poom is still explicitly requested on the current head. In that case the PR still needs Poom's formal review; do not skip solely because `reviewDecision == APPROVED`.

## Required handling

1. For every listed PR, fetch current live state:
   ```bash
   gh pr view <PR> --repo <OWNER/REPO> --json headRefOid,reviewDecision,mergeStateStatus,title
   gh api repos/<OWNER>/<REPO>/pulls/<PR>/reviews --paginate \
     --jq '[.[]|select(.user.login=="poom")|{state,commit_id,submitted_at,body:(.body|tostring|.[0:100])}]|.[-5:]'
   ```
2. If Poom has an `APPROVED` or `CHANGES_REQUESTED` review whose `commit_id` equals the current `headRefOid`, do **not** post a duplicate GitHub review. The review **body text is not authoritative** for head matching: GitHub can attach a submitted review to the current commit while the body still mentions an older SHA from a reused/reconstructed review note. Trust the formal review API `commit_id` over quoted body text. If the body/head mismatch makes the substantive verdict uncertain, do a narrow revalidation of the current diff/checks, but still skip duplicate posting when the current-head formal decision exists.
   - If `reviewDecision` is `APPROVED` but there is **no** Poom `APPROVED` review with `commit_id == headRefOid`, and Poom is requested (directly or through the pending queue), continue the guardrail review and post Poom's formal decision if authorized. Approval by another actor or bot is not a substitute for Poom's pending review.
   - If Poom has current-head `CHANGES_REQUESTED`, classify the PR as already reviewed / still blocked by the recorded finding. Re-review only when the head changed, the user asks to supersede, or new evidence needs the supersede-current-head-request-changes path.
   - If the live queue lists a PR whose direct Poom request is gone but a team request remains, and Poom already approved the current head, classify it as process/team-gate blocked rather than re-reviewing.
3. Post a per-PR thread result saying it is already reviewed on the current head and remains listed because of process/merge state or unresolved requested changes, not missing Poom review.
4. Rename/status the PR lane according to the decision (`Approved`, `Approved (blocked)`, or `Requested changes`); keep deterministic channel names stable.
5. In the final batch recap, separate:
   - `Reviewed/approved/requested-changes this run`
   - `Already approved on current head; still listed due process state`
   - `Already requested changes on current head; still listed due unresolved blocker`
   - `Still genuinely pending review`

## Example wording

```text
✅ <repo> #<num> — already reviewed on current head
🔗 <PR URL>

Verdict: Approve
Why:
- Verified live head is still <sha>.
- Verified Poom already has a submitted APPROVE review on that same head.
- GitHub reviewDecision is APPROVED; remaining state is process/merge blocking.

GitHub action:
- Already approved; no duplicate review posted.
```

```text
🛑 <repo> #<num> — already reviewed on current head
🔗 <PR URL>

Verdict: Needs changes
Why:
- Verified live head is still <sha>.
- Verified Poom already has a submitted CHANGES_REQUESTED review on that same head.
- The PR remains listed because the requested-change blocker is unresolved, not because a new Poom review is missing.

GitHub action:
- Already requested changes; no duplicate review posted.
```

## Pitfall

Do not claim `No pending PRs — queue is clear ✅` only because every listed PR has already been approved or requested-changes on the current head. The live list is not empty. Say the queue still lists process-blocked / already-decided PRs, name them, and use wording like `No unreviewed PRs remain`.
