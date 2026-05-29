# Terraform Google Workspace user aliases vs emails

Session-derived review note for Terraform PRs using the Google Workspace provider.

## Durable provider behavior to verify

For `googleworkspace_user`, the provider may surface user aliases and no-type alternate emails in the `emails` list even when they are not explicitly configured there. Provider source around `diffSuppressEmails` explains that user aliases and alternate emails with no `type` can be auto-added to the email list and diff-suppressed when the same address is represented through `aliases`.

Practical implication: a plan that removes alias-like entries from a `googleworkspace_user.emails` block is not automatically an alias deletion if the same addresses are preserved under the provider/resource's alias management (`aliases` / module alias inputs) and the plan shows no net alias removal.

## Review checklist

When reviewing a Google Workspace Terraform import/refactor that moves email aliases between fields:

1. Inspect the current code/module inputs for the authoritative alias field, not just `emails` block changes.
2. Inspect the Digger/Terraform plan for the affected user/group resources.
3. Check that previously called-out aliases appear in the final planned alias set, including domain variants when relevant.
4. Treat remove/add churn or ordering changes separately from net removal.
5. If uncertainty remains, check the provider docs/source for the exact resource behavior before blocking.
6. Separate merge-safety approval from process gates like AI label checks, policy-bot approvals, or apply pending.

## Evidence wording

```text
Alias-like `emails` cleanup is not treated as a deletion blocker because the current code/plan preserves the addresses through `aliases`, and provider behavior auto-surfaces/diff-suppresses alias/no-type emails in `emails`.
```
