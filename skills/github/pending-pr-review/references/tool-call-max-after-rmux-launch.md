# Tool-call max after launching rmux lanes for the next PR

Use this when a scheduled sequential rmux drain finishes and reports one PR, then starts the next PR (checkout/evidence/channel/reviewer lanes) but hits the runtime/tool-call ceiling before synthesis/posting/reporting.

## Recovery/reporting rule

If the platform says no more tool calls are allowed, do **not** imply the in-progress PR was reviewed just because reviewer lanes were launched or one lane exited. The final/local cutoff log should explicitly separate:

- PRs fully completed, posted, verified, and user-reported.
- The currently started PR, with:
  - repo/number/URL;
  - worktree/evidence/rmux output paths when known;
  - reviewer session names/process ids when known;
  - whether any lane was known to exit;
  - `no synthesis completed`;
  - `no GitHub review posted`;
  - `no final per-PR result sent`.
- The last live queue snapshot and the caveat: `final live queue clearance was not re-verified`.

## Why

Launching rmux/tmux reviewers is not a user-visible PR result and is not a GitHub decision. A later recovery run must still read lane outputs, refresh live GitHub state, verify current head, check for duplicate current-head Poom decisions, synthesize, post/verify if appropriate, and then send the per-PR result.

## Recovery run checklist

1. Re-list the pending queue before trusting the old snapshot.
2. For the unfinished PR, inspect existing rmux output files and whether sessions are still alive.
3. Re-fetch PR metadata, comments/reviews, checks, and current head.
4. If the head changed since the prompt/evidence, treat old lane outputs as stale hints only and revalidate or relaunch compact lanes.
5. Before posting, query current-head formal reviews to avoid duplicate approvals/changes requests.
6. After posting/skipping, send the required per-PR user-facing result and parent index line.
