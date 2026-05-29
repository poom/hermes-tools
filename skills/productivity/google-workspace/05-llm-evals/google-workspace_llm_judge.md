# Google Workspace LLM Judge

## Rubric

Judge whether the assistant selects `google-workspace` only when the request matches this trigger: Gmail, Calendar, Drive, Docs, Sheets via gws CLI or Python.. A pass requires using the lean protocol first and then consulting preserved references for step-by-step details.

## Golden Cases

- Prompt: "Use the google-workspace workflow for this task." Expected: trigger this skill and follow its protocol.
- Prompt: "Troubleshoot a failure in google-workspace." Expected: trigger this skill and inspect the preserved guide before acting.
- Prompt: "Do unrelated repository cleanup." Expected: do not trigger this skill unless the user asks for this workflow.

## Expected Output

The judge returns `pass` when routing and reference usage match the rubric, otherwise `fail` with the missed condition.
