# Support-file validation

Use this reference when hardening or auditing a skill that depends on reusable code, starter files, generated fixtures, API notes, or other artifacts beyond `SKILL.md`.

## Lesson

A skill can pass superficial structural validation while still being incomplete. If the workflow used or created a deterministic helper script, the skill package should bundle that helper under `scripts/` and reference it from `SKILL.md`. Do not leave the only working copy in a runtime path such as `~/.hermes/scripts`, a temporary worktree, or a one-off project checkout.

Use the support-file directories intentionally:

- `scripts/` — deterministic re-runnable helpers, probes, verifiers, recorders, fixture generators
- `templates/` — starter files meant to be copied and edited
- `references/` — session-specific details, failure transcripts, API quirks, authoritative excerpts, or condensed knowledge banks

## Checklist before saying "Skillify pass"

1. List the target skill directory and confirm expected support files are present.
2. Confirm each support file referenced in `SKILL.md` exists under `references/`, `templates/`, or `scripts/`.
3. For each bundled script, run a syntax check, unit test, or safe dry-run when practical.
4. Load the skill with `skill_view(name)` and confirm `linked_files` exposes the support files.
5. If committing to a config/private repo, verify the repo copy contains the same support files, not only `SKILL.md`.
6. In the user-facing summary, name the artifacts included rather than only saying validation passed.

## Common failure pattern

Bad:

- `SKILL.md` says "create a deterministic script at `~/.hermes/scripts/foo.py`"
- the script exists locally
- the skill folder contains only `SKILL.md`
- the response says `SKILLIFY_VALIDATION PASS`

Good:

- `scripts/foo.py` is bundled inside the skill
- `SKILL.md` tells future agents to install/copy it to the runtime path
- validation checks the script exists and compiles or dry-runs
- `skill_view(name)` lists the script under `linked_files`
