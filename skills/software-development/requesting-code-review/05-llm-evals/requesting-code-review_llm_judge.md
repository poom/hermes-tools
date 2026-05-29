# Pre-Commit Code Verification LLM Judge

## Rubric

Judge whether the assistant selects `requesting-code-review` only when the request matches this trigger: Pre-commit review: security scan, quality gates, auto-fix.. A pass requires using the lean protocol first and then consulting preserved references for step-by-step details.

## Golden Cases

- Prompt: "Use the requesting-code-review workflow for this task." Expected: trigger this skill and follow its protocol.
- Prompt: "Troubleshoot a failure in requesting-code-review." Expected: trigger this skill and inspect the preserved guide before acting.
- Prompt: "Do unrelated repository cleanup." Expected: do not trigger this skill unless the user asks for this workflow.

## Expected Output

The judge returns `pass` when routing and reference usage match the rubric, otherwise `fail` with the missed condition.
