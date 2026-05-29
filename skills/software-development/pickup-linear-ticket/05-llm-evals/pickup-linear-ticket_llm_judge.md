# Pick Up Linear Ticket LLM Judge

## Rubric

Judge whether the assistant selects `pickup-linear-ticket` only when the request matches this trigger: Use when Poom asks to pick up, implement, or ship a Linear ticket end-to-end: read the Linear ticket and linked Notion/Linear references, implement behind feature flags or experiments, run internal PR-style review loops, open a draft GitHub PR from the default template, mention @finn-codex, process feedback, and mark the PR ready only when no issues remain.. A pass requires using the lean protocol first and then consulting preserved references for step-by-step details.

## Golden Cases

- Prompt: "Use the pickup-linear-ticket workflow for this task." Expected: trigger this skill and follow its protocol.
- Prompt: "Troubleshoot a failure in pickup-linear-ticket." Expected: trigger this skill and inspect the preserved guide before acting.
- Prompt: "Do unrelated repository cleanup." Expected: do not trigger this skill unless the user asks for this workflow.

## Expected Output

The judge returns `pass` when routing and reference usage match the rubric, otherwise `fail` with the missed condition.
