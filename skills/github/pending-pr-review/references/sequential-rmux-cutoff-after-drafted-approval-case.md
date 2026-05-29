# Sequential rmux cutoff after approve-level review body was drafted

Use this as a concrete recovery shape for scheduled `deliver: local` pending-review drains when the parent completes evidence gathering + rmux reviewer lanes + local validation, drafts an approve/request-changes body, then hits the tool-call/runtime limit before `gh pr review`, memory update, per-PR Discord delivery, or final queue re-list.

## Observed pattern

A PR can show `reviewDecision: APPROVED` while still lacking a current-head formal review from `poom`:

- `reviewDecision` may be satisfied by another human/bot review (for example `finn-ai-coder[bot]`), not by Poom.
- The pending-review queue can still return the PR because Poom was requested or because process gates remain.
- Before skipping as duplicate-gated, query `repos/OWNER/REPO/pulls/PR/reviews` and filter by both:
  - `user.login == "poom"`
  - `commit_id == headRefOid`
  - `state in ("APPROVED", "CHANGES_REQUESTED")`

If that filtered list is empty, a current-head Poom decision is still missing even when `reviewDecision` is `APPROVED`.

## Cutoff final-response shape

When the cutoff happens after a full approve-level review was drafted but before posting:

- Say the PR is **unfinished**.
- Say `GitHub action: none / no formal review posted`.
- Include the current reviewed head and drafted body path.
- Include completed reviewer lanes and validation results only as proposed evidence, not as a completed GitHub action.
- Say final live queue clearance was not re-verified.
- If a PR-specific Discord channel was created/reused but no final result was sent there, say so explicitly.

Do not label the PR as `approved` in user-facing status unless the pulls reviews API confirms the formal Poom approval on the current head. Use wording such as `proposed verdict: APPROVE; posting/reporting unfinished`.

## Recovery run checklist

1. Re-fetch live PR metadata and sample `headRefOid` immediately.
2. Re-query pulls reviews API and duplicate-gate using the current head + Poom formal decisions.
3. If another run already posted the current-head Poom decision, do not duplicate it; report the verified review id/commit and update memory.
4. If no current-head Poom decision exists and the head still matches the drafted review body evidence, optionally do a narrow freshness check (checks/reviews/comments/threads) before posting the saved body.
5. Submit the formal review using the saved full body, then verify via pulls reviews API.
6. Update review memory with actual review id/state/commit/submitted timestamp and process snapshot.
7. Send the required per-PR Discord result, then parent/fallback index update.
8. Re-list the live queue before claiming queue clearance.

## Example artifact paths

A typical interrupted run may leave:

- `reviewer_prompt.md`
- `rmux/codex.out`
- `rmux/claude.out`
- `review_body.md`
- `live-prepost-*.json`
- `live-reviews-prepost.json`

Treat these artifacts as hints. The recovery run still needs a fresh live head/duplicate check before posting.
