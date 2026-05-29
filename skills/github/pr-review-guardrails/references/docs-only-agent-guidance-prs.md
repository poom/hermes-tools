# Docs-only agent guidance / centrally synced AGENTS.md PRs

Use this checklist when a PR changes centrally managed agent docs such as `AGENTS.md`, `CLAUDE.md`, `other-templates/AGENTS.md`, `other-templates/README.md`, `.github/sync-other-files.yml`, or `other-templates/agent-docs/*`.

## Review focus

1. Treat it as a rollout/documentation-contract change, not a trivial markdown edit, because downstream repos and agents rely on these names and read-order rules.
2. Verify mirrored files stay mirrored. For EWA-Actions-style central docs, `AGENTS.md`, `CLAUDE.md`, and `other-templates/AGENTS.md` should usually be byte-identical after the change.
3. Check read order and ownership wording for consistency:
   - `AGENTS.md` / `CLAUDE.md` as org-level entrypoint.
   - `AGENTS.repo.md` for repo-owned guidance.
   - `AGENTS.terraform.md` for Terraform guidance when enabled.
   - `AGENTS.<profile>.md` for language/profile guidance.
4. Verify profile names against the sync manifest rather than assuming they equal source languages. Example: Node.js / TypeScript repos may receive `AGENTS.nodejs.md`, not `AGENTS.typescript.md`.
5. Re-check old review threads on previous heads; do not repeat stale findings if current docs and manifest now agree.
6. Compare README/table text against `.github/sync-other-files.yml` destination mappings and `other-templates/agent-docs/` file names.
7. Run whitespace validation with `git diff --check` and, if full local hooks are unavailable, rely on hosted pre-commit plus targeted local consistency checks.

## Useful local consistency probes

```bash
python3 - <<'PY'
from pathlib import Path
root = Path('.')
mirrors = ['AGENTS.md', 'CLAUDE.md', 'other-templates/AGENTS.md']
contents = [root.joinpath(p).read_text() for p in mirrors]
if len(set(contents)) != 1:
    raise SystemExit('AGENTS/CLAUDE template copies differ')
readme = root.joinpath('other-templates/README.md').read_text()
required = ['AGENTS.repo.md', 'AGENTS.terraform.md', 'AGENTS.<profile>.md', 'AGENTS.nodejs.md']
missing = [s for s in required if s not in readme]
if missing:
    raise SystemExit(f'README missing expected terms: {missing}')
print('agent-doc consistency checks passed')
PY
```

## Decision guidance

Approve-level when the mirrored docs, README, sync manifest, and prior review concerns all agree on the current head and CI is otherwise green. Report policy-bot/human approval as a process gate unless the user explicitly asks to enforce it as a code-review blocker.
