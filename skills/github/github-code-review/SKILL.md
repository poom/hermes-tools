---
name: github-code-review
description: Use when applying the GitHub Code Review skill workflow: Review PRs: diffs, inline comments via gh or REST. Triggered by requests mentioning github-code-review, GitHub Code Review, setup, operation, troubleshooting, review, or automation for this workflow.
version: 1.1.0
license: MIT
metadata:
  hermes:
    tags: [GitHub, Code-Review, Pull-Requests, Git, Quality]
    related_skills: [github-auth, github-pr-workflow]
---
# GitHub Code Review

## Protocol

1. Use this skill only when the user request matches the trigger description or explicitly names `github-code-review`.
2. Read the linked references before taking action; they preserve the detailed step-by-step procedures from the previous guide.
3. Prefer deterministic scripts for repeatable validation and use the documented smoke command before live side effects.
4. If credentials, network access, or external systems are required, run the offline checks first and then ask for or verify the required access.
5. Keep new operational detail in `references/` and keep `SKILL.md` focused on routing, protocol, and failure behavior.

## References

- [Pr Review Finalization](references/pr-review-finalization.md) - preserved detailed guidance or domain-specific operations.
- [Preserved Skill Guide](references/preserved-skill-guide.md) - preserved detailed guidance or domain-specific operations.
- [Review Output Template](references/review-output-template.md) - preserved detailed guidance or domain-specific operations.
- [Review Verification Pitfalls](references/review-verification-pitfalls.md) - preserved detailed guidance or domain-specific operations.

## Scripts

- `scripts/skill_health.py` - deterministic support or offline coverage for this skill.
- `scripts/test_skill_health.py` - deterministic support or offline coverage for this skill.

## Failure Behavior

- If the request does not match this skill, do not force the workflow; use the more specific skill or normal repo process.
- If a referenced command cannot run because credentials or live endpoints are unavailable, report the blocked check and continue with offline evidence.
- If the preserved guide conflicts with current repository state, verify the live files first and update the relevant reference before proceeding.
