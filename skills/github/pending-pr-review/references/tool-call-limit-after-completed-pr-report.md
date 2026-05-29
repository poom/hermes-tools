# Tool-call limit after a PR was posted and reported, before final re-list

Use this recovery/reporting shape when a scheduled `deliver: local` pending-review run has already completed a PR unit of work — formal GitHub review posted and verified, review memory updated or mostly updated, PR-channel result sent, and parent/fallback index sent — but the platform/user then announces the maximum tool-calling iterations before the required final live queue re-list can run.

## What to do immediately

- Do **not** call more tools, send more messages, or try to re-list the queue after the cutoff instruction.
- Produce a local-only final log. User-facing PR results should already have been delivered with `send_message`; do not duplicate the full per-PR result in the local final.
- Clearly distinguish completed/reported PRs from queue clearance.

## Local final response shape

Include:

- Completed/reported PRs, each with:
  - repo/number and URL when available
  - verdict
  - GitHub action and formal review id
  - reviewed/current head commit if known
  - PR-channel and parent/fallback message ids if known
- Counts: completed, skipped, failed.
- Explicit caveat:
  - `Final live queue clearance was not re-verified after <last PR> because the tool-call limit was reached.`
- State whether another PR review was started after the last completed PR. If not, say so explicitly.

Do **not** say `No pending PRs — queue is clear ✅` unless the queue was actually re-listed empty before the cutoff.
Do **not** imply all raw pending PRs were drained. Use “completed/reported” rather than “queue clear.”

## Why this exists

A completed PR unit is real progress and should not be marked unfinished, but pending-review queues are live. Without a final `scripts/list_pending_prs.sh --stats-json` re-run, new or still-listed PRs may remain. The honest outcome is: posted/reported reviews are complete; final queue clearance is unverified.
