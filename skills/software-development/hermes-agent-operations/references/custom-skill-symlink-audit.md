# Custom Skill Symlink Audit

Session-derived recipe for identifying which skills in a git-backed Hermes config repo are likely user/project skills and safe to symlink into an active `$HERMES_HOME/skills` tree.

## Signals used

1. Parse skill names from `SKILL.md` frontmatter under:
   - config repo `skills/`
   - active `$HERMES_HOME/skills`
   - Hermes source `skills/`
   - Hermes source `optional-skills/`
2. Read `$HERMES_HOME/skills/.bundled_manifest` for installed bundled skills.
3. Read `$HERMES_HOME/skills/.hub/lock.json` and `.hub/audit.log` for hub/community installs.
4. A strong custom candidate is in the config repo but absent from Hermes source `skills/` and `optional-skills`.
5. A locally patched upstream skill is in Hermes source but its active tree hash differs from the source tree hash. Keep these separate from custom skills.

## Count reconciliation

Use one label per count; do not report a count without the filter that produced it.

- **Non-bundled**: skills absent from `.bundled_manifest`. This can include Hermes optional skills and is too broad for “my skills”.
- **Not in Hermes source/optional-skills**: skills absent from both upstream `skills/` and `optional-skills/`. This is a strong custom/project/community candidate list.
- **Recommended personal/project symlink set**: the confirmed subset after excluding external/community items or existing source-repo symlinks unless the user explicitly includes them.

If the counts differ, explain the reason before mutating. Example: “14 non-bundled, 10 not-upstream, 8 recommended personal/project skills because `gog` is community and `environment-harness` is already a source-repo symlink.”

## Example classification from one run

The user asked about `~/Projects/hermes-config/skills`, but that path did not exist. The actual repo was `~/hermes-config`, remote `git@github.com:poom/hermes-config.git`.

Strong custom candidates found in the repo:

- `autonomous-ai-agents/codex-daily-usage-record`
- `productivity/greenhouse-recruiting`
- `github/my-open-prs`
- `github/pending-pr-review`
- `software-development/pickup-linear-ticket`
- `github/pr-review-guardrails`
- `productivity/recruiter-cli`
- `software-development/skillify`

Ambiguous/non-bundled items that need confirmation:

- `gog` — installed from a community/OpenClaw source; not Hermes bundled, but not necessarily user-authored.
- `engineering-tools/environment-harness` — may already be symlinked to a source repo such as `$HOME/Projects/agent-resources/skills/environment-harness`; preserve that source symlink unless the user explicitly asks to repoint it to the config repo.

Local-only custom candidate missing from the repo:

- `software-development/hermes-gateway-runtime-debugging`

Patched upstream/bundled skills were reported separately and were not recommended for the default "my skills only" symlink set.

## Origin/history explanation pattern

When the user asks why local skills exist or whether they installed them before, explain:

1. `$HERMES_HOME/skills` is the active library Hermes loads from.
2. A git config repo such as `~/hermes-config/skills` is usually a backup/source-of-truth candidate.
3. Skills may have appeared in active local storage because they were bundled, installed from the hub, created by the agent, copied from another repo, or symlinked from a source repo.
4. To infer origin, inspect:
   - `.hub/lock.json` and `.hub/audit.log` for explicit `INSTALL`/`UNINSTALL` records.
   - existing symlink targets with `os.readlink()`.
   - git first/last-touch history in the config repo (`git log --diff-filter=A --follow -- skills/<path>`).
   - whether the skill exists in Hermes source `skills/` or `optional-skills/`.
5. Avoid saying “you installed it” unless the audit log proves it. Prefer “most likely installed/created before” with evidence.

Example concise answer:

```text
Yes, most likely they existed before today. Hermes loads active skills from ~/.hermes/skills. Your hermes-config repo later backed up those active folders. Today we replaced selected active folders with symlinks to the repo, and moved the old active folders to ~/.hermes/skill-backups/... so nothing was lost.
```

## Backup and mutation reporting pattern

When applying symlinks, keep backups outside the active skills tree so Hermes does not discover duplicate backup skills:

```text
~/.hermes/skill-backups/symlink-YYYYMMDD-HHMMSS/
```

Report exactly:

- “Moved old active local folders to backup” with the list of paths moved.
- “Unlinked/repointed existing symlinks” with old target and new target.
- “Current active symlinks” with each `$HERMES_HOME/skills/<path> -> <repo>/skills/<path>`.

If a first attempt put backups under `$HERMES_HOME/skills/.symlink_backups`, move them out immediately and verify `hermes skills list` no longer shows `.symlink_backups` as a category.

## Minimal Python probe pattern

Use this shape when shelling out would be noisy; keep output compact and do not print secrets.

```python
from pathlib import Path
import yaml, hashlib, os

home = Path.home()
repo_skills = home / "hermes-config" / "skills"
active_skills = home / ".hermes" / "skills"
source = home / ".hermes" / "hermes-agent"

def parse_name(md: Path):
    text = md.read_text(errors="ignore")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return (yaml.safe_load(parts[1]) or {}).get("name")
    return None

def collect(root: Path):
    by_name = {}
    if not root.exists():
        return by_name
    for md in root.rglob("SKILL.md"):
        by_name[parse_name(md) or md.parent.name] = md.parent.relative_to(root)
    # Explicitly include symlink directories that rglob may skip.
    for p in list(root.glob("*")) + list(root.glob("*/*")):
        if p.is_symlink() and (p / "SKILL.md").exists():
            by_name[parse_name(p / "SKILL.md") or p.name] = p.relative_to(root)
    return by_name

repo = collect(repo_skills)
active = collect(active_skills)
source_core = collect(source / "skills")
source_optional = collect(source / "optional-skills")
source_all = {**source_core, **source_optional}

custom = sorted(set(repo) - set(source_all))
for name in custom:
    active_path = active_skills / active.get(name, "") if name in active else None
    state = "missing active"
    if active_path and active_path.exists():
        state = "symlink->" + os.readlink(active_path) if active_path.is_symlink() else "local dir"
    print(name, repo[name], state)
```
