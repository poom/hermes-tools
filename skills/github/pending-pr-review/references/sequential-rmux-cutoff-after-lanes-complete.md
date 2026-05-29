# Sequential rmux cutoff after review lanes complete but before posting

Use this reference for scheduled `pending-pr-review` runs in sequential rmux drain mode when reviewer lanes and local synthesis substantially completed for a PR, but the Hermes/tool-call cutoff happens before the formal GitHub review and required per-PR user-facing report are posted.

## Classification

This is **unfinished review work**, not a completed PR result.

Even if both rmux lanes completed and the head was rechecked, do not report the PR as approved/requested-changes unless the pulls reviews API confirms a formal current-head GitHub decision was submitted, or the workflow explicitly allowed chat-only and the per-PR chat result was sent.

## Required final local log shape

In `deliver: local` jobs, include:

- Completed PRs with verified GitHub action IDs and Discord/channel delivery status.
- The unfinished PR URL/title/head SHA.
- Reviewer lane status and any proposed verdict, clearly labeled as **proposed / not posted**.
- Last live GitHub snapshot: head SHA, review count/current-head decisions, review-thread count, key checks, merge/process state.
- Whether a PR-specific Discord channel was created, and whether the final per-PR result was actually sent.
- Explicit statements:
  - `GitHub action: not posted`
  - `Discord final per-PR result: not sent`
  - `final live queue clearance was not re-verified`

## Recovery steps for the next run

Before posting anything from the saved work:

1. Re-run the live queue script and live PR metadata.
2. Re-check the current head SHA and current-head Poom reviews through the pulls reviews API.
3. Re-read new comments/review threads/checks since the cutoff.
4. If the head is unchanged and no duplicate current-head decision exists, reuse the saved synthesis/reviewer outputs only after confirming findings still apply.
5. Post the full normal `Guardrail review — <RESULT>` body, not an administrative note about recovering from cutoff.
6. Verify the review ID/commit via pulls reviews API.
7. Update review memory with the actual review ID, state, commit ID, delivery channel, and post-action process state.
8. Send the required per-PR Discord/channel result and parent/fallback index line.
9. Re-list the queue before claiming it is clear.

## Pitfall

Creating the PR-specific Discord channel or completing reviewer lanes is not user-facing completion. If the final result was not sent to the PR channel/parent and no GitHub review was posted, mark the PR as unfinished even when the proposed verdict is obvious.
