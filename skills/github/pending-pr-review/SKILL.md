---
name: pending-pr-review
description: Use when applying the Pending PR Review skill workflow: Use when Poom asks to review pending PRs, check the review queue, batch-review open GitHub PRs awaiting review, or recover missing submitted GitHub review decisions from saved review memory; lists pending PRs and runs pr-review-guardrails for each PR with one user-facing message/thread per PR. Triggered by requests mentioning pending-pr-review, Pending PR Review, setup, operation, troubleshooting, review, or automation for this workflow.
version: 1.0.0
license: MIT
required-skills: [pr-review-guardrails]
required-binaries: [bash, gh, python3]
required-env: []
required-mcps: []
metadata: github-pr-review-queue
---
# Pending PR Review

## Protocol

1. Use this skill only when the user request matches the trigger description or explicitly names `pending-pr-review`.
2. Read the linked references before taking action; they preserve the detailed step-by-step procedures from the previous guide.
3. Prefer deterministic scripts for repeatable validation and use the documented smoke command before live side effects.
4. If credentials, network access, or external systems are required, run the offline checks first and then ask for or verify the required access.
5. Keep new operational detail in `references/` and keep `SKILL.md` focused on routing, protocol, and failure behavior.

## References

- [Approved But Still Pending](references/approved-but-still-pending.md) - preserved detailed guidance or domain-specific operations.
- [Claude Interactive Sentinel Prompt Echo](references/claude-interactive-sentinel-prompt-echo.md) - preserved detailed guidance or domain-specific operations.
- [Context Compaction After Completed Pr](references/context-compaction-after-completed-pr.md) - preserved detailed guidance or domain-specific operations.
- [Cron Auto Delivery Duplicate Target](references/cron-auto-delivery-duplicate-target.md) - preserved detailed guidance or domain-specific operations.
- [Cron Cutoff Recovery After User Waits](references/cron-cutoff-recovery-after-user-waits.md) - preserved detailed guidance or domain-specific operations.
- [Cron Idle Timeout And Provider Stalls](references/cron-idle-timeout-and-provider-stalls.md) - preserved detailed guidance or domain-specific operations.
- [Cron Start Vs Output Finalization](references/cron-start-vs-output-finalization.md) - preserved detailed guidance or domain-specific operations.
- [Current Head Decision Only Drain](references/current-head-decision-only-drain.md) - preserved detailed guidance or domain-specific operations.
- [Deliver Local Hermes Send Cli](references/deliver-local-hermes-send-cli.md) - preserved detailed guidance or domain-specific operations.
- [Discord Thread Lifecycle](references/discord-thread-lifecycle.md) - preserved detailed guidance or domain-specific operations.
- [Drafted Request Changes After Duplicate Check Cutoff](references/drafted-request-changes-after-duplicate-check-cutoff.md) - preserved detailed guidance or domain-specific operations.
- [Github Actions Job Logs While Run Active](references/github-actions-job-logs-while-run-active.md) - preserved detailed guidance or domain-specific operations.
- [Github Search Limit Before Filtering](references/github-search-limit-before-filtering.md) - preserved detailed guidance or domain-specific operations.
- [Head Moved After Drafted Review Sequential Drain](references/head-moved-after-drafted-review-sequential-drain.md) - preserved detailed guidance or domain-specific operations.
- [Head Moved Before Posting After Blocker Fix](references/head-moved-before-posting-after-blocker-fix.md) - preserved detailed guidance or domain-specific operations.
- [Head Moved Before Posting Cutoff](references/head-moved-before-posting-cutoff.md) - preserved detailed guidance or domain-specific operations.
- [Live Queue Budget Exhaustion](references/live-queue-budget-exhaustion.md) - preserved detailed guidance or domain-specific operations.
- [Max Tool Cutoff After Completed Pr And Relist](references/max-tool-cutoff-after-completed-pr-and-relist.md) - preserved detailed guidance or domain-specific operations.
- [Max Tool Iterations Cutoff Local Delivery](references/max-tool-iterations-cutoff-local-delivery.md) - preserved detailed guidance or domain-specific operations.
- [Preserved Skill Guide](references/preserved-skill-guide.md) - preserved detailed guidance or domain-specific operations.
- [Re Requested Review Clears Queue](references/re-requested-review-clears-queue.md) - preserved detailed guidance or domain-specific operations.
- [Review Body Drafted Before Posting Cutoff](references/review-body-drafted-before-posting-cutoff.md) - preserved detailed guidance or domain-specific operations.
- [Reviewer Lanes Complete Before Posting Cutoff](references/reviewer-lanes-complete-before-posting-cutoff.md) - preserved detailed guidance or domain-specific operations.
- [Rmux Cli Reviewer Lanes](references/rmux-cli-reviewer-lanes.md) - preserved detailed guidance or domain-specific operations.
- [Scheduled Cron Delivery](references/scheduled-cron-delivery.md) - preserved detailed guidance or domain-specific operations.
- [Scheduled Timeout And Late Side Effects](references/scheduled-timeout-and-late-side-effects.md) - preserved detailed guidance or domain-specific operations.
- [Sequential Rmux Claude Startup Idle Variants](references/sequential-rmux-claude-startup-idle-variants.md) - preserved detailed guidance or domain-specific operations.
- [Sequential Rmux Cutoff After Current Head Recheck](references/sequential-rmux-cutoff-after-current-head-recheck.md) - preserved detailed guidance or domain-specific operations.
- [Sequential Rmux Cutoff After Drafted Approval Case](references/sequential-rmux-cutoff-after-drafted-approval-case.md) - preserved detailed guidance or domain-specific operations.
- [Sequential Rmux Cutoff After Evidence Only Start](references/sequential-rmux-cutoff-after-evidence-only-start.md) - preserved detailed guidance or domain-specific operations.
- [Sequential Rmux Cutoff After Lanes Complete](references/sequential-rmux-cutoff-after-lanes-complete.md) - preserved detailed guidance or domain-specific operations.
- [Sequential Rmux Cutoff After Next Pr Start](references/sequential-rmux-cutoff-after-next-pr-start.md) - preserved detailed guidance or domain-specific operations.
- [Sequential Rmux Drain Discord Progress](references/sequential-rmux-drain-discord-progress.md) - preserved detailed guidance or domain-specific operations.
- [Tool Budget Offline Review Cutoff](references/tool-budget-offline-review-cutoff.md) - preserved detailed guidance or domain-specific operations.
- [Tool Call Cutoff After Parent Evidence](references/tool-call-cutoff-after-parent-evidence.md) - preserved detailed guidance or domain-specific operations.
- [Tool Call Cutoff After Rmux Prompt Stall](references/tool-call-cutoff-after-rmux-prompt-stall.md) - preserved detailed guidance or domain-specific operations.
- [Tool Call Limit After Completed Pr Report](references/tool-call-limit-after-completed-pr-report.md) - preserved detailed guidance or domain-specific operations.
- [Tool Call Limit Final Response Deliver Local](references/tool-call-limit-final-response-deliver-local.md) - preserved detailed guidance or domain-specific operations.
- [Tool Call Max After Rmux Launch](references/tool-call-max-after-rmux-launch.md) - preserved detailed guidance or domain-specific operations.
- [Verified Review Before Delivery Cutoff](references/verified-review-before-delivery-cutoff.md) - preserved detailed guidance or domain-specific operations.

## Scripts

- `scripts/discord_pr_thread.py` - deterministic support or offline coverage for this skill.
- `scripts/list_pending_prs.sh` - deterministic support or offline coverage for this skill.
- `scripts/rmux_claude_interactive_reviewer.py` - deterministic support or offline coverage for this skill.
- `scripts/skill_health.py` - deterministic support or offline coverage for this skill.
- `scripts/test_discord_pr_thread.py` - deterministic support or offline coverage for this skill.
- `scripts/test_list_pending_prs.py` - deterministic support or offline coverage for this skill.
- `scripts/test_list_pending_prs.sh` - deterministic support or offline coverage for this skill.
- `scripts/test_rmux_claude_interactive_reviewer.py` - deterministic support or offline coverage for this skill.
- `scripts/test_skill_health.py` - deterministic support or offline coverage for this skill.

## Failure Behavior

- If the request does not match this skill, do not force the workflow; use the more specific skill or normal repo process.
- If a referenced command cannot run because credentials or live endpoints are unavailable, report the blocked check and continue with offline evidence.
- If the preserved guide conflicts with current repository state, verify the live files first and update the relevant reference before proceeding.
