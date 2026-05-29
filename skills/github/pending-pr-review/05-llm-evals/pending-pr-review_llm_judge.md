# Pending PR Review LLM Judge

## Rubric

Judge whether the assistant selects `pending-pr-review` only when the request matches this trigger: Use when Poom asks to review pending PRs, check the review queue, batch-review open GitHub PRs awaiting review, or recover missing submitted GitHub review decisions from saved review memory; lists pending PRs and runs pr-review-guardrails for each PR with one user-facing message/thread per PR.. A pass requires using the lean protocol first and then consulting preserved references for step-by-step details.

## Golden Cases

- Prompt: "Use the pending-pr-review workflow for this task." Expected: trigger this skill and follow its protocol.
- Prompt: "Troubleshoot a failure in pending-pr-review." Expected: trigger this skill and inspect the preserved guide before acting.
- Prompt: "Do unrelated repository cleanup." Expected: do not trigger this skill unless the user asks for this workflow.

## Expected Output

The judge returns `pass` when routing and reference usage match the rubric, otherwise `fail` with the missed condition.
