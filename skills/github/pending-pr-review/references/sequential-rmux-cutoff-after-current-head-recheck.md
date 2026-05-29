# Sequential rmux cutoff after current-head recheck, before posting

Use this recovery shape when a sequential pending-review drain has fully completed and reported an earlier PR, then gathers enough evidence for the next PR and performs the final current-head / duplicate-review check, but the platform/user announces the maximum tool-calling iterations before the formal GitHub review, review memory update, per-PR Discord delivery, or final queue re-list.

## Concrete shape from 2026-05-27 run

- Completed PR before cutoff: `EWA-Services/Tools #194` was approved, verified through the pulls reviews API, memory-updated, and reported to its PR Discord channel plus parent index.
- Next PR in progress: `EWA-Services/Tests #265`.
- Evidence gathered before cutoff showed request-changes-level risk:
  - current-head human `CHANGES_REQUESTED` review existed;
  - unresolved review thread remained on `tests/ui/1_ID/UserDelete.spec.ts`;
  - PR/README claimed a 5-minute Playwright timeout while code set `3 * 60 * 1000`, and CI failed with `Test timeout of 180000ms exceeded`;
  - API/UI required checks were failing.
- Reviewer B interactive Claude rmux lane idled at the prompt with no substantive answer and was killed/marked unavailable.
- Parent performed a live current-head and duplicate-review probe:
  - head was double-sampled and unchanged;
  - no current-head `poom` formal decision existed.
- Cutoff happened before `gh pr review`, memory update, per-PR Discord result, parent index, or final queue re-list.

## Required final/local response

When the max-tool/user cutoff arrives at this point, stop all further tool calls immediately. Do **not** try to post the already-drafted or obvious review, do **not** send Discord messages, and do **not** re-list the queue.

Report locally:

1. Every PR that was fully completed before cutoff, including GitHub review id, reviewed head, and delivery locations.
2. The in-progress PR as **unfinished** even if the evidence strongly indicates a verdict.
3. The last verified head/duplicate-review state for the unfinished PR.
4. `GitHub action: none posted before cutoff` for the unfinished PR.
5. `Discord result: not sent before cutoff` for the unfinished PR.
6. A compact evidence summary/proposed direction, clearly labeled as not posted.
7. The last known queue snapshot and the caveat: `final live queue clearance was not re-verified`.

## Recovery run checklist

A later run should not blindly post the old proposed verdict. It must first:

1. Re-fetch the PR head and compare it with the saved reviewed head.
2. Re-check current-head `poom` formal reviews via the pulls reviews API.
3. Re-read unresolved threads/comments and current checks, because the author may have pushed fixes after the cutoff.
4. If head/evidence still matches, synthesize/post the full formal review body and verify the review id/commit.
5. Send the missing per-PR Discord result and parent index line.
6. Re-list the live queue before claiming clear/no-unreviewed status.
