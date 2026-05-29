# PR Review Guardrails LLM Judge

## Rubric

Judge whether the assistant selects `pr-review-guardrails` only when the request matches this trigger: Use when reviewing GitHub pull requests with strict clean-code, SOLID, feature-flag, experiment-outcome, Terraform-plan, coverage, CI, missing-review-decision recovery, and GitHub posting guardrails; runs dual reviewers with GPT-5.5 plus direct Claude CLI and routes results back to the originating Discord thread or Telegram topic.. A pass requires using the lean protocol first and then consulting preserved references for step-by-step details.

## Golden Cases

- Prompt: "Use the pr-review-guardrails workflow for this task." Expected: trigger this skill and follow its protocol.
- Prompt: "Troubleshoot a failure in pr-review-guardrails." Expected: trigger this skill and inspect the preserved guide before acting.
- Prompt: "Do unrelated repository cleanup." Expected: do not trigger this skill unless the user asks for this workflow.

## Expected Output

The judge returns `pass` when routing and reference usage match the rubric, otherwise `fail` with the missed condition.
