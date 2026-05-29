# Shared Hermes tools repo sync

Use this pattern when the user wants scripts and active skills shared across multiple Hermes instances (for example Mac + Ubuntu) in a dedicated git repo.

## Durable workflow

- Use a rebase-only git workflow for shared multi-machine repos:
  - `git config pull.rebase true`
  - `git config rebase.autoStash true`
  - `git config branch.main.rebase true`
  - before pushing: `git pull --rebase --autostash origin main`
- Keep runtime/cache/auth state out of the repo with `.gitignore` entries for `__pycache__/`, `*.pyc`, `.DS_Store`, `.env`, `*.env`, `auth.json`, `auth.lock`, `state.db*`, `kanban.db*`, `sessions/`, `message-store/`, `logs/`, and `todos/`.
- Copy active skills from `$HERMES_HOME/skills`, but exclude caches/runtime metadata. Preserve skill support files (`references/`, `templates/`, `scripts/`, assets) because skills are class-level packages, not only `SKILL.md`.
- Make reusable scripts host/profile portable. Replace machine-specific paths with CLI flags and env vars such as `HERMES_HOME`, `HERMES_PROFILE`, repo path flags, Discord/GitHub identifiers, and output mode flags.
- For specific one-off scripts, prefer converting the script to a generic implementation plus a small backward-compatible wrapper rather than preserving hardcoded repo/PR/user names.

## Safety checks before commit

Run and report exact outputs where practical:

```bash
python3 -m compileall -q scripts
```

AST/skill/path scan:

- parse every `*.py` outside `.git` and `__pycache__` with `ast.parse`;
- count `skills/**/SKILL.md`;
- scan shared scripts for personal absolute home-directory paths and source-checkout paths.

Secret scan:

- scan text files for token-like patterns, at minimum GitHub `gh[pousr]_...`, OpenAI-like `sk-...`, Slack `xox...`, and private-key headers;
- sanitize even placeholder-looking examples if they match real token regexes, using obvious placeholders like `REDACTED_GITHUB_PAT` or `REDACTED_API_KEY`.

Smoke-test executable scripts with `--help` for argument parsing portability.

Run git whitespace validation:

```bash
git diff --check
# or, before committing staged changes:
git diff --cached --check
```

If copied templates/vendor files fail only because of trailing whitespace or extra EOF blank lines, normalize whitespace in text files, restage, and rerun the check before committing. Do not skip the check when the user explicitly asked for validation.

## Final verification/report

After committing:

```bash
git pull --rebase --autostash origin main
git push origin main
git status --short --branch
git log -2 --oneline
```

The final report should include the exact validation outputs, commit hashes/messages, rebase/push output, and final clean status. Keep it compact; huge commit file lists can be summarized as tool-output truncation if the command succeeded.
