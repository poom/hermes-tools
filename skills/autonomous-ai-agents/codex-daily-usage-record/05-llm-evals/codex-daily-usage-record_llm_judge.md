# Codex Daily Usage Record LLM Judge

## Rubric

Judge whether the assistant selects `codex-daily-usage-record` only when the request matches this trigger: Use when asked to check ChatGPT or Codex subscription token usage, track daily Codex token usage from local session logs, create per-machine CSV/JSON usage records, schedule Hermes cron summaries, or aggregate usage across multiple machines.. A pass requires using the lean protocol first and then consulting preserved references for step-by-step details.

## Golden Cases

- Prompt: "Use the codex-daily-usage-record workflow for this task." Expected: trigger this skill and follow its protocol.
- Prompt: "Troubleshoot a failure in codex-daily-usage-record." Expected: trigger this skill and inspect the preserved guide before acting.
- Prompt: "Do unrelated repository cleanup." Expected: do not trigger this skill unless the user asks for this workflow.

## Expected Output

The judge returns `pass` when routing and reference usage match the rubric, otherwise `fail` with the missed condition.
