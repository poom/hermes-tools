# Importing OpenClaw Workspace Skills into Hermes

Use this reference when the user asks to import, inspect, or migrate OpenClaw skills into Hermes.

## Discovery Commands

```bash
# Confirm OpenClaw CLI and skill commands
command -v openclaw
openclaw --version
openclaw skills --help
openclaw skills list --json > /tmp/openclaw_skills.json

# Inspect one skill if needed
openclaw skills info <skill-name> --json
```

OpenClaw workspace skills were found under:

```text
~/.openclaw/workspace/skills/<skill-name>/SKILL.md
```

Use `openclaw skills list --json` and filter for `source == "openclaw-workspace"` to identify custom/user workspace skills. Bundled skills are usually `source == "openclaw-bundled"`; extra registry skills may be `openclaw-extra`.

## Known User Environment Pattern

In the observed environment, OpenClaw custom skills were in:

```text
$HOME/.openclaw/workspace/skills/
```

Examples included:

- `codex-ticket-executor`
- `engineering-invoice-processor`
- `frontend-senior-angular-ionic`
- `gchat-unread-digest`
- `linear-stale-project-updates`
- `mcp-oauth-remote-bridge`
- `pending-pr-review`
- `pr-review-guardrails`
- `recruiter-cli`
- `repo-worktree-cleaner`
- `tmux`
- `today-meetings`
- `todo-manager`

Treat this as a discovery pattern, not a universal list; re-run the commands each session.

## Import Strategy

1. **List first; do not import immediately.** When the user asks to "show custom skills" or similar, produce a compact table: name, description, support files, and any caveats.
2. **Wait for explicit selection before writing.** Importing creates durable skill state.
3. **Read source files.** For each selected skill, read `SKILL.md` and enumerate `references/`, `templates/`, and `scripts/`. Avoid copying dependency trees such as `node_modules/` unless explicitly requested.
4. **Adapt to Hermes format.** Keep class-level intent, frontmatter, triggers, pitfalls, and verification. Replace OpenClaw-specific invocation patterns with Hermes equivalents where possible.
5. **Use Hermes skill support-file layout:**
   - `references/` for runbooks, docs, source excerpts, migration notes.
   - `templates/` for copy-and-modify starter files.
   - `scripts/` for deterministic helpers.
6. **Create or patch thoughtfully.** Prefer updating an existing class-level Hermes skill if it covers the same task. Create a new user-local skill only when no umbrella exists.
7. **Verify after import.** Use `skills_list` / `skill_view` where possible. Note that newly created skills may require a fresh session to appear in the loader depending on runtime caching.

## Caveats

- OpenClaw skills may reference OpenClaw-specific tools (`openclaw message`, `sessions_spawn`, gateway concepts, workspace paths). Convert or mark these as Hermes-specific TODOs.
- Some skills contain personal or organization-specific paths, emails, teams, labels, or workflows. Preserve operationally required paths if the user wants the personal workflow imported, but redact credentials/tokens and avoid exposing identity details unnecessarily in chat.
- Large dependency folders are not skill content. For example, an invoice-processing skill with `node_modules/` should normally import only `SKILL.md`, needed scripts, package manifests, and concise setup notes.
- Imported skills should be class-level. Do not create one-session artifact names like `import-openclaw-skill-today`; use the task class name.
