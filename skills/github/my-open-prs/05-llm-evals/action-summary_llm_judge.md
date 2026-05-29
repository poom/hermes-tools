# Action Summary LLM Judge

Use this rubric when the agent rewrites a generic `Needs My Feedback` reason after inspecting GitHub details.

Pass criteria:

- Names the concrete blocker type: changes requested, failing checks, merge conflicts, stale branch, branch protection, or unresolved conversations.
- Includes the reviewer, check name, or branch state when available in the evidence.
- Does not claim a fix that is not present in the evidence.
- Stays one sentence or sentence fragment suitable for a PR bullet.

Add a golden case whenever a real PR summary was too vague or missed the actionable blocker.
