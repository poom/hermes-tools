# Re-requested Reviews That Still Appear in Pending Queue

## Trigger

A PR still appears in `scripts/list_pending_prs.sh --json` / `--stats-json` because GitHub has Poom in `reviewRequests`, even though an older Poom approval may exist in the Pull Request Reviews API.

This can happen when GitHub re-requests review, a previous approval is dismissed/hidden by workflow state, or the aggregate `reviewDecision` remains `APPROVED` while Poom is still explicitly requested.

## Rule

If the PR is in the pending-review queue and GitHub still lists Poom in `reviewRequests`, post a normal current-head review result after refreshing the guardrail evidence. Do not silently skip based on prior local memory, chat notes, or aggregate `reviewDecision`.

The goal is to clear the live GitHub `reviewRequests` entry so the PR does not requeue in the next scheduled round.

## Required Checks Before Posting

1. Re-fetch live PR state:
   - `headRefOid`
   - `reviewRequests`
   - `reviewDecision`
   - `mergeStateStatus`
2. Re-fetch Pull Request Reviews API and inspect Poom reviews on `headRefOid`.
3. If Poom is still in `reviewRequests`, perform a normal/narrow guardrail refresh:
   - read latest comments and review threads;
   - confirm current checks/plans;
   - verify old blockers are still resolved or no new blockers appeared;
   - run Reviewer B when practical.
4. Submit the normal formal review body (`APPROVE`, `REQUEST_CHANGES`, or `COMMENT` as appropriate), not an administrative note like “clearing queue”.
5. Verify through the Pull Request Reviews API and re-query PR state.
6. Re-run the pending queue script and report whether the PR disappeared.

## Reporting Shape

Include:

- Review id and URL.
- Reviewed head SHA.
- Whether Poom is still in `reviewRequests` after posting.
- Whether the PR still appears in the pending queue after posting.
- Any remaining process blockers such as branch behind main, policy-bot, or apply gates.

## Example Outcome

For a permissions/Terraform PR where an older current-head Poom approval existed but Poom was re-requested:

- Posted a fresh normal approval on the same current head.
- Verified the new review id via Pull Request Reviews API.
- Verified Poom disappeared from `reviewRequests`.
- Re-ran the pending queue and confirmed the PR no longer appeared.
