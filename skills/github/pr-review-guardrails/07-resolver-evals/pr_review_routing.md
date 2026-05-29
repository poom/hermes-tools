# PR review guardrails resolver evals

These cases prove the skill resolver routes realistic requests correctly.

Should trigger / routes to this skill:
- “review this PR https://github.com/EWA-Services/repo/pull/123”
- “re-review PR #123 and request changes if blockers remain”
- “check this Terraform PR for plan safety”
- “the last run wrote memory but did not submit the GitHub review; recover the missing decision”
- “guardrail review this feature-flag experiment cleanup PR”

Should not trigger:
- “review all pending PRs in my queue” → `pending-pr-review`
- “create a GitHub issue” → GitHub issue skill
- “summarize this blog post” → research/content skill
