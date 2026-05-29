# Pending PR review resolver evals

These cases prove the skill resolver routes realistic requests correctly.

Should trigger / routes to this skill:
- “review pending PRs”
- “check Poom’s review queue”
- “batch review open GitHub PRs awaiting my review”
- “the pending queue still returns a PR already reviewed locally; recover the missing GitHub decision”

Should not trigger:
- “review this single PR https://github.com/org/repo/pull/123” → `pr-review-guardrails`
- “create a GitHub issue” → GitHub issue skill
- “summarize a Linear ticket” → Linear skill
