# Tool-call-limit final response in `deliver: local` pending-review drains

Use this when a scheduled `pending-pr-review` run is stopped by the runtime/tool-call limit after some PRs were already processed.

## Durable pattern

When the runtime says no more tool calls are allowed, do **not** attempt additional `send_message`, queue re-listing, GitHub verification, memory writes, or cleanup. The final response is only a local log. It must be precise about which user-visible deliveries and GitHub side effects already happened before the cutoff.

Include:

- Completed PRs that were posted and verified:
  - repo/PR URL
  - formal review id/state and commit/head SHA
  - PR-specific Discord channel and whether parent index was sent
- Started-but-unfinished PRs:
  - repo/PR URL
  - work/channel/evidence already created
  - explicit `no GitHub review posted`
  - explicit `no final per-PR result sent` unless it was actually sent
  - any likely finding as `preliminary evidence`, not a verdict
- Last live queue snapshot if known.
- Counts: completed/reported, skipped, failed, started-unfinished, not-started.
- Exact caveat: `Final live queue clearance was not re-verified.`

## What not to claim

- Do not say the queue is clear unless the final queue script result was empty after all posting.
- Do not label an unfinished PR `approved` or `requested changes` unless the pulls reviews API confirmed a formal current-head decision.
- Do not imply a created Discord PR channel is a completed user-facing per-PR result. Channel creation alone is not review delivery.
- Do not treat preliminary evidence from local inspection as a guardrail verdict if rmux reviewer lanes, final head check, duplicate-review gate, posting, and verification did not happen.

## Example final local log shape

```text
Local cron log — pending-pr-review sequential rmux drain stopped by tool-call iteration limit.

Completed/reported:
- Repo #123 — requested changes posted and verified.
  - PR: https://github.com/ORG/Repo/pull/123
  - GitHub review id: 123456789
  - Commit: abcdef...
  - Discord PR channel: discord:...
  - Parent index sent to discord:...

Started but unfinished:
- Repo #124 — channel/evidence gathered, but no GitHub review posted and no final per-PR result sent.
```

Continuation:

```text
  - PR: https://github.com/ORG/Repo/pull/124
  - Channel created: discord:...
  - Preliminary evidence: ...

Last live queue snapshot:
- Repo #124 — ...
- OtherRepo #1 — ...

Counts:
- Completed and user-reported: 1
- Skipped duplicate/current-head decisions: 0
- Failed: 0
```

Continuation:

```text
- Started but unfinished: 1
- Not started from last snapshot: 1

Final live queue clearance was not re-verified.
```
