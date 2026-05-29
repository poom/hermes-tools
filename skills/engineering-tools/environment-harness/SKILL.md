---
name: environment-harness
description: Use when applying the Environment Harness skill workflow: Make any repo self-describing for AI agent environments — credentials, tool versions, package registries, and test dependencies — so Symphony agents can build, test, and iterate without human setup. Triggered by requests mentioning environment-harness, Environment Harness, setup, operation, troubleshooting, review, or automation for this workflow.
version: 0.4.0 # x-release-please-version
audience: team
required-skills: []
required-binaries:
  - op
  - mise
  - envsubst
  - docker
required-env:
  - OP_SERVICE_ACCOUNT_TOKEN
required-mcps: []
mutates: Guidance only; harnesses built from this skill resolve secrets via op, render tool config templates into $HOME, install runtimes with mise, and may start docker compose services during before_run.
department:
  - Engineering
category: Engineering Tools
status: Active
setup-required: true
available-for: Both
---
# Environment Harness

## Protocol

1. Use this skill only when the user request matches the trigger description or explicitly names `environment-harness`.
2. Read the linked references before taking action; they preserve the detailed step-by-step procedures from the previous guide.
3. Prefer deterministic scripts for repeatable validation and use the documented smoke command before live side effects.
4. If credentials, network access, or external systems are required, run the offline checks first and then ask for or verify the required access.
5. Keep new operational detail in `references/` and keep `SKILL.md` focused on routing, protocol, and failure behavior.

## References

- [Agents Repo Md](references/agents-repo-md.md) - preserved detailed guidance or domain-specific operations.
- [Changelog Archive](references/changelog-archive.md) - preserved detailed guidance or domain-specific operations.
- [Docker And Monorepos](references/docker-and-monorepos.md) - preserved detailed guidance or domain-specific operations.
- [Ecosystem Patterns](references/ecosystem-patterns.md) - preserved detailed guidance or domain-specific operations.
- [Eval Framework](references/eval-framework.md) - preserved detailed guidance or domain-specific operations.
- [Onboarding Checklist](references/onboarding-checklist.md) - preserved detailed guidance or domain-specific operations.
- [Preserved Skill Guide](references/preserved-skill-guide.md) - preserved detailed guidance or domain-specific operations.
- [Resolution Flow](references/resolution-flow.md) - preserved detailed guidance or domain-specific operations.
- [Security And Ops](references/security-and-ops.md) - preserved detailed guidance or domain-specific operations.

## Scripts

- `scripts/scan.py` - deterministic support or offline coverage for this skill.
- `scripts/skill_health.py` - deterministic support or offline coverage for this skill.
- `scripts/test_scan.py` - deterministic support or offline coverage for this skill.
- `scripts/test_skill_health.py` - deterministic support or offline coverage for this skill.

## Failure Behavior

- If the request does not match this skill, do not force the workflow; use the more specific skill or normal repo process.
- If a referenced command cannot run because credentials or live endpoints are unavailable, report the blocked check and continue with offline evidence.
- If the preserved guide conflicts with current repository state, verify the live files first and update the relevant reference before proceeding.
