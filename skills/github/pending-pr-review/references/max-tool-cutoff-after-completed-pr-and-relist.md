# Max-tool cutoff after completed PR delivery and live re-list

Use this recovery/reporting shape when a scheduled pending-PR review run has already completed one or more PRs, posted/verified the GitHub review decisions, delivered the per-PR Discord messages, and re-listed the live queue, but then the platform/user announces that no more tool calls are allowed.

## Required behavior

1. Stop immediately. Do not try to send another Discord message, re-run queue discovery, inspect files, or start the next PR.
2. Final response is a parent/fallback recap only; the scheduler will auto-deliver it when configured that way.
3. Include every completed PR with:
   - repo/PR/title and URL
   - formal GitHub action/state (`APPROVED`, `CHANGES_REQUESTED`, etc.)
   - review id and current-head `commit_id` when already verified
   - per-PR Discord channel/message id if known
   - concise verdict reason
4. Include the latest live queue snapshot that was already captured before cutoff. Label it as the **latest live queue snapshot**, not as a fresh/current check.
5. If the latest re-list was non-empty, explicitly say the queue is not clear and list the remaining PRs.
6. If no next PR was started after the re-list, say so. This prevents a future recovery run from looking for half-started reviewer lanes or draft bodies that do not exist.
7. Do not use the exact empty-queue string unless the already-captured final re-list was empty.

## Example wording

```text
Scheduled pending-PR review run recap (stopped because max tool-calling iterations were reached).

Completed / reported:
1. ✅ OWNER/repo #123 — Approved
   - Formal review id: ...
   - Current-head commit: ...
   - Per-PR Discord message id: ...

Latest live queue snapshot after #123: 6 PRs still pending review/request queue:
- OWNER/repo #124 — title — URL

Queue is not clear. I did not start the next PR before the tool-call cutoff.
```

## Pitfalls

- Do not imply final live queue clearance was re-verified after the cutoff announcement.
- Do not re-open tooling to fetch a newer queue snapshot; the cutoff instruction forbids more tool calls.
- Do not claim an unfinished PR was reviewed just because its channel was created or evidence was collected earlier.
