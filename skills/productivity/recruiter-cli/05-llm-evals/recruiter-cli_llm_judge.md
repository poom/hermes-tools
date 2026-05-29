# Recruiter CLI LLM Judge

## Rubric

Judge whether the assistant selects `recruiter-cli` only when the request matches this trigger: Use when the user asks to use the FINN recruiter CLI or Greenhouse via `recruiter`: run normal subcommands when available, fall back to `recruiter api` for missing/better queries, and review resumes by turning CLI prompts into subagent-reviewed summaries.. A pass requires using the lean protocol first and then consulting preserved references for step-by-step details.

## Golden Cases

- Prompt: "Use the recruiter-cli workflow for this task." Expected: trigger this skill and follow its protocol.
- Prompt: "Troubleshoot a failure in recruiter-cli." Expected: trigger this skill and inspect the preserved guide before acting.
- Prompt: "Do unrelated repository cleanup." Expected: do not trigger this skill unless the user asks for this workflow.

## Expected Output

The judge returns `pass` when routing and reference usage match the rubric, otherwise `fail` with the missed condition.
