# Terraform bootstrap apply trigger PRs

Use this when a PR intentionally makes a tiny docs/comment/no-op Terraform-adjacent change so Digger can detect a project and produce/apply a Terraform plan for infrastructure code that was already merged earlier but was not applied.

## Pattern observed

In `EWA-Services/Statement-Service` PR #1138, a prior PR (#1137 / BE-2936) had already merged the production version bump for `risk-evaluation-v0.6.0`, but the first production apply that creates `RiREDACTED_SECRET_PATTERN` had not happened. The follow-up PR only added `Risk-Evaluation/README.md` and changed Terraform comment punctuation so Digger would generate a production plan/apply context.

## Review handling

1. Treat the PR as a Terraform rollout/apply-safety review, not as a normal docs-only PR.
2. Verify the PR body/user context explains why a no-op/docs/comment touch is needed (for example: prior infra PR merged but apply was missed or release workflow rejected first-create resources).
3. Read the linked ticket and earlier merged PR to confirm the intended resources/version.
4. Inspect the latest Digger plan comments/status, not just checks:
   - The target environment should show the expected creates/updates.
   - Other environments may legitimately be `0 add / 0 change / 0 destroy` if already bootstrapped.
5. Compare the plan to the ticket scope:
   - Expected bootstrap creates are usually OK when they match the earlier reviewed infra design.
   - Zero destroys/replacements is the conservative approve-level signal.
   - In-place policy updates are OK when they only add deployment permissions for the newly bootstrapped artifact/function/repository.
6. Explicitly check there is no premature cutover if the ticket says traffic stays on the old path until a follow-up:
   - grep/inspect plan for API Gateway, event source mappings, Lambda permissions, receiver/trigger resources, queue changes, or route/integration updates.
   - A sender IAM policy for the new function is not itself a traffic cutover.
7. Reclassify prior blockers as resolved when the new plan evidence now matches the PR intent. Do not repeat old `No projects impacted` or missing-evidence blockers after a current plan shows the intended resources.
8. Separate code/Terraform safety approval from process state. GitHub may still show `CHANGES_REQUESTED` or policy-bot blocked because another reviewer has an active review or stale AI-review check remains; report that as merge/process readiness, not a code blocker.

## Approve-level wording

```markdown
I re-reviewed this as a safe Digger apply-context PR. The current diff is docs/comment-only, and the latest production Digger plan now shows the intended bootstrap resources (`N add / M change / 0 destroy`) rather than `No projects impacted`. The creates/updates match the linked ticket and earlier merged PR, and I do not see any cutover resources such as API Gateway/SQS event-source/receiver changes. From code/Terraform safety, this is safe to approve; any remaining GitHub blocked state is process/check refresh or another active review.
```
