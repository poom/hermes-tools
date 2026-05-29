# Sequential rmux drain with explicit Discord progress

Use this when a scheduled `pending-pr-review` run explicitly asks for sequential rmux/tmux reviewer lanes **and** explicit Discord progress/per-PR delivery even though the scheduler also auto-posts the final response.

## Durable workflow notes

- Treat the user's delivery instruction as authoritative. The usual scheduled-cron shortcut (`final response only; no dynamic delivery`) is overridden when the job text explicitly says to send progress/debug/per-PR messages.
- Still keep the final response user-visible and compact; it is the parent/fallback recap that survives cutoffs.
- Send these operational messages as work completes, not only at the end:
  1. initial parent queue count with `raw_fetched`, `dropped_by_local_filter`, and `risk_hidden_by_local_filter`;
  2. `Starting <repo> #<num> ...` before each PR;
  3. one PR-specific final result in the deterministic PR channel;
  4. one parent `Done ... remaining after re-list: <N>` line after each live queue re-list.
- Process one PR at a time. After a PR is posted/verified/skipped, re-list before starting the next PR.
- If the raw queue still returns a PR that has a current-head `poom` formal decision, report it as `already reviewed on current head / process-blocked`, update memory, and include it in the final recap. Do not duplicate the GitHub review and do not say the raw queue is clear.

## Reviewer lane transport notes

- Codex/Claude lane transport failures are operational details for the Discord result and memory, not GitHub review-body content.
- For Claude interactive rmux, `--tools ''` can still leave the TUI at an agent/tool/auth prompt with only echoed prompt text. If there is no substantive verdict and no completion sentinel, kill the rmux/session promptly, append a transport-stall marker to the output file, and synthesize from refreshed GitHub evidence plus local validation.
- For Codex CLI auth/transport failures, record the output path and mark Reviewer A unavailable. Do not encode the failure as a durable negative claim about Codex itself; auth/setup can change.

## Practical reporting detail

When sending Discord results via a local helper, verify its expected target shape. Some helpers accept a raw channel id (`150...`) rather than `discord:<id>`; if the first send fails with a target-format error, retry once with the raw channel id and record only the successful message id(s).
