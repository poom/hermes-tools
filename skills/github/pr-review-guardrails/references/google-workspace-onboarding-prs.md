# Google Workspace onboarding PRs

Use this reference when reviewing Terraform PRs in `EWA-Services/google-workspace` that add a new employee/user and Google Workspace group memberships.

## Approve-level checklist

1. **Ticket/PR data consistency**
   - Read the linked Linear ticket (usually `ITO-###`) from the PR body/title/comments.
   - Match name, role/title, department, location/country, personal email, phone, hiring manager / joining notes when present.
   - Confirm the `users_data.tf` entry derives the expected primary email (`<alias>@ewa-services.com`) and is active/non-imported unless the PR is explicitly an import.

2. **Constants and group membership**
   - If a new location code is added to `constants.tf`, verify it is alphabetically placed and used by the user entry.
   - Verify user/group lists are kept in the repo's existing order. In this repo the relevant checks are commonly alias/email ordering for group member lists and surrounding user-data order in `users_data.tf`.
   - Check for duplicate active primary aliases and duplicate group/member entries.

3. **Plan safety**
   - Inspect the latest Digger/Terraform plan, not just the source diff.
   - Expected net-new onboarding plan shape is usually: create `googleworkspace_user`, create initial `random_password`, create intended group memberships, and zero destroys.
   - Unrelated in-place metadata/normalization drift can be approve-level when it is clearly documented by the author, non-destructive, and does not suspend users/remove access. Still call it out as a process/apply caveat.
   - Do not approve unexplained unrelated destroys, suspensions, group removals, or privilege/owner changes.

4. **Workflow/process gates**
   - Treat `Check Restricted Super-Admin Words` as a process gate if it fires only because `constants.tf` was touched and the file already contains `SUPER_ADMIN`; require the authorized override path rather than making the onboarding diff itself request-changes.
   - If an approval triggers a rerun and the restricted-word check still fails, report `Approved (blocked)` / process-blocked rather than reversing code approval.
   - `policy-bot` approvals and `digger apply` are process gates; distinguish them from code/data blockers.

5. **Linear linkback workflow edits**
   - A narrow semantic-PR workflow change that accepts both `linear[bot]` and `linear-code[bot]` as valid Linear linkback commenters is backwards-compatible and low risk when scoped only to comment detection.

## Example approve summary wording

```text
The onboarding data matches the linked Linear ticket, ordering is now correct, and the latest Digger plan is non-destructive. I approve the code/data changes. Merge/apply remains blocked by process gates: restricted-word override, policy-bot approval, and digger apply.
```
