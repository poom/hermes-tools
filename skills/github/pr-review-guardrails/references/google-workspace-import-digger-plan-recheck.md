# Google Workspace import PRs: Digger plan recheck after stale alias blockers

Use for `EWA-Services/google-workspace` import/onboarding PR re-reviews when earlier reviews blocked on Digger plan alias/settings drift, but the PR has since been repaired/rebased.

## Pattern

1. **Re-read live PR state first**
   - Fetch PR metadata, current `headRefOid`, comments, formal reviews, inline review threads, current checks, and Digger comments.
   - Query review threads via GraphQL when `gh pr view --json reviewThreads` is unavailable.
   - Treat old inline threads as evidence, but classify them against current head. An unresolved thread can be both `isResolved=false` and `isOutdated=true`; do not repeat it until the current code and current plan prove it still applies.

2. **Use Digger run logs when the plan comment is truncated/too large**
   - Digger may report `failed to post report ... Body is too long (maximum is 65536 characters)` while the underlying plan succeeded.
   - Pull the workflow log from the linked Digger run/check, e.g. `gh run view <run-id> --repo EWA-Services/google-workspace --log > /tmp/gw-plan.log`.
   - Record the plan summary (`N to import, N to add, N to change, 0 to destroy`) and inspect relevant resource snippets from the log rather than relying only on PR comments.

3. **Differentiate real removals from Terraform ordering churn**
   - Terraform list diffs can show the same alias as both removed and added when ordering changes. For example a snippet with `- sales-sa@example.com` and `+ sales-sa@example.com` is not, by itself, a real alias loss.
   - For a prior alias-removal blocker, confirm the source now models the alias and the current plan still retains/adds it.
   - Known prior blocker examples:
     - `users_data.tf` for `david.b` should preserve aliases such as `webmaster`, `dataprotection`, and `vlad.s` as `additional_email_aliases`; the user module expands them to both ewa-services.com and finn-app.com aliases unless disabled.
     - `group_imported_sales` should model `sales-id` and `sales-sa` aliases as well as the intended `sales@example.com` alias.

4. **Check settings drift as well as aliases**
   - Old blockers may include behavior-affecting group settings such as `enable_collaborative_inbox`, `is_archived`, `reply_to`, and `who_can_assist_content`.
   - Verify current code has explicit `# Preserve live settings at import time` overrides for any settings previously identified as live-state preservation requirements.
   - If the plan still has many in-place updates, summarize whether they are import/default capture, explicit intended aliases, ordering churn, or unresolved behavior changes.

5. **Local validation limits**
   - Do not convert missing local Terraform binaries into a review blocker when current remote CI/Digger plan is available. Record it as a local environment limitation and rely on `pre-commit`, restricted words, policy validation, and current Digger plan/checks.

6. **Before posting**
   - Complete Reviewer B via direct Claude CLI over the evidence packet.
   - Re-sample the current head immediately before posting.
   - Verify no current-head Poom decision already exists.
   - If approving after stale blockers, explicitly say the old inline blockers are outdated/stale and why the current plan/code resolves them.
