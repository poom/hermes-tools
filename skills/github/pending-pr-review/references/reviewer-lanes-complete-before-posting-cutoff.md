# Reviewer lanes complete before GitHub posting cutoff

Use this when a scheduled `deliver: local` sequential rmux drain reaches the platform/tool-call limit after one PR was fully posted/reported and the next PR's rmux reviewer lanes have completed, but before the parent posts a formal GitHub review, updates review memory, sends the per-PR Discord result, or re-lists the final queue.

## Required local final-response shape

Do not attempt more tool calls after the cutoff notice. Produce a local recovery log only:

- Completed/reported PRs:
  - PR URL
  - verdict
  - formal review id/action if posted
  - current-head SHA verified
  - Discord PR channel/message and parent index message if already sent
  - review-memory path if written
- Started but unfinished PRs:
  - PR URL and PR channel id if created/reused
  - reviewer lane status and output paths, e.g. `rmux/codex.last.txt`, `rmux/claude.out`
  - proposed verdict only, clearly labeled `not posted`
  - `GitHub action: none / no formal review submitted`
  - `User-facing per-PR result: not sent`
  - concrete recovery instruction: re-fetch head + current Poom review state, duplicate-gate, revalidate blockers, then post/report if still applicable
- Last live queue snapshot:
  - count and listed PR URLs if known
  - `filter_stats.risk_hidden_by_local_filter` if known
- Counts:
  - completed/reported
  - skipped duplicate-current-head decisions
  - failed
  - started but unfinished
  - not started
- Queue caveat:
  - `Queue status: not clear` when any live PR remains
  - always include `final live queue clearance was not re-verified` unless a final re-list already happened after all side effects

## Classification rules

- A completed reviewer lane is not a completed PR review. Until `gh pr review` is posted and verified on the current head, report only a **proposed** verdict.
- Channel creation alone is not a user-facing PR result. If no per-PR result message was sent, label it explicitly.
- Do not claim `approved`, `requested changes`, or `GitHub action: requested changes` unless the pulls reviews API confirms the formal decision on the current head.
- Recovery must redo the final head + duplicate-review check. A saved reviewer output/body may be used as evidence, but not blindly posted after a time gap.

## Interactive Claude sentinel nuance

When using `rmux_claude_interactive_reviewer.py`, a lane may produce a substantive verdict and then append `__CLAUDE_IDLE_WITHOUT_SENTINEL__` because the model wrote a human-readable marker such as `REVIEW_DONE` instead of the exact requested sentinel. Treat this as a usable completed lane if the captured output contains a substantive current-head review and the helper records `__CLAUDE_EXIT:0__`. Record the sentinel mismatch as a transport nuance, not as `Reviewer B unavailable`.
