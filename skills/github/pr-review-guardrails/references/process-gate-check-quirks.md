# Process gate / check-status quirks

Use this when a PR review is content-approved but GitHub merge state is blocked by metadata, AI-label, policy-bot, or rerun check noise.

## Duplicate or stale check rows

`gh pr checks` can show multiple rows for the same logical workflow/job after labels, PR body, comments, or reviews trigger reruns. Do not summarize the first failing row as the current state without checking the run timestamps and latest replacement run.

Useful commands:

```bash
gh pr checks PR --repo OWNER/REPO --watch=false > /tmp/checks.txt 2>&1 || true
gh run list --repo OWNER/REPO --branch HEAD_BRANCH --limit 20 \
  --json databaseId,name,status,conclusion,createdAt,updatedAt,headSha
```

If an old failed run and a newer pending/pass run coexist, distinguish:

- content/code-review verdict: approve or request changes based on the diff;
- merge readiness: blocked until required current process gates pass;
- stale/process noise: note only if it still appears in required checks.

## AI Label Check failures after body/label edits

A PR can have the `ai-assisted` label and a `### Workflow trace` section but still fail AI Label Check. Inspect the failed run log rather than guessing from the PR body:

```bash
gh run view RUN_ID --repo OWNER/REPO --log-failed
```

Example failure from EWA-Actions #420:

```text
### Workflow trace must be a readable Markdown bullet list for ai-assisted PRs.
```

Treat this as a process/metadata gate unless the PR's code change is specifically about the AI-label validator. Mention the exact failed validator message in merge readiness. Do not turn a docs/content approval into `REQUEST_CHANGES` solely because the gate is failing, unless the user asked to enforce process gates as review blockers.

## Formal review wording

For approve-level content reviews with pending/failing process gates, submit `APPROVE` when the diff is safe, and include a non-blocking/process note such as:

```text
Current live checks/policy were still partly pending/failing when reviewed, including <gate>. Those are merge/process gates rather than content blockers for this review.
```

Use a final thread status like `Approved (blocked)` when helpful.
