#!/usr/bin/env python3
"""Shared helpers for portable Hermes utility scripts.

Keep this module dependency-free so scripts can run on macOS, Ubuntu, and fresh
Hermes installs. All paths can be overridden with environment variables.
"""
from __future__ import annotations

import os
import shlex
import shutil
from pathlib import Path


def hermes_home() -> Path:
    """Return the active Hermes home/profile directory."""
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")).expanduser()


def hermes_scripts_dir() -> Path:
    """Return the Hermes scripts directory used by cron/script helpers."""
    return Path(os.environ.get("HERMES_SCRIPTS_DIR", hermes_home() / "scripts")).expanduser()


def load_hermes_dotenv(path: str | Path | None = None) -> None:
    """Load simple KEY=VALUE pairs without requiring python-dotenv.

    Existing environment variables win. Quotes are stripped; shell expansions are
    intentionally not evaluated.
    """
    env_path = Path(path or os.environ.get("HERMES_ENV_FILE", hermes_home() / ".env")).expanduser()
    try:
        text = env_path.read_text(errors="ignore")
    except Exception:
        return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            try:
                value = shlex.split(value)[0]
            except Exception:
                value = value[1:-1]
        os.environ[key] = value


def portable_env(extra_paths: list[str | Path] | None = None) -> dict[str, str]:
    """Return an env with common user binary dirs prepended when present.

    HERMES_EXTRA_PATHS may contain an os.pathsep-separated list of additional
    directories for host-specific tools.
    """
    env = os.environ.copy()
    candidates: list[Path] = []
    if extra_paths:
        candidates.extend(Path(p).expanduser() for p in extra_paths)
    candidates.extend(Path(p).expanduser() for p in os.environ.get("HERMES_EXTRA_PATHS", "").split(os.pathsep) if p)
    candidates.extend([
        Path.home() / ".local" / "bin",
        Path.home() / ".bun" / "bin",
        Path("/opt/homebrew/bin"),
        Path("/usr/local/bin"),
    ])
    prefix = [str(p) for p in candidates if p.exists()]
    env["PATH"] = os.pathsep.join(prefix + [env.get("PATH", "")])
    return env


def which_executable(name: str, env_var: str | None = None, *, required: bool = False) -> str | None:
    """Resolve an executable from an explicit env var, PATH, or common user dirs."""
    if env_var and os.environ.get(env_var):
        return str(Path(os.environ[env_var]).expanduser())
    env = portable_env()
    found = shutil.which(name, path=env.get("PATH"))
    if found:
        return found
    if required:
        raise RuntimeError(f"Required executable not found: {name} (set {env_var} or HERMES_EXTRA_PATHS)")
    return None
