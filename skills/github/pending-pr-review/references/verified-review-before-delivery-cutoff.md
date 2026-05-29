# Verified GitHub review before per-PR delivery cutoff

Use this recovery note for deliver-local scheduled pending-review drains when a PR reached a verified formal GitHub review, but the run was interrupted before the required per-PR user-facing Discord/Telegram result and/or final queue re-list.

## Trigger shape

- Sequential rmux/tmux drain mode.
- A formal GitHub review was submitted and verified through `repos/:owner/:repo/pulls/:number/reviews` on the live `headRefOid`.
- The job hit a tool/runtime cutoff before one or more required user-facing messages were sent.
- The final live queue was not re-listed, or a new/head-changed delta was only partially inspected.

## Recovery steps

1. **Do not re-review or repost by default.** First verify the live PR head and pulls reviews API. If Poom already has a current-head `APPROVED` or `CHANGES_REQUESTED` review, treat the GitHub decision as done and avoid duplicate reviews.
2. **Complete missing user-facing delivery.** In deliver-local runs, a verified review is not complete until the per-PR result has been sent to the PR-specific channel (or fallback target) and the parent index/update line has been sent.
3. **Report exact provenance.** Include the review id, state, `commit_id`, PR `headRefOid`, and whether the per-PR channel/fallback was used.
4. **If the head changed around posting, validate narrowly before messaging.** Compare the reviewed/prepared head to the review `commit_id` and current `headRefOid`. If the formal review is attached to the current head but the body discusses an older intermediate SHA, trust the review object's `commit_id` for duplicate gating, then inspect the small delta enough to classify whether the already-posted decision still reads correctly.
5. **Do not claim queue clearance.** Unless the recovery run re-runs the pending queue script after delivery, say `final live queue clearance was not re-verified`. If the queue still lists only current-head reviewed/process-blocked PRs, say `No unreviewed PRs remain`, not the exact empty-queue string.
6. **Update review memory.** Record the verified review id/state/commit, delivery target, any head-change caveat, and the fact that the missing per-PR report was recovered.

## Per-PR recovery wording

Use language like:

```text
GitHub action: already posted before the previous cutoff — verified <STATE> review id <id> on current head <sha>.
Delivery recovery: this message completes the missing per-PR deliver-local report; no duplicate GitHub review was posted.
Queue note: final live queue clearance will be checked after this report; until then, do not treat the queue as clear.
```

## Pitfall

A formal review being verified is not the same as the scheduled pending-review workflow being complete. In `deliver: local` mode, missing Discord/Telegram delivery is a user-visible workflow failure even when GitHub state is correct. Recover delivery first, then re-list the queue.
