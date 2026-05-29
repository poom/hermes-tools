# Sequential rmux cutoff after evidence-only PR start

Use this when a scheduled `pending-pr-review` sequential rmux drain fully completes one PR, then begins the next PR but hits a tool/runtime cutoff before reviewer lanes, synthesis, GitHub posting, memory update, or per-PR delivery.

## Classification

Classify the partially started PR as **evidence-only started**, not reviewed, failed, approved, or requested-changes.

Evidence-only start examples:

- PR channel may or may not have been created.
- Repo clone/fetch/checkout completed.
- PR metadata, checks, diffstat, diff, comments, reviews, or review-thread artifacts were saved.
- A guardrail reference was read and local evidence inspection began.
- No completed Reviewer A/B lanes, no synthesized verdict, and no final head/duplicate-review gate happened.

## Required final/local cutoff wording

For the completed PRs, report only verified actions: review id/state/commit, delivery target/message id if known, and memory update if done.

For the evidence-only PR, say all of the following clearly:

- `Status: evidence-only started`
- `No final review synthesized`
- `No GitHub review posted`
- `No per-PR result sent`
- The evidence root/worktree paths if known
- The last known head SHA if known
- `Recovery requirement: re-fetch current head + duplicate-review state before using any saved evidence`

Do **not** imply the PR has a proposed verdict. Do **not** call it blocked/approved/needs-changes unless a formal current-head review or completed synthesis exists.

## Recovery run checklist

1. Re-run the pending queue script and locate the PR in the live queue.
2. Fetch current PR metadata and `headRefOid`; compare with the saved evidence head.
3. Query `pulls/<number>/reviews` and filter for `user.login == "poom"`, `commit_id == headRefOid`, and `state in (APPROVED, CHANGES_REQUESTED)` before doing review work.
4. If a current-head Poom decision exists, skip duplicate posting and report it as already reviewed/process-blocked if still listed.
5. If no current-head decision exists and the head is unchanged, saved diff/check/comment artifacts may be used as hints, but refresh live comments, reviews, threads, checks, and diff before synthesis.
6. If the head changed, treat saved evidence as stale context only; restart the guardrail review against the new head.

## Parent/fallback delivery

If cutoff prevents dynamic delivery, the local final response should be a recovery log, not the only user-facing PR result. Include:

- Completed PRs and their verified Discord/GitHub side effects.
- Evidence-only PRs and exact unfinished state.
- Last live queue snapshot if available.
- The caveat: `final live queue clearance was not re-verified` unless a final re-list already happened after all work stopped.
