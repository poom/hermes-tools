# My Open PRs LLM Judge

## Rubric

Judge whether the assistant selects `my-open-prs` only when the request matches this trigger: Use when tracking the current user's open non-draft GitHub pull requests in ewa-services, posting a PR queue summary to Discord, creating one normal Discord text channel per active PR, keeping per-PR blocker/status channels up to date, reporting merged/closed PRs, deleting the PR channel when closed/merged, and maintaining durable per-PR Markdown status files under <hermes-home>/my-open-prs.. A pass requires using the lean protocol first and then consulting preserved references for step-by-step details.

## Golden Cases

- Prompt: "Use the my-open-prs workflow for this task." Expected: trigger this skill and follow its protocol.
- Prompt: "Troubleshoot a failure in my-open-prs." Expected: trigger this skill and inspect the preserved guide before acting.
- Prompt: "Do unrelated repository cleanup." Expected: do not trigger this skill unless the user asks for this workflow.

## Expected Output

The judge returns `pass` when routing and reference usage match the rubric, otherwise `fail` with the missed condition.
