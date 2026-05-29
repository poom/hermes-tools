---
name: pickup-linear-ticket
description: Use when applying the Pick Up Linear Ticket skill workflow: Use when Poom asks to pick up, implement, or ship a Linear ticket end-to-end: read the Linear ticket and linked Notion/Linear references, implement behind feature flags or experiments, run internal PR-style review loops, open a draft GitHub PR from the default template, mention @finn-codex, process feedback, and mark the PR ready only when no issues remain. Triggered by requests mentioning pickup-linear-ticket, Pick Up Linear Ticket, setup, operation, troubleshooting, review, or automation for this workflow.
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [linear, github, pull-request, feature-flags, experiments, implementation, review-loop]
    related_skills: [linear, notion, github-pr-workflow, requesting-code-review, pr-review-guardrails]
required-skills: [linear, notion, github-pr-workflow, requesting-code-review, pr-review-guardrails]
required-binaries: [git, gh, python3]
required-env: [LINEAR_API_KEY]
---
# Pick Up Linear Ticket

## Protocol

1. Use this skill only when the user request matches the trigger description or explicitly names `pickup-linear-ticket`.
2. Read the linked references before taking action; they preserve the detailed step-by-step procedures from the previous guide.
3. Prefer deterministic scripts for repeatable validation and use the documented smoke command before live side effects.
4. If credentials, network access, or external systems are required, run the offline checks first and then ask for or verify the required access.
5. Keep new operational detail in `references/` and keep `SKILL.md` focused on routing, protocol, and failure behavior.

## References

- [Finn Web App Growthbook And Push Fallbacks](references/finn-web-app-growthbook-and-push-fallbacks.md) - preserved detailed guidance or domain-specific operations.
- [Preserved Skill Guide](references/preserved-skill-guide.md) - preserved detailed guidance or domain-specific operations.

## Scripts

- `scripts/discord_ticket_channels.py` - deterministic support or offline coverage for this skill.
- `scripts/skill_health.py` - deterministic support or offline coverage for this skill.
- `scripts/test_discord_ticket_channels.py` - deterministic support or offline coverage for this skill.
- `scripts/test_skill_health.py` - deterministic support or offline coverage for this skill.

## Failure Behavior

- If the request does not match this skill, do not force the workflow; use the more specific skill or normal repo process.
- If a referenced command cannot run because credentials or live endpoints are unavailable, report the blocked check and continue with offline evidence.
- If the preserved guide conflicts with current repository state, verify the live files first and update the relevant reference before proceeding.
