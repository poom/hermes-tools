---
name: pickup-linear-ticket
description: "Use when Poom asks to pick up, implement, or ship a Linear ticket end-to-end: read the Linear ticket and linked Notion/Linear references, implement behind feature flags or experiments, run internal PR-style review loops, open a draft GitHub PR from the default template, mention @finn-codex, process feedback, and mark the PR ready only when no issues remain."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [linear, github, pull-request, feature-flags, experiments, implementation, review-loop]
    related_skills: [linear, notion, github-pr-workflow, requesting-code-review, pr-review-guardrails]
required-skills: [linear, notion, github-pr-workflow, requesting-code-review, pr-review-guardrails]
required-binaries: [git, gh, python3]
required-env: [LINEAR_API_KEY]
---

# Pick Up Linear Ticket

## Overview

Use this skill to take a Linear ticket from intake to PR-ready. The workflow is intentionally conservative: understand all linked context first, implement the smallest ticket-scoped change behind the correct feature flag or experiment guard, run internal review before asking external automation, then iterate on feedback until the PR is ready.

The PR should start as a draft. Only mark it ready after `@finn-codex` and review/check feedback are clean or explicitly non-blocking.

For Discord coordination, prefer **one ticket = one dedicated topic/channel** under the `tickets` category when tooling/permissions allow it. Use a stable name based on the ticket identifier and title slug, such as `FINN-123-short-ticket-title`, truncated to a Discord-safe length. Put all progress, review-loop notes, PR links, and final status for that ticket in that lane instead of scattering updates across general channels.

## When to Use

Use when the user says things like:

- "Pick up FINN-123"
- "Implement this Linear ticket"
- "Take this ticket to PR"
- "Do the Linear ticket and ask finn-codex to review"
- "Ship this behind a feature flag / experiment"

Do not use for:

- Pure PR review requests where no implementation is needed; use `pr-review-guardrails`.
- Creating or triaging tickets only; use `linear`.
- Tiny local edits where the user explicitly says not to open a PR.

## Workflow

### 1) Resolve the ticket and linked context

1. Load/use the `linear` skill.
2. Fetch the Linear ticket by identifier or URL using the best available path: Linear CLI, `mcporter linear-finn` MCP tooling, or direct Linear GraphQL. Prefer GraphQL when a complete issue+comments+relations snapshot is needed.
3. Read the full ticket:
   - title and description
   - acceptance criteria / DoD
   - labels, project, team, priority
   - assignee/state
   - comments and attachments
   - linked PRs, related Linear issues, parent/child issues
   - links to Notion, docs, Figma, GrowthBook, dashboards, or other refs
4. Follow all relevant links before coding:
   - Linear references: fetch related issue details and comments.
   - Notion links: use the `notion` skill/API if `NOTION_API_KEY` is available; otherwise open/read any publicly reachable page or ask for access only if the content is required and inaccessible.
   - GitHub links: inspect related PRs/issues/diffs for precedent.
5. Produce a short implementation brief before editing:
   - ticket summary
   - exact acceptance criteria
   - files/components likely involved
   - feature flag / experiment requirement
   - test plan
   - unresolved questions or blocked access

Useful Linear query shape:

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ issue(id: \"FINN-123\") { id identifier title description url priority state { name type } assignee { name email } team { key } project { name url } labels { nodes { name } } comments { nodes { body user { name } createdAt } } relations { nodes { relatedIssue { identifier title url state { name type } } } } attachments { nodes { title url } } } }"}' \
  | python3 -m json.tool
```

Always check the GraphQL `errors` array; HTTP 200 can still be a failed Linear query.

### 2) Create or reuse the ticket topic/channel

After the ticket title is known, create or reuse a dedicated Discord text channel under the `tickets` category. Do **not** require the user to create the category manually first: the helper creates or reuses the category automatically.

Use the bundled helper from this skill directory:

```bash
python3 scripts/discord_ticket_channels.py ensure \
  --source-channel-id <current-discord-channel-or-thread-id> \
  --ticket-id FINN-123 \
  --title "Add checkout eligibility" \
  --linear-url "https://linear.app/finn/issue/FINN-123/add-checkout-eligibility" \
  --category-name tickets
```

The helper is idempotent and prints JSON with `channel_id`, `name`, `action`, and `category_created`.

What the helper does:

1. Reads `DISCORD_BOT_TOKEN` from the environment or `~/.hermes/.env` without printing it.
2. Fetches the source channel/thread to identify the Discord guild.
3. Finds a category named `tickets` case-insensitively, or creates it if missing.
4. Builds the channel name as:

   ```text
   <ticket-id-lowercase>-<slugified-title>
   ```

   Examples:

   ```text
   finn-123-add-checkout-eligibility
   fe-2470-redirect-authenticated-users-away-from-landing-page
   ```

5. Searches the guild for an existing text channel whose name starts with the ticket ID, preferring one already under `tickets`.
6. If found, reuses it, renames it to the canonical name if needed, moves it under `tickets`, and refreshes the topic.
7. If missing, creates a new text channel under `tickets` with a managed topic containing the ticket ID/title/Linear URL.

After a successful `ensure`, post the initial status into the returned channel:

```text
Ticket: <TICKET-ID> — <title>
Linear: <url>
Status: picked up / reading context
Plan: <one-line implementation plan or "reading Linear/Notion/GitHub context first">
```

Use `send_message` with target `discord:<channel_id>` for that initial post and all later ticket updates.

Rules:

- One Linear ticket = one Discord ticket channel.
- Category name: `tickets`.
- Reuse by ticket ID; never create duplicates for the same ticket.
- Send ticket progress, implementation notes, internal review summaries, PR URL, `@finn-codex` status, and final ready status there.
- If Discord creation fails because the token/tooling/permissions are unavailable, continue in the origin conversation and briefly report the exact limitation; do not block implementation only because Discord lane creation failed.

### 3) Prepare a clean implementation branch

1. Check repo status first. Do not mix unrelated local changes into the ticket branch.
2. Sync the base branch.
3. Create a ticket-scoped branch.

```bash
git status --short
git fetch origin
git checkout main && git pull --ff-only origin main
git checkout -b "feat/FINN-123-short-ticket-slug"
```

If the repo uses `master`, `develop`, or another base, use the repo's actual default/base branch from `gh repo view --json defaultBranchRef` or existing project convention.

### 4) Implement with feature flag / experiment safety

Default rule: new user-visible or behavior-changing code must be gated unless the ticket explicitly says no flag is needed.

Implementation rules:

- Prefer the repo's existing feature flag or experiment framework; do not invent a parallel system.
- If the ticket names a flag/experiment, use that exact key and check existing rollout conventions.
- Before coding against a flag, inspect existing nearby flag usage and generated helpers. If the repo uses generated experiment-key services, inject/use that wrapper rather than calling the low-level experiment service directly from feature code.
- Flag OFF must preserve current behavior.
- Flag ON must implement only the ticket-scoped behavior.
- For experiments, preserve assignment/exposure semantics and document the intended outcome if integrating or removing experiment logic.
- Add or update tests for both critical paths:
  - flag/experiment OFF or control path
  - flag/experiment ON or treatment path
- Add a defensive fallback when a flag lookup can fail and safe behavior is to preserve the old path.
- Avoid broad refactors unless they are necessary for the ticket.
- Keep commits focused and reviewable.

FINN-Web-App note: GrowthBook flags should follow the generated experiment-key service convention. For guard/one-shot decisions, do not consume immediate fallback emissions before GrowthBook is ready; use a ready-gated wrapper and add a cold-start spec. See `references/finn-web-app-growthbook-and-push-fallbacks.md` for the FE-2470 pattern, guard readiness caveat, and the `.mise`/schematic caveat.

Before moving on, run the most relevant tests/lints locally. If the full suite is too expensive or dependencies are unavailable, run targeted tests and record the limitation plus the remote CI expectation.

### 5) Internal review loop before opening the PR

Run an internal PR-style review before publishing. This is inspired by `pr-review-guardrails`, but it is internal only:

- Do not post GitHub reviews/comments during this internal phase.
- Do not mention `@finn-codex` yet.
- Use the current git diff and ticket brief as review context.
- Check clean code, SOLID, feature-flag safety, experiment correctness, acceptance criteria, tests, migration/rollout risks, and security.
- If practical, use an independent reviewer context (`requesting-code-review` or delegated review) rather than only self-reading.

Minimum internal review checklist:

- [ ] Ticket acceptance criteria are fully covered.
- [ ] Linked Notion/Linear context was considered.
- [ ] New behavior is correctly gated by the flag/experiment.
- [ ] OFF/control behavior is preserved.
- [ ] ON/treatment behavior satisfies the ticket.
- [ ] Tests cover the meaningful paths or a clear reason is documented.
- [ ] No secrets, debug logs, dead code, or unrelated refactors.
- [ ] Local targeted checks pass or limitations are documented.

If the internal review finds issues:

1. Fix only the reported issues.
2. Re-run relevant tests.
3. Run internal review again.
4. Repeat until the internal review is clean or the remaining concern needs user/product clarification.

### 6) Commit and open a draft PR with the default template

1. Stage only ticket-relevant files.
2. Commit with a clear conventional message including the ticket ID.
3. Push the branch.
4. Create a **draft** PR using the repository's default pull request template.

```bash
git status --short
git add <ticket-relevant-files>
git commit -m "feat: implement FINN-123 short ticket title"
git push -u origin HEAD
```

If `git push` hangs repeatedly with no output, do not keep retrying the same command. Inspect for stuck git/ssh processes and compare local/remote refs first. As a last-resort fallback for an already-open GitHub PR branch, use the GitHub Git Data API to create a commit/tree and move the branch ref, then immediately `git fetch` and `git reset --hard origin/<branch>` so local state matches the real PR head. See `references/finn-web-app-growthbook-and-push-fallbacks.md` for the proven sequence.

Find the default PR template:

```bash
TEMPLATE=""
for f in \
  .github/pull_request_template.md \
  .github/PULL_REQUEST_TEMPLATE.md \
  PULL_REQUEST_TEMPLATE.md; do
  if [ -f "$f" ]; then TEMPLATE="$f"; break; fi
done
printf '%s\n' "$TEMPLATE"
```

If a template exists, fill it out rather than replacing it with a custom format. Include:

- Linear ticket URL
- Summary of implementation
- Feature flag / experiment behavior
- Test plan with commands run
- Rollout or risk notes
- Screenshots/videos if UI changed and feasible

Create the draft PR:

```bash
gh pr create --draft --title "FINN-123: short ticket title" --body-file /tmp/pr-body.md
```

If the repo has multiple PR templates, pick the one matching the change type. If unsure, use the default template and note the assumption.

### 7) Mention `@finn-codex` for review

After the draft PR exists, add a PR comment requesting review:

```bash
gh pr comment --body "@finn-codex please review this PR."
```

Then capture the PR URL/number:

```bash
gh pr view --json number,url,title,headRefName,baseRefName,isDraft --jq '{number,url,title,headRefName,baseRefName,isDraft}'
```

### 8) Wait for feedback and classify it

Poll the PR until `@finn-codex`, GitHub reviews, comments, or checks provide a clear result. Avoid silent long-running work: if waiting will take several minutes, send a compact progress update.

Check feedback sources:

```bash
gh pr view --json reviewDecision,reviews,comments,latestReviews,statusCheckRollup
# For inline review comments:
gh api repos/{owner}/{repo}/pulls/{pr_number}/comments --paginate
# For checks:
gh pr checks || true
```

Classify feedback as:

- **Issues found / blocking:** `REQUEST_CHANGES`, failed relevant checks, inline comments requiring code changes, explicit bug/security/test concerns.
- **Non-blocking:** suggestions/nits that do not affect correctness or readiness.
- **No issues:** approval, clean finn-codex result, passing relevant checks, and no unresolved blocking comments.
- **Unclear:** ambiguous bot output or missing review; continue waiting or ask the user only if blocked by access/permissions or product ambiguity.

### 9) If issues are found, fix and return to internal review

When blocking feedback exists:

1. Read every actionable item.
2. Update the implementation.
3. Add/update tests for the fix when appropriate.
4. Run targeted checks.
5. Re-run the internal review loop from step 5.
6. Commit and push the fixes.
7. Reply to/resolve feedback when the tool permits and the fix is verified. For GitHub PR review threads, explicitly query unresolved threads with GraphQL; `gh pr view`/REST review comments can miss unresolved thread state. Resolve only after the code change is pushed or the thread is genuinely obsolete.
8. Ask `@finn-codex` to review again if needed.

```bash
git add <fixed-files>
git commit -m "fix: address FINN-123 review feedback"
git push
gh pr comment --body "@finn-codex addressed the feedback; please re-review."
```

Repeat until feedback is clean or a human/product decision is required.

### 10) If no issues remain, mark the PR ready

Before marking ready:

- Re-fetch the PR state.
- Confirm the current head is the one reviewed.
- Confirm draft status is still true.
- Confirm no blocking review/check/comment remains.
- Confirm the PR body has the ticket link and test plan.

Then mark ready:

```bash
gh pr ready
```

Final response should include:

```text
<repo> #<pr-number> — <title>
<PR URL>
Status: ready for human review
Ticket: <Linear URL>
Flag/experiment: <name or none with reason>
Checks/tests: <summary>
Feedback loop: <clean / fixed N rounds / remaining non-blocking notes>
```

## Common Pitfalls

1. **Coding before reading linked context.** Always follow related Linear/Notion/GitHub references before implementation; many tickets hide the real acceptance criteria in comments or linked docs.
2. **Opening the PR as ready too early.** Start as draft. Mark ready only after internal review and `@finn-codex` feedback are clean.
3. **Forgetting flag OFF behavior.** A feature flag is not enough; verify old behavior remains safe when disabled.
4. **Treating experiment cleanup as a normal refactor.** If integrating/removing experiment logic, require the outcome/source of truth and preserve the winning/control path correctly.
5. **Posting internal review feedback externally.** Internal review should not create GitHub reviews/comments. Only the PR creation and `@finn-codex` request are external by default.
6. **Mixing unrelated local changes.** Use `git status --short` before staging and commit only ticket-relevant files.
7. **Ignoring check failures as bot noise.** Inspect failed checks enough to distinguish stale/process failures from real implementation problems.
8. **Marking ready while review feedback is unresolved.** Re-check comments, reviews, checks, and unresolved review threads immediately before `gh pr ready`. Use GitHub GraphQL `reviewThreads` for thread resolution state; REST inline comments alone do not tell you whether a thread is resolved.
9. **Using the low-level feature flag API when the repo expects generated wrappers.** First inspect existing flag patterns. In FINN-Web-App, use generated GrowthBook experiment-key services in application code; direct `ExperimentService` calls in guards/components are a review risk.
10. **Repeating a hung `git push`.** If push hangs with no output, inspect process/ref state and switch strategy. For GitHub PR branches, the Git Data API can update the branch, but local must be fetch/reset to the API-created head afterward.

## Verification Checklist

- [ ] Linear ticket and comments read.
- [ ] Related Linear issues and Notion/doc references read or access limitation documented.
- [ ] Dedicated ticket topic/channel under `tickets` created or reused, or limitation documented.
- [ ] Implementation branch created from current base.
- [ ] Feature flag / experiment plan identified.
- [ ] Code implemented with flag OFF/control and ON/treatment behavior handled.
- [ ] Relevant tests/lints run and results recorded.
- [ ] Internal review completed with no blocking findings.
- [ ] PR opened as draft using the default PR template.
- [ ] PR body includes Linear link, summary, flag/experiment notes, and test plan.
- [ ] `@finn-codex` mentioned for review.
- [ ] Feedback checked and classified.
- [ ] Blocking feedback fixed, internally re-reviewed, pushed, and re-requested if needed.
- [ ] No blocking feedback/checks remain.
- [ ] PR marked ready.
