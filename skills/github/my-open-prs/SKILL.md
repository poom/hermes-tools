---
name: my-open-prs
description: Use when applying the My Open PRs skill workflow: Use when tracking the current user's open non-draft GitHub pull requests in ewa-services, posting a PR queue summary to Discord, creating one normal Discord text channel per active PR, keeping per-PR blocker/status channels up to date, reporting merged/closed PRs, deleting the PR channel when closed/merged, and maintaining durable per-PR Markdown status files under <hermes-home>/my-open-prs. Triggered by requests mentioning my-open-prs, My Open PRs, setup, operation, troubleshooting, review, or automation for this workflow.
required-skills: []
required-binaries:
  - gh
  - python3
---
# My Open PRs

## Protocol

1. Use this skill only when the user request matches the trigger description or explicitly names `my-open-prs`.
2. Read the linked references before taking action; they preserve the detailed step-by-step procedures from the previous guide.
3. Prefer deterministic scripts for repeatable validation and use the documented smoke command before live side effects.
4. If credentials, network access, or external systems are required, run the offline checks first and then ask for or verify the required access.
5. Keep new operational detail in `references/` and keep `SKILL.md` focused on routing, protocol, and failure behavior.

## References

- [Classification Pitfalls](references/classification-pitfalls.md) - preserved detailed guidance or domain-specific operations.
- [Discord Pr Text Channels](references/discord-pr-text-channels.md) - preserved detailed guidance or domain-specific operations.
- [Discord Thread Cron State](references/discord-thread-cron-state.md) - preserved detailed guidance or domain-specific operations.
- [Preserved Skill Guide](references/preserved-skill-guide.md) - preserved detailed guidance or domain-specific operations.
- [Review Prs Category Cleanup](references/review-prs-category-cleanup.md) - preserved detailed guidance or domain-specific operations.

## Scripts

- `scripts/discord_pr_channels.py` - deterministic support or offline coverage for this skill.
- `scripts/my_open_prs.py` - deterministic support or offline coverage for this skill.
- `scripts/skill_health.py` - deterministic support or offline coverage for this skill.
- `scripts/test_discord_pr_channels.py` - deterministic support or offline coverage for this skill.
- `scripts/test_my_open_prs.py` - deterministic support or offline coverage for this skill.
- `scripts/test_skill_health.py` - deterministic support or offline coverage for this skill.

## Failure Behavior

- If the request does not match this skill, do not force the workflow; use the more specific skill or normal repo process.
- If a referenced command cannot run because credentials or live endpoints are unavailable, report the blocked check and continue with offline evidence.
- If the preserved guide conflicts with current repository state, verify the live files first and update the relevant reference before proceeding.
