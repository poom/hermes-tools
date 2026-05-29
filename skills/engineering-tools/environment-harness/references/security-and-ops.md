# Security and Ops

## Security Model

Safe to commit:

- `.agents.env` with `op://` references only
- `.agents.npmrc` and other `.agents.*` templates with `${ENV_VAR}` placeholders
- `.mise.toml` with tool versions

Runtime-only secret:

- `OP_SERVICE_ACCOUNT_TOKEN` in the orchestrator environment

Preferred vaults:

- `Engineering`
- `Agent-Testing`

Do not reference:

- production credentials
- deployment/infrastructure secrets
- customer data or PII
- personal developer tokens

## Threat Model

| Threat | Mitigation |
|---|---|
| Repo readers see `.agents.env` | refs are useless without 1Password access |
| Agent runtime is compromised | service account scope limits blast radius |
| Ref points at wrong item | setup/test failure surfaces it quickly |
| Item is deleted | `op read` fails loudly |

## CI Alignment

The environment harness is for agent environments, not CI, but the responsibilities should stay aligned:

| Concern | CI | Agent harness |
|---|---|---|
| secret store | GitHub Secrets | 1Password |
| secret injection | `${{ secrets.X }}` | `op read` in `before_run` |
| tool versions | `actions/setup-*` | `mise install` |
| package auth | CI config files | `.agents.*` templates |

## Versioning

Current contract is intentionally simple: `KEY=<secret-store-reference>`.

Only add schema versioning if the format must support new secret backends or conditionals. Until then, keep the parser simple and backward-compatible.

## Troubleshooting

- `op read` returns not found: the item moved or was deleted
- package install still gets 401: token is expired or mapped to the wrong registry
- `mise install` fails: network issue or unsupported tool version
- tests fail only in agents: missing service, missing non-secret env var, or undeclared runtime dependency
