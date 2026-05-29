# Config repo relocation and external skill symlinks

Session-derived pattern for Hermes skill library cleanup:

## Context

A user may have three distinct locations involved in skill management:

- `$HERMES_HOME/skills` — active skills Hermes loads from.
- A git-backed config repo, e.g. `<home>/Projects/hermes-config/skills` — backup/source-of-truth for selected custom skills.
- A separate project/source repo, e.g. `<home>/Projects/agent-resources/skills/environment-harness` — true source of truth for one skill even if a copied version also exists in the config repo.

Do not collapse these without explicit confirmation. A skill being present in the config repo does not automatically mean the config repo is its desired active target.

## Safe relocation workflow

When the user says a config repo should live at a different path:

1. Verify source path exists, destination path does not, and the source is a normal git directory.
2. Run `git status --short` before moving and report whether it was clean.
3. Move the repo to the requested canonical path.
4. Update only symlinks that currently point at the old repo path to the new repo path.
5. Verify:
   - old path no longer exists, or is an intentional compatibility symlink;
   - new path exists and `git rev-parse --show-toplevel` points there;
   - git remote is unchanged;
   - every active skill symlink points to the intended target and has `SKILL.md`;
   - `skill_view` or `hermes skills list` can resolve representative skills.

## External symlink pitfall

If a selected skill was previously an external symlink, treat its original target as high-signal intent. Before repointing it to the config repo, explicitly call out:

```text
<skill> currently points to <external repo>. I will keep that unless you want the config-repo copy instead.
```

Example: `engineering-tools/environment-harness` may belong to `<home>/Projects/agent-resources/skills/environment-harness` even though a copy also exists under `<home>/Projects/hermes-config/skills/engineering-tools/environment-harness`.

If the user corrects this after repointing, restore only that symlink:

```text
$HERMES_HOME/skills/engineering-tools/environment-harness -> <home>/Projects/agent-resources/skills/environment-harness
```

Then verify `SKILL.md`, `hermes skills list`, and `skill_view(environment-harness)`.

## Reporting rule

Use separate final lines for:

- config repo path after move;
- selected skills pointing to config repo;
- external skills intentionally pointing elsewhere.

This avoids implying all selected skills share one source-of-truth path.
