# Tool-call cutoff after rmux reviewer prompt stall

Use this when a sequential pending-review drain has already gathered parent evidence for a PR, then rmux reviewer lanes fail or stall before synthesis/posting and the platform announces the maximum tool-call limit.

## Concrete pattern

A scheduled sequential-rmux drain reached `EWA-Services/Tests #265` after completing earlier PRs. Parent evidence was strong enough to suggest `REQUEST_CHANGES`:

- Current head had no Poom formal review.
- Current-head CI failed on the workflow the PR was meant to fix.
- Docs/PR body claimed a 5-minute Playwright timeout, while code set `PLAYWRIGHT_TEST_TIMEOUT_MS = 3 * 60 * 1000` and CI logs showed `Test timeout of 180000ms exceeded`.
- An old unresolved review thread was partly stale: current code had added `@issue` to the second test, so the original skip-issues blocker was no longer fully current, though the tag/locale mismatch remained worth noting.

Reviewer lanes then failed/stalled:

- Codex rmux exited with a transport/auth failure (`401 Unauthorized`) and no substantive review.
- Claude interactive rmux stayed at the Claude prompt with no substantive response, meaning the prompt likely was not submitted or the TUI stalled before answering. This must be treated as `Reviewer B unavailable/transport-stalled`; do not treat the prompt text or idle TUI screen as a review.
- The hard tool-call limit arrived before formal GitHub posting, review memory update, per-PR Discord delivery, and final queue re-list.

## Required final/local recovery shape

When the platform says no more tool calls are allowed:

1. Stop all tool use immediately. Do not attempt another queue check, Discord send, GitHub review, or rmux cleanup.
2. Report completed PRs with exact verified GitHub review ids, head SHAs, and delivery message ids if known.
3. For the in-progress PR, label it **unfinished** even if parent evidence suggests a clear verdict:
   - `GitHub action: none / no formal review submitted`
   - `final per-PR user-facing result: not sent`
   - include reviewer lane paths/statuses if known
   - summarize parent evidence as `proposed/likely verdict`, not as a submitted decision
4. Include the last live queue snapshot available.
5. End with the caveat: `final live queue clearance was not re-verified` unless a final re-list already happened after the last completed PR.

## Recovery run checklist

A future recovery run should not blindly post the drafted/likely verdict. It must:

1. Re-fetch live queue and current PR head.
2. Re-check Poom current-head formal reviews via pulls reviews API to avoid duplicates.
3. Re-read live review threads/comments because old unresolved threads may have become stale after new commits.
4. Re-run or narrowly replace stalled reviewer lanes if still needed.
5. Re-synthesize against current head, then post/verify/report normally.
