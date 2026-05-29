# Team membership / IAM access data PRs

Use this reference for small PRs that add a person to a team membership file which fans out to IAM, AWS, Google Workspace, or other access grants. Concrete session: `EWA-Services/user-iam#187`, adding `benjamin.t` to `teams/backend.yaml`.

## Review checklist

1. **Scope and ticket consistency**
   - Read the linked ticket from PR title/body/comments.
   - Verify the requested person, username/alias, team, and access domain match the PR diff.
   - If older linkback/comments mention broader access, look for current ticket comments or PR updates that split scope into follow-up tickets before treating the mismatch as a blocker.

2. **Membership data integrity**
   - Parse the changed YAML/JSON data instead of eyeballing indentation.
   - Confirm the user is added to the intended section (for example `users` vs `powerusers`).
   - Check sorted ordering and duplicate entries in the changed list.
   - Search repo-wide for the alias to avoid duplicate membership or accidental addition in multiple team files.

3. **Access inheritance disclosure**
   - Follow the team-to-policy mapping, not just the one-line membership diff.
   - Identify inherited account/environment access and whether it includes privileged policies such as `AdministratorAccess`, write-capable roles, or production access.
   - If the inherited access is broad, require the PR description or an author reply to explicitly disclose the effective access scope or provide a narrower path. A clear, current disclosure plus resolved thread can make an earlier blocker stale.

4. **Plan / generated access evidence**
   - Inspect the latest Digger/Terraform/plan checks when the membership drives generated IAM resources.
   - Approve-level plans show intended user/group/login-profile additions and no unexplained destroys/removals/privilege changes.
   - Treat policy-bot approval, Digger apply, or human access sign-off as process gates unless the current diff itself is wrong.

5. **Prior review thread classification**
   - Re-read prior inline/formal reviews and author replies.
   - Classify stale old-head blockers separately from current-head access-scope issues.
   - If the author fixed the issue by updating the PR description with the effective access scope and the thread is resolved, record it as `clear + credible` rather than repeating the old blocker.

## Approve-level evidence pattern

Approve can be appropriate when:

- The diff is limited to the intended membership addition.
- The alias appears once, in the correct team/list, with ordering preserved.
- The ticket/current PR metadata supports the access request scope.
- Effective inherited privileged access is disclosed or otherwise explicitly accepted.
- Current plan checks show only intended non-destructive additions.
- No unresolved review threads remain except process gates.

## Example approval wording

```text
The membership data is correct, the effective backend AWS access is now disclosed in the PR description, current plan checks show only the intended IAM additions with no destroys, and prior old-head blockers are stale. I approve the code/data change; policy-bot approval and apply remain process gates.
```
