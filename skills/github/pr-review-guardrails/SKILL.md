---
name: pr-review-guardrails
description: Use when applying the PR Review Guardrails skill workflow: Use when reviewing GitHub pull requests with strict clean-code, SOLID, feature-flag, experiment-outcome, Terraform-plan, coverage, CI, missing-review-decision recovery, and GitHub posting guardrails; runs dual reviewers with GPT-5.5 plus direct Claude CLI and routes results back to the originating Discord thread or Telegram topic. Triggered by requests mentioning pr-review-guardrails, PR Review Guardrails, setup, operation, troubleshooting, review, or automation for this workflow.
version: 1.0.0
license: MIT
required-skills: []
required-binaries: [gh, git, python3, claude]
required-env: []
required-mcps: []
metadata: github-pr-review-guardrails
---
# PR Review Guardrails

## Protocol

1. Use this skill only when the user request matches the trigger description or explicitly names `pr-review-guardrails`.
2. Read the linked references before taking action; they preserve the detailed step-by-step procedures from the previous guide.
3. Prefer deterministic scripts for repeatable validation and use the documented smoke command before live side effects.
4. If credentials, network access, or external systems are required, run the offline checks first and then ask for or verify the required access.
5. Keep new operational detail in `references/` and keep `SKILL.md` focused on routing, protocol, and failure behavior.

## References

- [Preserved Skill Guide](references/preserved-skill-guide.md) - high-frequency guardrail detail.
- [Review Template](references/review-template.md) - high-frequency guardrail detail.
- [Volatile Pr Heads](references/volatile-pr-heads.md) - high-frequency guardrail detail.
- [Github Review Threads Graphql Fallback](references/github-review-threads-graphql-fallback.md) - high-frequency guardrail detail.
- Full reference index: `04-integration-tests/reference-index.md` keeps all preserved case notes reachable for audits.

## Scripts

- `scripts/discord_rename_thread.py` - deterministic support or offline coverage for this skill.
- `scripts/linear_ticket_context.py` - deterministic support or offline coverage for this skill.
- `scripts/skill_health.py` - deterministic support or offline coverage for this skill.
- `scripts/test_discord_rename_thread.py` - deterministic support or offline coverage for this skill.
- `scripts/test_linear_ticket_context.py` - deterministic support or offline coverage for this skill.
- `scripts/test_skill_health.py` - deterministic support or offline coverage for this skill.

## Failure Behavior

- If the request does not match this skill, do not force the workflow; use the more specific skill or normal repo process.
- If a referenced command cannot run because credentials or live endpoints are unavailable, report the blocked check and continue with offline evidence.
- If the preserved guide conflicts with current repository state, verify the live files first and update the relevant reference before proceeding.
