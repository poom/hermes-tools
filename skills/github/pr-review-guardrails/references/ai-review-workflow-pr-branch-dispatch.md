# AI-review workflow PR-branch dispatch pattern

Use this when reviewing a PR that changes the AI review workflow, PR metadata gate, or the reusable workflow callers that produce the `finn-ai-coder / review` check.

## Why

For `issue_comment` triggers, GitHub Actions often evaluates the workflow file from the base/default branch. If the PR itself changes the workflow caller, a comment such as `@finn-codex please review` can be skipped or can exercise stale base-branch logic. This can leave the metadata gate failing with "missing AI review" even though a comment was posted.

If the PR branch contains a `workflow_dispatch` entry on the review workflow, dispatch the workflow on the PR head branch explicitly so the changed caller and reusable-workflow inputs are tested at the current PR head.

## Command pattern

```bash
gh workflow run code-review.yaml \
  --repo OWNER/REPO \
  --ref <pr-head-branch> \
  -f provider=codex \
  -f pr_number=<PR_NUMBER> \
  -f trigger_type=pr_comment \
  -f comment_body='@finn-codex please review the current diff and record the verdict.' \
  -f comment_author=<author-or-reviewer> \
  -f comment_id='' \
  -f file_path='' \
  -f line_number='' \
  -f codex_version=0.130.0 \
  -f codex_model=gpt-5.5 \
  -f codex_reasoning_effort=xhigh
```

Then poll and inspect:

```bash
gh run list --repo OWNER/REPO --workflow 'Code Review' \
  --branch <pr-head-branch> --event workflow_dispatch --limit 3 \
  --json databaseId,status,conclusion,createdAt,headSha,displayTitle

gh run view <RUN_ID> --repo OWNER/REPO --json status,conclusion,url,jobs

gh pr checks https://github.com/OWNER/REPO/pull/<PR_NUMBER> --watch=false || true
```

If the run fails, inspect failed logs and PR review/comments:

```bash
gh run view <RUN_ID> --repo OWNER/REPO --log-failed \
  | grep -E 'verdict|Verdict|REQUEST|APPROVE|failure|error|::error|finn-ai-coder|review' -C 3

gh api repos/OWNER/REPO/pulls/<PR_NUMBER>/reviews --paginate \
  --jq '[.[] | {id,user:.user.login,state,commit_id,submitted_at,body:(.body[0:500])}] | .[-10:]'

gh api repos/OWNER/REPO/pulls/<PR_NUMBER>/comments --paginate \
  --jq '[.[] | {id,user:.user.login,path,line,body:(.body[0:700]),html_url}] | .[-10:]'
```

## Decision rule

- A current-head `REQUEST_CHANGES` from `finn-ai-coder[bot]` or an inline blocker from the workflow-dispatched review is a real blocker. Do not proceed with an "everything looks good" ping/request until it is resolved.
- A newer metadata-gate follow-up passing can supersede an older "missing AI review" metadata failure, but it does not supersede an active failed `finn-ai-coder / review` check or current `CHANGES_REQUESTED` review decision.
- When user instructions are conditional (e.g. "if everything looks good, mention Jai"), do not post the mention if the workflow-dispatched review finds a blocker.

## Example observed blocker

In a google-workspace handoff PR, local/manual review found zero content diff from the source PR and checks mostly passed. A PR-branch `workflow_dispatch` codex review then found that `.github/workflows/code-review.yaml` dropped `pull_request.ready_for_review`, meaning draft PRs marked ready would stop automatically triggering AI review. The resulting `finn-ai-coder / review` failed and submitted `CHANGES_REQUESTED`; the correct outcome was to report the blocker and not ping Jai yet.
