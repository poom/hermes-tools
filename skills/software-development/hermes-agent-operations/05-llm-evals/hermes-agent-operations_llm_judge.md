# Hermes Agent Operations LLM Judge

## Rubric

Judge whether the assistant selects `hermes-agent-operations` only when the request matches this trigger: Operate and maintain a live Hermes Agent install: gateway runtime debugging, config/env drift triage, skill library syncing, backups, symlinks, and machine-specific cron/config restore.. A pass requires using the lean protocol first and then consulting preserved references for step-by-step details.

## Golden Cases

- Prompt: "Use the hermes-agent-operations workflow for this task." Expected: trigger this skill and follow its protocol.
- Prompt: "Troubleshoot a failure in hermes-agent-operations." Expected: trigger this skill and inspect the preserved guide before acting.
- Prompt: "Do unrelated repository cleanup." Expected: do not trigger this skill unless the user asks for this workflow.

## Expected Output

The judge returns `pass` when routing and reference usage match the rubric, otherwise `fail` with the missed condition.
