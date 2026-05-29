# Superseding Poom's own current-head REQUEST_CHANGES after new evidence

## Trigger

Use this when the user explicitly asks to re-review a PR and **supersede** Poom's prior current-head `REQUEST_CHANGES` if a missing-evidence blocker is now resolved (for example Digger/Terraform plan output appeared after the prior review).

This is different from the normal duplicate-decision guardrail. A current-head Poom `REQUEST_CHANGES` is usually enough to skip duplicate posting, but an explicit supersede instruction authorizes a fresh formal review on the same commit if the old blocker is stale.

## Workflow

1. Refresh live PR state: head SHA, diff, comments, formal reviews, review threads, checks, and any newly posted evidence.
2. Identify the exact old Poom blocker and confirm it was the reason for the prior `REQUEST_CHANGES`.
3. Verify the new evidence resolves that blocker. For Terraform/Digger cases, inspect the plan summary and plan body, not just the file diff:
   - current head matches the plan/check head;
   - staging/production or relevant projects succeeded;
   - no unexplained destroys/replacements;
   - in-place changes match the authored Terraform diff.
4. Re-run the normal review synthesis, including direct Claude CLI when practical.
5. Immediately before posting, sample the PR head (twice for volatile PRs). Abort/revalidate if it changed.
6. Post a full formal `APPROVE` body that says what was rechecked, why the old blocker is stale/resolved, and any remaining non-code process gates.
7. Verify with the pulls reviews API, not only `gh pr view --json reviewDecision`:
   ```bash
   gh api repos/OWNER/REPO/pulls/PR/reviews --paginate > /tmp/reviews.json
   python3 - <<'PY'
   import json
   head='CURRENT_HEAD_SHA'
   for r in json.load(open('/tmp/reviews.json')):
       if r['user']['login']=='poom' and r.get('commit_id')==head:
           print(r['id'], r['state'], r['submitted_at'], (r.get('body') or '').splitlines()[:1])
   PY
   ```
8. If `reviewDecision` remains `CHANGES_REQUESTED`, check whether another reviewer still has a current-head changes-requested review. Report this as process/human-gate state; do not imply the Poom supersede failed when the pulls reviews API shows a current-head Poom `APPROVED` review.

## Example pattern

In monitoring-infrastructure #319, Poom's current-head `REQUEST_CHANGES` blocked only because Digger plan evidence was missing. Later Digger production and staging plans succeeded on the same head (`+0 ~1 -0`, no destroys/replacements, in-place Grafana rule group update only). The correct action under an explicit supersede request was to post a new formal Poom `APPROVE` on the same head and verify it by review id, while noting that GitHub `reviewDecision` still stayed `CHANGES_REQUESTED` because a separate Jai review had the same stale missing-plan rationale.
