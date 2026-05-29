# IAM/team membership access PR reviews

Use this for small `user-iam`/team membership PRs that add a person to a YAML team file and thereby grant cloud access through existing team wiring.

## Checklist

1. **Refresh live PR state first**: head SHA, diff, checks, comments/reviews, review threads, and pulls reviews API. In parent-delegated mode, do not post; return the proposed review action/body for the parent.
2. **Confirm data-shape invariants**:
   - Changed file(s) are limited to the intended team membership YAML unless the PR claims broader scope.
   - New login is in the intended list (`users` vs `powerusers`/`administrators`).
   - Lists remain valid YAML, sorted if the repo convention is sorted, and duplicate-free.
   - Search/parse all team files to verify the login is not unintentionally added to multiple teams or privilege tiers.
3. **Trace inherited permissions, not just the line diff**:
   - For AWS, inspect the team's included accounts and the relevant managed/custom policy mapping files for each included account.
   - For GCP, inspect included projects and group/poweruser role wiring where applicable.
   - Explicitly call out inherited admin/elevated access when normal team membership implies it. This is not automatically a code blocker if the PR/ticket/description clearly disclose it and the required human/policy approver must sign off.
4. **Ticket consistency**:
   - Fetch the live Linear ticket when possible. Prefer the live ticket over stale GitHub linkback comments copied from an older ticket.
   - If a stale linkback mentions broader access but the live ticket has been narrowed and comments split the remaining access into a separate ticket, treat the live ticket + PR body as authoritative evidence; mention the stale linkback only as context.
5. **Prior blocker ledger**:
   - Old blockers for title/metadata/AI disclosure/missing Digger plans can be stale after a new head or PR-body update. Re-check current title, checks, plans, and review threads before carrying them forward.
   - If an inline blocker says the team grant includes unexpected admin access, classify an updated PR body that explicitly acknowledges inherited admin access as a credible resolution when current code evidence matches.
6. **Digger / Terraform evidence**:
   - Review current Digger plan comments/checks for the relevant projects, not only source diff.
   - For a simple user grant, approve-level evidence is normally: intended IAM user, group membership, and login profile additions in the expected accounts; zero destroys; unrelated drift either absent or explained.
   - Remember repo guidance may still require Digger apply before merge; treat that as a process gate unless the plan itself shows a code/data risk.
7. **Local validation**:
   - `git diff --check origin/<base>...HEAD`.
   - Parse team YAML and relevant JSON policy files.
   - Validate ordering/duplicates and the new user's repo-wide membership occurrence.
   - If local pre-commit or gpg is unavailable, rely on remote passing checks / GitHub commit verification and record the limitation without turning it into a blocker.

## Approval wording pattern

When safe, scope the approval carefully:

- Approve the current YAML/data change and current-head evidence.
- State that policy-bot/human approval and Digger apply/completion remain separate process gates.
- Avoid saying the PR is fully merge-ready if `policy-bot`, stale review decisions, or Digger apply are still pending.

## Parent-delegated output pitfall

If no current-head `poom` formal decision exists, propose a complete `APPROVE`/`REQUEST_CHANGES` body for the parent. If a current-head `poom` decision appears during final verification, report it and do not propose duplicate posting unless the parent explicitly wants to supersede it.
