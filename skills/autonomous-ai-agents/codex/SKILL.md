---
name: codex
description: Use when delegating coding, PR review, refactoring, batch issue fixing, or Codex CLI operations to OpenAI Codex. Triggered by requests mentioning Codex CLI, codex exec, full-auto, Codex quota, report-only PR review, or Hermes Codex automation.
version: 1.0.0
license: MIT
---
# Codex CLI

## Protocol

1. Use this skill when the user asks to delegate coding work, PR review, quota checks, or Hermes automation to the OpenAI Codex CLI.
2. Before running Codex, confirm the working directory is a git repository and choose interactive PTY mode for interactive Codex sessions.
3. For long-running work, start Codex in the background, record the session id, and monitor with the process tools until it finishes or needs input.
4. For quota or subscription questions, verify live auth state when current quota matters; do not treat stale login status as sufficient evidence.
5. For report-only PR review, keep Codex read-only and leave posting or synthesis to the parent agent.

## References

- [Chatgpt Subscription Usage](references/chatgpt-subscription-usage.md) - detailed preserved guidance or domain-specific operations.
- [Preserved Skill Guide](references/preserved-skill-guide.md) - detailed preserved guidance or domain-specific operations.
- [Rmux Report Only Pr Review](references/rmux-report-only-pr-review.md) - detailed preserved guidance or domain-specific operations.

## Scripts

- `scripts/skill_health.py` - offline package health check for links and required evidence folders.
- `scripts/test_skill_health.py` - unit coverage for the health check.

## Failure Behavior

- If Codex auth is missing or expired, stop and ask the user to refresh the Codex login before making live quota or execution claims.
- If the target directory is not a git repository, initialize a temporary repository for scratch work or ask for the correct checkout.
- If a background Codex task stalls, poll logs first, then submit required input or terminate only after explaining the risk.
