# Terraform Grafana SLO PRs with missing Digger plan

Use this when reviewing Terraform PRs that add or change Grafana SLO resources, dashboards, alert rules, or observability infrastructure, but no current Digger/Terraform plan is available because Digger failed, was locked by another PR, or the runner/tooling is unavailable locally.

## Pattern observed

In `EWA-Services/monitoring-infrastructure` PR #316, the diff added six BigQuery-backed Grafana SLO configs for ID-card OCR correctness/latency (PH/TH/ZA) through the existing `modules/grafana-slo` module. Source review found no code-level blocker and CI/pre-commit passed, but the only Digger staging comment failed before planning because the project was locked by another PR (`failed to acquire lock staging`). Local `terraform`, `tofu`, and `tflint` were also unavailable on the macOS host.

## Review handling

1. Do the normal Terraform source review anyway:
   - Read the PR body, linked ticket, comments, review threads, and checks.
   - Inspect the changed SLO/dashboard/rule files plus the reused module contract.
   - Verify labels, destination/query datasources, targets/windows, country/service scope, and ticket alignment.
2. Inspect Digger comments and run logs explicitly. A passing generic `request` job can just mean the Digger guide/comment was posted; it is not plan evidence.
3. If the latest Digger comment says lock acquisition failed or no plan was produced, classify the source diff separately from merge readiness:
   - `source_review`: no blocker / findings as applicable.
   - `merge_readiness`: not approve-ready until a current-head plan is posted and inspected.
4. For parent-delegated/no-posting lanes, propose `COMMENT` rather than `APPROVE` when the only blocker is missing plan evidence. Do not overstate this as a code defect; it is an infra-review evidence gap.
5. If local Terraform tooling is missing, record exact unavailable commands and rely on remote CI only for syntax/pre-commit, not for plan safety.
6. Required approval evidence before switching to approve-level:
   - A fresh Digger/Terraform plan for the current head SHA.
   - Expected SLO/dashboard/rule create/update count matches the PR scope.
   - Zero unexplained destroys/replacements and no destructive unrelated drift.
   - Any unrelated in-place drift is documented as an operational caveat, not silently ignored.

## Re-review after source fixes + plan appears

When the author pushes a new head that addresses source-level SLO blockers and later posts a successful Digger plan, do a focused re-review rather than repeating the stale request-changes verdict:

1. Re-read the author reply and classify it under the normal author-reply rules. For this class, a reply is usually **clear + credible** when it states exactly how the latency denominator, latest-row/terminal selection, and window/filter semantics changed, and the current code matches those statements.
2. Verify the old inline thread state through review threads. If the old comment is resolved/outdated and the current diff no longer contains the offending predicate, do not duplicate the inline comment.
3. Compare the old requested-change head to the current head for the SLO file. For BigQuery-backed OCR SLOs, approve-level evidence includes:
   - latency `Total` keeps the same valid completed-attempt population as `Success` without excluding worst-tail values such as `>= 3600s`;
   - correctness and latency use a latest-row selection such as `ROW_NUMBER() OVER (PARTITION BY document_name ORDER BY timestamp DESC)` plus `update_rank = 1` so intermediate Firestore `UPDATE` rows are not counted as separate final states;
   - any SQL rolling-window predicate has an explicit source-scan/window rationale and is applied consistently to `Success` and `Total`.
4. Inspect the fresh current-head Digger plan comments/checks. Expected approve-level shape for adding six country × SLI Grafana SLOs is `+6 / ~0 / -0` for each relevant environment, with no destroys/replacements.
5. If the prior Poom `REQUEST_CHANGES` was on an older head and no current-head Poom decision exists, submit a full current-head formal review after sampling the head immediately before posting. This is not a duplicate review; it is the required current-head decision.
6. Treat `policy-bot`, `digger/apply`, stale metadata-gate rows, or other human/process gates as merge-readiness notes unless the diff or plan itself is unsafe.

## Suggested parent-delegated wording

```markdown
Source review found no code-level blocker in the SLO diff, and the linked ticket/checks line up. However, I would not approve yet because there is no live Digger/Terraform plan for the current head: Digger failed before planning due a project lock. For Terraform-managed Grafana SLO changes, please rerun/inspect the current-head Digger plan and verify it shows the expected SLO additions with no unexplained destroys/replacements before approval/apply/merge.
```
