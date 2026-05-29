# Live queue growth and tool-iteration budget exhaustion

Session pattern observed: a pending-review batch started with 6 PRs, all were reviewed and posted, then the required final queue re-list found a newly pending PR. A dedicated Discord thread was created for the new PR, but the session hit the tool-call iteration cap before the new review could be completed.

Guidance for future runs:

- Treat the final queue re-list as a new batch boundary, not as a guarantee that the run can finish every newly arrived PR in the same session.
- If the live queue grows near the end of a long batch and tool/time budget is low, prefer a compact parent-thread update that says the initial batch is complete and lists the newly discovered PR(s) as still pending.
- Do not create or rename a PR-specific thread to `Reviewing` unless there is enough remaining budget to actually start meaningful review work. A `Reviewing` thread with no completed review is worse than a parent-thread note that the PR remains queued.
- If a thread was already created for a newly discovered PR but review cannot continue, post a concise status in that thread/parent channel when possible: `Thread created; review not completed before session/tool budget ended; PR remains pending.`
- Never send `No pending PRs — queue is clear ✅` unless the final live queue list is empty after all posted reviews and any newly discovered PRs were processed.

This complements the main skill's live-queue re-list rule: keep processing newly discovered PRs when practical, but be explicit about unreviewed leftovers when a platform/tool budget prevents completion.
