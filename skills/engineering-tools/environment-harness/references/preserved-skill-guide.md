# Preserved Environment Harness Guide

This reference preserves the previous detailed operating guide. Use it for step-by-step procedures after the lean `SKILL.md` routes to this skill.

## Previous Frontmatter

```yaml
name: environment-harness
description: Make any repo self-describing for AI agent environments — credentials, tool versions, package registries, and test dependencies — so Symphony agents can build, test, and iterate without human setup.
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
```

Continuation:

```yaml
required-mcps: []
mutates: Guidance only; harnesses built from this skill resolve secrets via op, render tool config templates into $HOME, install runtimes with mise, and may start docker compose services during before_run.
department:
  - Engineering
category: Engineering Tools
status: Active
setup-required: true
available-for: Both
```

## Previous Operating Guide

# Environment Harness

Use this skill when a repository needs to become agent-ready: credentials, tool versions, package registries, and test dependencies must be explicit so agents can install dependencies and run tests without human setup. Context engineering (`AGENTS.md`) tells an agent how to work; the environment harness tells it how to set up the repo.

## Contract

An agent-ready repo uses four pieces:

| File or hook | Purpose |
|---|---|
| `.agents.env` | committed `op://` references for secrets needed in agent runs |
| `.agents.npmrc` | committed package-manager config that reads resolved env vars |
| `.mise.toml` | committed runtime/tool version declarations |
| `before_run` | orchestrator hook that resolves refs, renders templates, and prepares test dependencies |

## Core Files

### `.agents.env`

- Format: `KEY=<secret-store-reference>`
- Allowed: private registry tokens, test/staging credentials, integration-test cloud creds
- Forbidden: production credentials, personal tokens, PII, inline secrets

```env
NPM_TOKEN=<secret-store-reference>
FONTAWESOME_TOKEN=<secret-store-reference>
GH_PACKAGES_TOKEN=<secret-store-reference>
```

Validate a reference safely with `op read --no-newline "<secret-store-reference>" | wc -c`.

### `.agents.npmrc`

- npm is the native case: `.npmrc` reads `${ENV_VAR}` directly from the environment.
- For formats without native interpolation, commit `.agents.<tool-config>` and render it during `before_run`.

```ini
@finn:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${GH_PACKAGES_TOKEN}
@fortawesome:registry=https://npm.fontawesome.com/
//npm.fontawesome.com/:_authToken=${FONTAWESOME_TOKEN}
```

### `.mise.toml`

- Required for runtime declarations such as `node = "20"` or `python = "3.12"`.
- Validate the declared Node toolchain with `mise install && mise exec -- node --version`.

## `before_run`

1. Resolve `.agents.env` with `op read`.
2. Call `render_tool_configs()` for non-native templates.
3. Trust and install declared tool versions with `mise`.
4. Set non-secret test env vars and start optional services.

Exact commands that must remain available in the harness:

- `envsubst < "$REPO_ROOT/.agents.netrc" > "$HOME/.netrc"`
- `chmod 600 "$HOME/.netrc"`
- `envsubst < "$REPO_ROOT/.agents.auth.json" > "$HOME/.composer/auth.json"`
- `docker compose -f docker-compose.agents.yml up -d --wait`
- `docker compose -f docker-compose.agents.yml down -v`
- `pnpm --filter @repo/auth test`

## Rules

- Fail loudly when `op read` or template rendering fails.
- Use dedicated agent vaults such as `Engineering` or `Agent-Testing`, never production or deployment vaults.
- Keep `.agents.*` files committed as references/templates only; runtime secrets stay in the orchestrator.

## References

- Full render helpers and `before_run` pseudocode: references/resolution-flow.md (`references/resolution-flow.md`)
- Ecosystem-specific patterns: references/ecosystem-patterns.md (`references/ecosystem-patterns.md`)
- Security model, CI alignment, versioning, and troubleshooting: references/security-and-ops.md (`references/security-and-ops.md`)
- Docker services and monorepo patterns: references/docker-and-monorepos.md (`references/docker-and-monorepos.md`)
- Repo rollout checklist: references/onboarding-checklist.md (`references/onboarding-checklist.md`)
- `AGENTS.repo.md` file spec: references/agents-repo-md.md (`references/agents-repo-md.md`)
