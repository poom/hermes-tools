# Max tool-iterations cutoff during deliver-local pending-review drains

Use this when the platform/user announces that no more tool calls are allowed after a sequential pending-review run has already sent some Discord/GitHub side effects.

## Required final-response shape

When the cutoff arrives, do **not** attempt more queue checks, GitHub verification, Discord delivery, rmux polling, or memory writes. The final response is now only a local recovery log.

Include:

- Every PR that was fully completed and user-reported before the cutoff.
- For each completed PR: PR URL, verdict, GitHub action, formal review id/state when available, reviewed head SHA, Discord PR-channel/parent destinations if known, and model/token usage if already captured.
- Any PR that was started but not completed, explicitly marked `unfinished`.
- For unfinished PRs: worktree/root paths, current head/base last observed, evidence already collected, reviewer-lane/session/output paths if known, and the explicit statements `no GitHub review posted` and `no final per-PR result sent` unless verified otherwise.
- The last live queue snapshot that was actually re-listed before the cutoff.
- Counts: completed, skipped, failed, unfinished/started, not started.
- The caveat: `final live queue clearance was not re-verified` unless a final post-action queue re-list was already performed.

## Do not over-claim

- Do not label an unfinished PR as approved/requested-changes just because preliminary evidence suggests a verdict.
- Do not imply the raw queue is clear unless the live queue script returned empty after all completed actions.
- Do not say a Discord result was delivered for a PR unless `send_message` already succeeded for that PR.
- Do not post or promise to post after the cutoff; recovery must happen in the next scheduled/manual run.

## Useful recovery wording

```text
Completed and user-reported:
- <repo> #<num> — <verdict>
  - PR: <url>
  - GitHub action: <state> posted and verified, review id <id>
  - Discord: <channel/url>

Started but not completed before cutoff:
- <repo> #<num> — unfinished
  - PR: <url>
  - Last observed head: <sha>
  - Evidence collected: <short list>
  - GitHub action: none / no formal review posted
  - Discord: no final per-PR result sent

Queue status:
- Last live queue snapshot: <items>
- final live queue clearance was not re-verified.
```
