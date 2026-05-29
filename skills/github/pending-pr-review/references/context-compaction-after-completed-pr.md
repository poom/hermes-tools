# Context compaction after a completed PR but before parent completion send

Use this recovery pattern when a scheduled sequential pending-review run is compacted or resumed after a PR was already fully reviewed/reported, and the only uncertain step is the parent/fallback progress line.

## Recognition signals

- Per-PR result was already sent to the PR-specific channel and has a message id.
- GitHub review was already posted and verified through the pulls reviews API on the current `headRefOid`.
- Durable review memory was updated.
- The live pending queue was already re-listed after the PR and returned a concrete snapshot, often `N=0`.
- A parent completion message file exists, but the transcript does not show it being sent.

## Recovery steps

1. Do **not** duplicate the GitHub review or per-PR result.
2. If tool calls are still allowed and the parent completion message file exists, try sending it once with `hermes send --to <parent-target> --file <file> --json || true`.
3. If Hermes returns `skipped=true` with `reason=cron_auto_delivery_duplicate_target`, do not retry that same parent target. Preserve the intended parent progress line in the final cron response instead.
4. In the final response, include:
   - completed/skipped/failed counts,
   - final live queue snapshot and whether it was re-verified,
   - the PR URL and PR-channel link/message location,
   - the verified GitHub review id/action,
   - the caveat that parent/fallback dynamic sends were skipped because the cron scheduler auto-delivers to the same target.
5. If the final queue was already re-listed to zero, it is safe to include `No pending PRs — queue is clear ✅` in the final response. Do not run another review just to recreate progress messages.

## Pitfall

A missing parent `Done ... remaining after re-list` send in the transcript is not an unfinished PR review when the formal review, per-PR result, memory update, and final live queue re-list are already complete. Treat it as a delivery-recap recovery, not a review recovery.
