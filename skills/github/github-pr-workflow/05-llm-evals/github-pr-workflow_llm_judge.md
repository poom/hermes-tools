# GitHub Pull Request Workflow LLM Judge

## Rubric

Judge whether the assistant selects `github-pr-workflow` only when the request matches this trigger: GitHub PR lifecycle: branch, commit, open, CI, merge.. A pass requires using the lean protocol first and then consulting preserved references for step-by-step details.

## Golden Cases

- Prompt: "Use the github-pr-workflow workflow for this task." Expected: trigger this skill and follow its protocol.
- Prompt: "Troubleshoot a failure in github-pr-workflow." Expected: trigger this skill and inspect the preserved guide before acting.
- Prompt: "Do unrelated repository cleanup." Expected: do not trigger this skill unless the user asks for this workflow.

## Expected Output

The judge returns `pass` when routing and reference usage match the rubric, otherwise `fail` with the missed condition.
