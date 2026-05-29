# Terraform docs-only PRs with Digger drift

Use this when a Terraform repository PR changes only documentation or agent guidance, but Digger still emits a plan.

## Pattern observed

A docs-only PR adding `AGENTS.terraform.md` in `EWA-Services/google-workspace` had a clean file diff but the latest Digger plan showed unrelated in-place drift:

- `Plan: 0 to add, 2 to change, 0 to destroy`
- one Google Workspace group member `delivery_settings` drift
- one Google Workspace user alias ordering/change

The PR itself did not author Terraform resource changes, and there were no destroys/replacements.

## Review handling

1. Still inspect the latest Digger plan; do not skip it just because the source diff is docs-only.
2. If the plan contains unrelated in-place drift with zero add/destroy/replace:
   - do **not** invent a request-changes blocker solely from the drift;
   - mention it as an operational caveat;
   - recommend not running `digger apply` from the docs-only PR unless the owner confirms the drift is intended or separately resolves it.
3. If the plan contains unrelated creates, destroys, replacements, secret rotations, or identity-sensitive updates, escalate using the normal Terraform plan-safety rules.
4. For agent-guidance docs, re-validate any prior review comments against the current head. If the prior issue was about unsafe Digger unlock advice and the current doc now says to wait/escalate and not unlock another PR's lock, mark it resolved.

## Suggested approve-body wording

```markdown
The docs-only diff is safe, and the prior Digger lock-handling concern is resolved. The latest Digger plan still shows unrelated in-place drift (`0 add, 2 change, 0 destroy`). I would not run `digger apply` from this docs PR unless the repo owner confirms those drift changes are intended.
```
