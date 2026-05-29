# Systematic Debugging LLM Judge

## Rubric

Judge whether the assistant selects `systematic-debugging` only when the request matches this trigger: 4-phase root cause debugging: understand bugs before fixing.. A pass requires using the lean protocol first and then consulting preserved references for step-by-step details.

## Golden Cases

- Prompt: "Use the systematic-debugging workflow for this task." Expected: trigger this skill and follow its protocol.
- Prompt: "Troubleshoot a failure in systematic-debugging." Expected: trigger this skill and inspect the preserved guide before acting.
- Prompt: "Do unrelated repository cleanup." Expected: do not trigger this skill unless the user asks for this workflow.

## Expected Output

The judge returns `pass` when routing and reference usage match the rubric, otherwise `fail` with the missed condition.
