#!/usr/bin/env python3
"""Curated Hermes config backup sync.

Copies safe Hermes config/customization files into a configurable git
checkout, redacts literal API keys in config.yaml, commits only when there
are changes, and pushes when a remote is configured.

Designed for Hermes cron no_agent=true: quiet on no-op, compact output on change/error.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from hermes_tools_common import hermes_home

SRC = Path(os.environ.get("HERMES_HOME", hermes_home())).expanduser()
DST = Path(os.environ.get("HERMES_CONFIG_BACKUP_DIR", Path.home() / "Projects" / "hermes-config")).expanduser()
REMOTE = os.environ.get("HERMES_CONFIG_BACKUP_REMOTE", "").strip()
REPO_LABEL = os.environ.get("HERMES_CONFIG_BACKUP_REPO_LABEL", REMOTE or str(DST))
BRANCH = os.environ.get("HERMES_CONFIG_BACKUP_BRANCH", "main")

SECRET_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----.*?-----END (?:RSA |OPENSSH |EC )?PRIVATE KEY-----", re.S),
]

FORBIDDEN_EXACT = {
    ".env",
    "auth.json",
    "auth.lock",
    "state.db",
    "state.db-wal",
    "state.db-shm",
    "kanban.db",
    "skills/.usage.json.lock",
}
FORBIDDEN_PREFIX = (
    "sessions/",
    "logs/",
    "message-sessions/",
    "cron/output/",
    "worktrees/",
    "pr-worktrees/",
    "pr-review-worktrees/",
    "pr-work/",
    "pr-reviews/",
    "cache/",
    "audio_cache/",
    "image_cache/",
    "sandboxes/",
    "state-snapshots/",
)


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True, check=check)


def ensure_repo() -> None:
    if (DST / ".git").exists():
        if REMOTE:
            run(["git", "remote", "set-url", "origin", REMOTE], cwd=DST)
        run(["git", "checkout", "-B", BRANCH], cwd=DST)
        # Pull only if remote branch exists. Empty/new repos may not have one.
        if REMOTE:
            refs = run(["git", "ls-remote", "--heads", "origin", BRANCH], cwd=DST).stdout.strip()
            if refs:
                run(["git", "pull", "--rebase", "--autostash", "origin", BRANCH], cwd=DST)
    else:
        if DST.exists():
            shutil.rmtree(DST)
        if REMOTE:
            run(["git", "clone", REMOTE, str(DST)], check=False)
        if not (DST / ".git").exists():
            DST.mkdir(parents=True, exist_ok=True)
            run(["git", "init"], cwd=DST)
            if REMOTE:
                run(["git", "remote", "add", "origin", REMOTE], cwd=DST)
        run(["git", "checkout", "-B", BRANCH], cwd=DST)


def safe_remove(path: Path) -> None:
    """Remove a file/dir/symlink if it exists, without following symlinks."""
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def clean_repo_worktree() -> None:
    """Clean only generated subtrees that are safe to recopy.

    Do not delete the whole repo: some active ~/.hermes/skills entries are
    symlinks into DST, so wiping DST first breaks the source tree mid-backup.
    """
    for rel in ["scripts", "hooks", "bin", "my-open-prs"]:
        safe_remove(DST / rel)


def redact_config() -> None:
    cfg = SRC / "config.yaml"
    if not cfg.exists():
        return
    out: list[str] = []
    for line in cfg.read_text(errors="replace").splitlines():
        m = re.match(r"^(\s*)(api_key\s*:\s*)(.*)$", line, flags=re.I)
        if m:
            val = m.group(3).strip()
            if val and val.lower() not in {"null", "none", "false"} and "$" not in val and not val.startswith("env:"):
                line = f"{m.group(1)}{m.group(2)}REDACTED_COMMIT_SAFE"
        out.append(line)
    (DST / "config.yaml").write_text("\n".join(out) + "\n")


def ignore_filter(_dirpath: str, names: list[str]) -> set[str]:
    blocked = {
        "__pycache__",
        ".DS_Store",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".hub",
        ".curator_backups",
        ".curator_state",
        ".usage.json",
        ".usage.json.lock",
    }
    return {n for n in names if n in blocked or n.endswith(".pyc")}


def copytree(rel: str) -> None:
    s = SRC / rel
    if s.exists():
        safe_remove(DST / rel)
        shutil.copytree(s, DST / rel, ignore=ignore_filter, ignore_dangling_symlinks=True)


def copy_one(src: Path, dst: Path) -> None:
    safe_remove(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, ignore=ignore_filter, ignore_dangling_symlinks=True)
    else:
        shutil.copy2(src, dst)


def copy_skills() -> None:
    skills_root = SRC / "skills"
    if not skills_root.exists():
        return
    (DST / "skills").mkdir(parents=True, exist_ok=True)
    ignored_names = ignore_filter(str(skills_root), [p.name for p in skills_root.iterdir()])
    for category in skills_root.iterdir():
        if category.name in ignored_names or category.name.startswith("."):
            continue
        if not category.is_dir():
            continue
        if category.is_symlink():
            if not category.exists():
                continue
            resolved = category.resolve()
            # Top-level skill symlink already backed by this repo.
            if is_within(resolved, DST):
                continue
            copy_one(resolved, DST / "skills" / category.name)
            continue
        # Some skills are installed directly at skills/<name>/SKILL.md without a category.
        if (category / "SKILL.md").exists():
            copy_one(category, DST / "skills" / category.name)
            continue
        (DST / "skills" / category.name).mkdir(parents=True, exist_ok=True)
        child_ignored = ignore_filter(str(category), [p.name for p in category.iterdir()])
        for child in category.iterdir():
            if child.name in child_ignored or child.name.startswith("."):
                continue
            if child.is_symlink():
                if not child.exists():
                    continue
                resolved = child.resolve()
                # Already backed by this repo; copying it onto itself is unsafe.
                if is_within(resolved, DST):
                    continue
                src = resolved
            else:
                src = child
            copy_one(src, DST / "skills" / category.name / child.name)


def copy_backup_cron_job() -> None:
    """Back up this Mac's full cron job list.

    This repository is the Mac backup (`poom/hermes-config`), so cron/jobs.json
    should mirror the active Mac cron jobs. The Ubuntu machine uses its own
    backup repository and must not rewrite this file.
    """
    jobs_path = SRC / "cron" / "jobs.json"
    if not jobs_path.exists():
        return
    (DST / "cron").mkdir(parents=True, exist_ok=True)
    shutil.copy2(jobs_path, DST / "cron" / "jobs.json")


def copy_inputs() -> None:
    redact_config()
    for name in ["SOUL.md", "shell-hooks-allowlist.json"]:
        p = SRC / name
        if p.exists() and p.is_file():
            shutil.copy2(p, DST / name)
    copy_skills()
    for rel in ["scripts", "hooks", "bin", "my-open-prs"]:
        copytree(rel)
    copy_backup_cron_job()


def count_files(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(1 for p in root.rglob("*") if p.is_file())


def count_skill_files(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(1 for p in root.rglob("SKILL.md") if p.is_file())


def included_items() -> list[str]:
    items = []
    for rel in ["config.yaml", "SOUL.md", "shell-hooks-allowlist.json"]:
        if (DST / rel).exists():
            items.append(rel)
    if (DST / "skills").exists():
        items.append(f"skills/ ({count_skill_files(DST / 'skills')} skills, {count_files(DST / 'skills')} files)")
    if (DST / "cron" / "jobs.json").exists():
        try:
            jobs_count = len(json.loads((DST / "cron" / "jobs.json").read_text()).get("jobs", []))
        except Exception:
            jobs_count = "unknown"
        items.append(f"cron/jobs.json ({jobs_count} job{'s' if jobs_count != 1 else ''})")
    for rel in ["scripts", "hooks", "bin", "my-open-prs"]:
        if (DST / rel).exists():
            items.append(f"{rel}/ ({count_files(DST / rel)} files)")
    return items


def format_list(values: list[str]) -> list[str]:
    if not values:
        return ["- none"]
    return [f"- {value}" for value in values]


def print_success(result: dict[str, object], sanitized: list[str], removed: list[str]) -> None:
    commit = str(result.get("commit", ""))
    short_commit = commit[:7] if commit else "unknown"
    lines = [
        "Backup success",
        "",
        "Files/folders:",
        *format_list(included_items()),
        "",
        "Git:",
        f"- Repo: {REPO_LABEL}",
        f"- Branch: {BRANCH}",
        f"- Commit: {short_commit}",
        "- Pushed: yes",
        "",
        "Safety:",
        "- Secrets scan: passed",
        f"- Sanitized: {', '.join(sanitized) if sanitized else 'none'}",
        f"- Removed: {', '.join(removed) if removed else 'none'}",
    ]
    print("\n".join(lines))


def print_failure(error: Exception) -> None:
    lines = [
        "Backup fail",
        "",
        "Files/folders:",
        "- not completed",
        "",
        "Error:",
        f"- {error}",
    ]
    print("\n".join(lines), file=sys.stderr)


def write_repo_docs() -> None:
    (DST / "README.md").write_text(f"""# hermes-config

Private Mac backup of Hermes Agent configuration and customizations for this machine.

Included:
- `config.yaml` with literal `api_key` values redacted
- `skills/` custom/installed skill files, excluding hub/cache metadata
- `scripts/` helper scripts used by cron/jobs
- `my-open-prs/` durable Markdown status files for tracked GitHub PR monitors
- `hooks/` and `bin/` custom local extensions, except unsafe binary matches
- `cron/jobs.json` job definitions, without cron output/locks

Backup policy:
- Daily automatic sync commits and pushes if anything changed.
- When Hermes intentionally edits this backup/config during a task, commit and push immediately too.

Intentionally not committed:
- `.env`
- `auth.json` / OAuth tokens / credential pools
- sessions, logs, state DBs, caches, worktrees, generated media

Restore notes:
1. Copy files back into `~/.hermes/` or a profile directory.
2. Recreate secrets in `~/.hermes/.env` or via `hermes login` / `hermes auth`.
3. Replace `REDACTED_COMMIT_SAFE` placeholders in `config.yaml` if needed.
4. Restart Hermes/gateway after config changes.
""")
    (DST / ".gitignore").write_text("""# Secrets / credentials
.env
.env.*
!.env.example
auth.json
auth.lock
*token*
*secret*
*credential*
*.pem
*.key
*.p12
*.pfx
id_rsa*
id_ed25519*

# Hermes state / runtime
state.db*
kanban.db*
sessions/
message-sessions/
logs/
cache/
audio_cache/
image_cache/
sandboxes/
state-snapshots/
processes.json
gateway.pid
gateway.lock
gateway_state.json
.restart_last_processed.json
.hermes_history

# Cron runtime output
cron/output/
cron/.tick.lock

# Worktrees / generated review artifacts
worktrees/
pr-worktrees/
pr-review-worktrees/
pr-work/
pr-reviews/
pr-monitors/

# Skill hub/cache metadata
skills/.hub/
skills/.curator_backups/
skills/.curator_state
skills/.usage.json
skills/.usage.json.lock

# Caches / generated files
__pycache__/
*.py[cod]
.DS_Store
.pytest_cache/
.mypy_cache/
.ruff_cache/
context_length_cache.yaml
models_dev_cache.json
usage/
""")


def sanitize_and_scan() -> tuple[list[str], list[str]]:
    sanitized: list[str] = []
    removed: list[str] = []
    for p in list(DST.rglob("*")):
        if ".git" in p.parts or not p.is_file():
            continue
        rel = str(p.relative_to(DST))
        data = p.read_bytes()
        text_probe = data.decode("latin1", errors="ignore")
        matched = any(pat.search(text_probe) for pat in SECRET_PATTERNS)
        if not matched:
            continue
        is_text = b"\x00" not in data and len(data) < 5_000_000
        if not is_text:
            p.unlink()
            removed.append(rel)
            continue
        text = data.decode("utf-8", errors="replace")
        new = text
        for pat in SECRET_PATTERNS:
            new = pat.sub("REDACTED_SECRET_PATTERN", new)
        if new != text:
            p.write_text(new)
            sanitized.append(rel)

    findings: list[str] = []
    for p in DST.rglob("*"):
        if ".git" in p.parts or not p.is_file():
            continue
        text = p.read_bytes().decode("latin1", errors="ignore")
        if any(pat.search(text) for pat in SECRET_PATTERNS):
            findings.append(str(p.relative_to(DST)))
    if findings:
        raise RuntimeError("secret pattern findings after sanitize: " + json.dumps(findings))
    return sanitized, removed


def validate_tracked_candidates() -> None:
    run(["git", "add", "-A"], cwd=DST)
    files = run(["git", "diff", "--cached", "--name-only"], cwd=DST).stdout.splitlines()
    bad = [f for f in files if f in FORBIDDEN_EXACT or f.startswith(FORBIDDEN_PREFIX)]
    if bad:
        raise RuntimeError("forbidden files staged: " + json.dumps(bad))


def commit_and_push() -> dict[str, object] | None:
    validate_tracked_candidates()
    diff = run(["git", "diff", "--cached", "--quiet"], cwd=DST, check=False)
    if diff.returncode == 0:
        return None
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run(["git", "commit", "-m", f"chore: sync Hermes config ({ts})"], cwd=DST)
    if REMOTE:
        run(["git", "push", "-u", "origin", BRANCH], cwd=DST)
    head = run(["git", "rev-parse", "HEAD"], cwd=DST).stdout.strip()
    changed = run(["git", "show", "--stat", "--oneline", "--summary", "--no-renames", "HEAD"], cwd=DST).stdout
    return {"commit": head, "summary": changed[:4000]}


def main() -> int:
    try:
        ensure_repo()
        clean_repo_worktree()
        copy_inputs()
        write_repo_docs()
        sanitized, removed = sanitize_and_scan()
        result = commit_and_push()
        if result:
            print_success(result, sanitized, removed)
        return 0
    except Exception as e:
        print_failure(e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
