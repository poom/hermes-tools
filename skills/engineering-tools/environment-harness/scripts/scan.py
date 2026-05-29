#!/usr/bin/env python3
"""Generate a dumb deterministic repo execution contract for any repository.

The scanner only catalogs files, structured metadata, and literal string/pattern matches.
The JSON artifact is authoritative. The markdown output is rendered from that JSON.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCHEMA_VERSION = "2026-03-hybrid-v2"

KEYWORD_RELEASE = ("release", "deploy", "publish", "ship", "artifact", "tag")
KEYWORD_CI = ("ci", "workflow", "github actions", "pipeline")
LOCAL_HINT_KEYWORDS = ("test", "lint", "check", "fmt", "build", "start", "dev", "bootstrap", "install")

PYTHON_SOURCE_SUFFIXES = {".py", ".pyw"}
PYTHON_SOURCE_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
}
GLOBAL_SCAN_SKIP_DIRS = PYTHON_SOURCE_SKIP_DIRS | {
    "vendor",
    ".tox",
    "coverage",
    ".cache",
    ".next",
    ".nuxt",
    "target",
    "out",
}
PYTHON_SOURCE_SAMPLE_LIMIT = 20
DOC_FILE_LIMIT = 100
DOC_COMMAND_LIMIT = 20
WORKFLOW_COMMAND_LIMIT = 20
ENTRYPOINT_DISPLAY_LIMIT = 20
WORKFLOW_RUN_DISPLAY_LIMIT = 6
ROOT_GUIDANCE_HEADING_LIMIT = 10
ROOT_GUIDANCE_COMMAND_START_LIMIT = 8

DOC_FENCE_RE = re.compile(r"```(?P<lang>[A-Za-z0-9_-]*)\n(?P<body>.*?)```", re.DOTALL)
TOP_LEVEL_MARKDOWN_HEADING_RE = re.compile(r"^#\s+(.+?)\s*$")
DIRECT_PATH_ONLY_RE = re.compile(r"^\./[A-Za-z0-9_./-]+/?$")
SHELL_FENCE_LANGUAGES = {"", "bash", "sh", "shell", "zsh", "console"}
FILE_LIKE_SUFFIXES = {
    ".md",
    ".markdown",
    ".rst",
    ".txt",
    ".json",
    ".jsonc",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".lock",
    ".service",
    ".xml",
    ".html",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".jsx",
    ".py",
    ".sh",
    ".bash",
    ".zsh",
    ".go",
    ".rs",
    ".php",
    ".sql",
}
COMMAND_START_RE = re.compile(
    r"^"
    r"(?:"
    r"make|just|task|npm|pnpm|yarn|bun|node|npx|pnpx|python|python3|pip|pip3|pytest|tox|nox|poetry|uv|go|cargo|docker(?:-compose)?|bash|sh|openclaw|gh|mise|\./[A-Za-z0-9_./-]+"
    r")\b"
)
RUN_LINE_RE = re.compile(r"^(\s*)(?:-\s*)?run:\s*(.*?)\s*$")
SECRET_RE = re.compile(r"\$\{\{\s*secrets\.([A-Za-z0-9_]+)\s*}}")
VAR_RE = re.compile(r"\$\{\{\s*vars\.([A-Za-z0-9_]+)\s*}}")
ENV_REF_RE = re.compile(r"\$\{\{\s*env\.([A-Za-z0-9_]+)\s*}}")

SETUP_ACTIONS = {
    "node": {
        "marker": "actions/setup-node@",
        "version_keys": ("node-version",),
        "version_file_keys": ("node-version-file",),
    },
    "python": {
        "marker": "actions/setup-python@",
        "version_keys": ("python-version",),
        "version_file_keys": ("python-version-file",),
    },
    "go": {
        "marker": "actions/setup-go@",
        "version_keys": ("go-version",),
        "version_file_keys": ("go-version-file",),
    },
}

MATRIX_VERSION_KEYS = {
    "node": ("node", "node-version", "node_version"),
    "python": ("python", "python-version", "python_version"),
    "go": ("go", "go-version", "go_version"),
}

PACKAGE_MANAGER_HINTS = {
    "npm": (r"\bnpm\b", r"cache:\s*npm\b"),
    "pnpm": (r"\bpnpm\b", r"pnpm/action-setup@", r"cache:\s*pnpm\b"),
    "yarn": (r"\byarn\b", r"cache:\s*yarn\b"),
    "bun": (r"\bbun\b",),
    "pip": (r"\bpip3?\b",),
    "poetry": (r"\bpoetry\b",),
    "pipenv": (r"\bpipenv\b",),
    "uv": (r"\buv\b",),
}

DOCKER_ACTION_HINTS = (
    "docker/build-push-action",
    "docker/login-action",
    "docker/metadata-action",
    "docker/setup-buildx-action",
    "docker/setup-qemu-action",
)
DOCKER_COMMAND_HINT_PATTERNS = (
    "docker build",
    "docker compose",
    "docker-compose",
    "docker run",
    "docker pull",
    "docker push",
    "podman build",
    "buildx build",
)

GUIDANCE_MARKERS = (
    "prompt-sources",
    "agent-prompts",
    "agents/",
    ".codex/skills/repo-execution-contract.json",
    ".codex/skills/repo-execution-contract.md",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--repo-name", default="")
    parser.add_argument(
        "--output",
        default=".codex/skills/repo-execution-contract.md",
        help="Markdown skill output path",
    )
    parser.add_argument(
        "--json-output",
        default=".codex/skills/repo-execution-contract.json",
        help="Structured JSON output path",
    )
    parser.add_argument(
        "--verify-supported",
        action="store_true",
        help="Compatibility flag: keep hook integrations stable.",
    )
    parser.add_argument(
        "--enforce-supported",
        action="store_true",
        help="Compatibility flag: kept for hook integrations; no single-repo enforcement.",
    )
    return parser.parse_args()



def relpath(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()



def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")



def glob_sorted(root: Path, pattern: str) -> list[Path]:
    results: list[Path] = []
    for path in root.rglob(pattern):
        if any(part in GLOBAL_SCAN_SKIP_DIRS for part in path.parts):
            continue
        if path.is_file():
            results.append(path)
    return sorted(results)



def leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip(" "))



def dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered



def dedupe_objects(values: list[dict], key_fields: tuple[str, ...]) -> list[dict]:
    seen: set[tuple[str, ...]] = set()
    ordered: list[dict] = []
    for value in values:
        key = tuple(str(value.get(field, "")) for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(value)
    return ordered



def limit_values(values: list[str], limit: int) -> list[str]:
    return values[:limit]



def trim_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value



def normalize_scalar(raw: str) -> str:
    value = raw.strip().rstrip(",")
    return trim_quotes(value)



def parse_literal_value_list(raw: str) -> list[str]:
    value = raw.strip()
    if not value or value in {"|", ">", "|-", ">-"}:
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1]
        parts = re.findall(r'"[^"]*"|\'[^\']*\'|[^,\[\]]+', inner)
        return dedupe_strings([normalize_scalar(part) for part in parts])
    return [normalize_scalar(value)]



def parse_image_ref(raw: str) -> dict:
    value = normalize_scalar(raw)
    if not value:
        return {"raw": "", "name": "", "tag": "", "digest": ""}
    name = value
    tag = ""
    digest = ""
    if "@" in value:
        name, digest = value.split("@", 1)
    else:
        last_slash = value.rfind("/")
        last_colon = value.rfind(":")
        if last_colon > last_slash:
            name = value[:last_colon]
            tag = value[last_colon + 1 :]
    return {"raw": value, "name": name, "tag": tag, "digest": digest}



def resolve_repo_name(root: Path, explicit_name: str) -> str:
    if explicit_name:
        return explicit_name
    symphony_repo = root / ".symphony_repo"
    if symphony_repo.exists():
        name = symphony_repo.read_text(encoding="utf-8").strip()
        if name:
            return name
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return "unknown/unknown"
    url = result.stdout.strip()
    if url.endswith(".git"):
        url = url[:-4]
    if url.startswith("git@github.com:"):
        return url.split(":", 1)[1]
    if url.startswith("https://github.com/"):
        return url.split("https://github.com/", 1)[1]
    return url or "unknown/unknown"



def parse_make_public_targets(make_text: str) -> list[str]:
    targets: list[str] = []
    seen: set[str] = set()
    for line in make_text.splitlines():
        if not line or line.startswith("\t"):
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" in stripped and ":" not in stripped:
            continue
        match = re.match(r"^([A-Za-z0-9][A-Za-z0-9_.-]*)\s*:\s*(?:$|[^=])", line)
        if not match:
            continue
        name = match.group(1)
        if name.startswith(".") or name.startswith("_"):
            continue
        if name not in seen:
            seen.add(name)
            targets.append(name)
    return targets



def parse_package_scripts(package_text: str) -> list[str]:
    try:
        payload = json.loads(package_text)
    except json.JSONDecodeError:
        return []
    scripts = payload.get("scripts") or {}
    if not isinstance(scripts, dict):
        return []
    return sorted([str(key) for key in scripts.keys()])



def parse_composer_json(text: str) -> dict:
    """Parse a composer.json file, extracting scripts, require, and require-dev."""
    payload = parse_json_object(text)
    if not payload:
        return {"scripts": [], "require": {}, "require_dev": {}, "platform": {}}
    scripts_raw = payload.get("scripts") or {}
    scripts = sorted(str(k) for k in scripts_raw.keys()) if isinstance(scripts_raw, dict) else []
    require_raw = payload.get("require") or {}
    require = {str(k): str(v) for k, v in require_raw.items()} if isinstance(require_raw, dict) else {}
    require_dev_raw = payload.get("require-dev") or {}
    require_dev = {str(k): str(v) for k, v in require_dev_raw.items()} if isinstance(require_dev_raw, dict) else {}
    config = payload.get("config") or {}
    platform_raw = config.get("platform") or {} if isinstance(config, dict) else {}
    platform = {str(k): str(v) for k, v in platform_raw.items()} if isinstance(platform_raw, dict) else {}
    return {"scripts": scripts, "require": require, "require_dev": require_dev, "platform": platform}



def parse_mise_toml_tools(text: str) -> list[tuple[str, str]]:
    """Parse [tools] section from mise.toml / .mise.toml. Returns list of (tool, version) tuples."""
    tools: list[tuple[str, str]] = []
    in_tools = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "[tools]":
            in_tools = True
            continue
        if in_tools:
            if stripped.startswith("[") and stripped.endswith("]"):
                break
            if not stripped or stripped.startswith("#"):
                continue
            match = re.match(r'^([A-Za-z0-9_.-]+)\s*=\s*(.+)$', stripped)
            if match:
                tool = match.group(1)
                version = normalize_scalar(match.group(2))
                tools.append((tool, version))
    return tools



def parse_tool_versions(text: str) -> list[tuple[str, str]]:
    """Parse .tool-versions file. Returns list of (tool, version) tuples."""
    tools: list[tuple[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split(None, 1)
        if len(parts) == 2:
            tools.append((parts[0], parts[1].strip()))
        elif len(parts) == 1:
            tools.append((parts[0], ""))
    return tools



def read_single_version_file(path: Path) -> str:
    """Read a single-value version file (.python-version, .nvmrc, etc.)."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        lines = [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]
        return lines[0] if lines else ""
    except OSError:
        return ""



def scan_runtime_manifests(root: Path) -> list[dict]:
    """Scan all known manifest files for runtime/tool version pins.

    Returns a list of entries like:
        {"tool": "php", "version": "^8.2.0", "source": "composer.json:require.php", "path": "composer.json"}

    If a manifest file exists but the version field is absent, emits an entry with version=null.
    100% deterministic: parses structured fields only, no inference.
    """
    manifests: list[dict] = []

    # mise.toml / .mise.toml
    for pattern in ("mise.toml", ".mise.toml"):
        for path in glob_sorted(root, pattern):
            rel = relpath(root, path)
            text = read_text(path)
            tools = parse_mise_toml_tools(text)
            if tools:
                for tool, version in tools:
                    manifests.append({
                        "tool": tool,
                        "version": version or None,
                        "source": f"{rel}:[tools].{tool}",
                        "path": rel,
                    })
            else:
                manifests.append({
                    "tool": None,
                    "version": None,
                    "source": f"{rel}:[tools]",
                    "path": rel,
                    "note": "manifest found but no [tools] entries",
                })

    # .tool-versions
    for path in glob_sorted(root, ".tool-versions"):
        rel = relpath(root, path)
        text = read_text(path)
        tools = parse_tool_versions(text)
        if tools:
            for tool, version in tools:
                manifests.append({
                    "tool": tool,
                    "version": version or None,
                    "source": f"{rel}:{tool}",
                    "path": rel,
                })
        else:
            manifests.append({
                "tool": None,
                "version": None,
                "source": rel,
                "path": rel,
                "note": "manifest found but no tool entries",
            })

    # composer.json — require.php
    for path in glob_sorted(root, "composer.json"):
        rel = relpath(root, path)
        payload = parse_json_object(read_text(path))
        require = payload.get("require") or {}
        if isinstance(require, dict) and "php" in require:
            manifests.append({
                "tool": "php",
                "version": str(require["php"]),
                "source": f"{rel}:require.php",
                "path": rel,
            })
        else:
            manifests.append({
                "tool": "php",
                "version": None,
                "source": f"{rel}:require.php",
                "path": rel,
                "note": "composer.json found but no require.php field",
            })

    # package.json — engines.node, engines.npm
    for path in glob_sorted(root, "package.json"):
        rel = relpath(root, path)
        payload = parse_json_object(read_text(path))
        engines = payload.get("engines") or {}
        if isinstance(engines, dict):
            for engine_key in ("node", "npm"):
                if engine_key in engines:
                    manifests.append({
                        "tool": engine_key,
                        "version": str(engines[engine_key]),
                        "source": f"{rel}:engines.{engine_key}",
                        "path": rel,
                    })

    # pyproject.toml — requires-python, tool.poetry.dependencies.python
    for path in glob_sorted(root, "pyproject.toml"):
        rel = relpath(root, path)
        text = read_text(path)
        # requires-python (PEP 621)
        match = re.search(r'(?m)^requires-python\s*=\s*["\']([^"\']+)["\']', text)
        if match:
            manifests.append({
                "tool": "python",
                "version": match.group(1),
                "source": f"{rel}:requires-python",
                "path": rel,
            })
        # Poetry: [tool.poetry.dependencies] python = "..."
        poetry_match = re.search(
            r'(?ms)\[tool\.poetry\.dependencies\].*?^python\s*=\s*["\']([^"\']+)["\']',
            text,
        )
        if poetry_match:
            manifests.append({
                "tool": "python",
                "version": poetry_match.group(1),
                "source": f"{rel}:tool.poetry.dependencies.python",
                "path": rel,
            })

    # go.mod — go X.Y directive
    for path in glob_sorted(root, "go.mod"):
        rel = relpath(root, path)
        text = read_text(path)
        go_ver = extract_go_version(text)
        if go_ver:
            manifests.append({
                "tool": "go",
                "version": go_ver,
                "source": f"{rel}:go",
                "path": rel,
            })

    # Single-value version files
    single_value_files = {
        ".python-version": "python",
        ".nvmrc": "node",
        ".node-version": "node",
        ".ruby-version": "ruby",
        ".java-version": "java",
    }
    for filename, tool in single_value_files.items():
        for path in glob_sorted(root, filename):
            rel = relpath(root, path)
            version = read_single_version_file(path)
            manifests.append({
                "tool": tool,
                "version": version or None,
                "source": rel,
                "path": rel,
            })

    return manifests



def extract_go_version(go_mod_text: str) -> str:
    match = re.search(r"(?m)^go\s+([0-9.]+)$", go_mod_text)
    return match.group(1) if match else ""



def classify_name(name: str) -> str:
    lowered = name.lower()
    if any(keyword in lowered for keyword in KEYWORD_RELEASE):
        return "release/deploy"
    if any(keyword in lowered for keyword in KEYWORD_CI):
        return "ci-only"
    if any(keyword in lowered for keyword in LOCAL_HINT_KEYWORDS):
        return "local-with-deps"
    return "unknown/manual-review"



def normalize_command_line(line: str) -> str:
    stripped = line.strip()
    if stripped.startswith("$"):
        stripped = stripped[1:].strip()
    return stripped



def is_executable_file(path: Path) -> bool:
    try:
        return path.is_file() and bool(path.stat().st_mode & 0o111)
    except OSError:
        return False



def is_probable_doc_path_listing(root: Path, command: str) -> bool:
    token, _, remainder = command.partition(" ")
    comment_only_remainder = not remainder or remainder.lstrip().startswith("#")

    if DIRECT_PATH_ONLY_RE.match(token) and not remainder:
        if token.endswith("/"):
            return True
        path = root / token[2:]
        try:
            if not path.exists():
                return False
            if path.is_dir():
                return True
            if not path.is_file():
                return False
        except OSError:
            return False
        return not is_executable_file(path)

    lowered = token.lower()
    if comment_only_remainder and any(lowered.endswith(suffix) for suffix in FILE_LIKE_SUFFIXES):
        return True

    return False



def extract_command_start(command: str) -> str:
    normalized = normalize_command_line(command)
    return normalized.split(None, 1)[0] if normalized else ""



def extract_markdown_top_level_headings(text: str) -> list[str]:
    headings: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if re.match(r"^\s*```", line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = TOP_LEVEL_MARKDOWN_HEADING_RE.match(line.strip())
        if match:
            headings.append(match.group(1).strip())
    return dedupe_strings(headings)



def looks_like_command(line: str) -> bool:
    return bool(COMMAND_START_RE.match(normalize_command_line(line)))



def extract_command_lines(block: str, root: Path | None = None) -> list[str]:
    commands: list[str] = []
    for line in block.splitlines():
        command = normalize_command_line(line)
        if not command or command.startswith("#"):
            continue
        if root is not None and is_probable_doc_path_listing(root, command):
            continue
        if looks_like_command(command):
            commands.append(command)
    return dedupe_strings(commands)



def collect_step_chunk(lines: list[str], start_index: int) -> tuple[str, int]:
    base_indent = leading_spaces(lines[start_index])
    chunk_lines = [lines[start_index]]
    index = start_index + 1
    while index < len(lines):
        line = lines[index]
        if line.strip() and re.match(r"^\s*-\s+", line) and leading_spaces(line) <= base_indent:
            break
        chunk_lines.append(line)
        index += 1
    return "\n".join(chunk_lines), index



def tool_for_matrix_key(key: str) -> str:
    lowered = key.lower()
    for tool, keys in MATRIX_VERSION_KEYS.items():
        if lowered in keys:
            return tool
    return ""



def extract_matrix_versions(text: str) -> dict:
    lines = text.splitlines()
    versions = {"node": [], "python": [], "go": []}
    index = 0
    while index < len(lines):
        match = re.match(r"^(\s*)matrix:\s*$", lines[index])
        if not match:
            index += 1
            continue
        block_indent = len(match.group(1))
        index += 1
        while index < len(lines):
            line = lines[index]
            stripped = line.strip()
            if stripped and leading_spaces(line) <= block_indent:
                break
            key_match = re.match(r"^\s*([A-Za-z0-9_.-]+):\s*(.*?)\s*$", line)
            if key_match:
                key = key_match.group(1)
                tool = tool_for_matrix_key(key)
                if tool:
                    value = key_match.group(2)
                    if value:
                        versions[tool].extend(parse_literal_value_list(value))
                    else:
                        key_indent = leading_spaces(line)
                        probe = index + 1
                        while probe < len(lines):
                            next_line = lines[probe]
                            next_stripped = next_line.strip()
                            if next_stripped and leading_spaces(next_line) <= key_indent:
                                break
                            bullet = re.match(r"^\s*-\s*(.+?)\s*$", next_line)
                            if bullet and leading_spaces(next_line) > key_indent:
                                versions[tool].extend(parse_literal_value_list(bullet.group(1)))
                            probe += 1
            index += 1
    return {tool: dedupe_strings(values) for tool, values in versions.items() if values}



def extract_setup_actions(text: str) -> dict:
    lines = text.splitlines()
    details: dict[str, list[dict]] = {"node": [], "python": [], "go": []}
    for index, line in enumerate(lines):
        for tool, config in SETUP_ACTIONS.items():
            marker = config["marker"]
            if marker not in line:
                continue
            action_ref = line.split(marker, 1)[1].strip().split()[0]
            chunk, _ = collect_step_chunk(lines, index)
            versions: list[str] = []
            version_files: list[str] = []
            cache_hints: list[str] = []
            cache_dependency_paths: list[str] = []
            for key in config["version_keys"]:
                for match in re.finditer(rf"(?m)^\s*{re.escape(key)}:\s*(.+?)\s*$", chunk):
                    versions.extend(parse_literal_value_list(match.group(1)))
            for key in config["version_file_keys"]:
                for match in re.finditer(rf"(?m)^\s*{re.escape(key)}:\s*(.+?)\s*$", chunk):
                    version_files.extend(parse_literal_value_list(match.group(1)))
            for match in re.finditer(r"(?m)^\s*cache:\s*(.+?)\s*$", chunk):
                cache_hints.extend(parse_literal_value_list(match.group(1)))
            for match in re.finditer(r"(?m)^\s*cache-dependency-path:\s*(.+?)\s*$", chunk):
                cache_dependency_paths.extend(parse_literal_value_list(match.group(1)))
            details[tool].append(
                {
                    "uses": f"{marker}{action_ref}",
                    "versions": dedupe_strings(versions),
                    "version_files": dedupe_strings(version_files),
                    "cache": dedupe_strings(cache_hints),
                    "cache_dependency_paths": dedupe_strings(cache_dependency_paths),
                }
            )
    return {tool: values for tool, values in details.items() if values}



def extract_run_commands(text: str) -> list[str]:
    lines = text.splitlines()
    commands: list[str] = []
    index = 0
    while index < len(lines):
        match = RUN_LINE_RE.match(lines[index])
        if not match:
            index += 1
            continue
        indent = len(match.group(1))
        value = match.group(2).strip()
        if value and value not in {"|", ">", "|-", ">-"}:
            command = normalize_command_line(value)
            if looks_like_command(command):
                commands.append(command)
            index += 1
            continue
        index += 1
        block_lines: list[str] = []
        while index < len(lines):
            line = lines[index]
            if line.strip() and leading_spaces(line) <= indent:
                break
            if line.strip():
                content = line[indent + 2 :] if len(line) > indent + 2 else line.strip()
                block_lines.append(content)
            index += 1
        commands.extend(extract_command_lines("\n".join(block_lines)))
    return limit_values(dedupe_strings(commands), WORKFLOW_COMMAND_LIMIT)



def extract_block_mapping_keys(text: str, block_name: str) -> list[str]:
    lines = text.splitlines()
    keys: list[str] = []
    index = 0
    while index < len(lines):
        match = re.match(rf"^(\s*){re.escape(block_name)}:\s*$", lines[index])
        if not match:
            index += 1
            continue
        block_indent = len(match.group(1))
        index += 1
        while index < len(lines):
            line = lines[index]
            stripped = line.strip()
            if stripped and leading_spaces(line) <= block_indent:
                break
            key_match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*.*$", line)
            if key_match and leading_spaces(line) > block_indent:
                keys.append(key_match.group(1))
            index += 1
    return dedupe_strings(keys)



def extract_container_images(text: str) -> list[dict]:
    lines = text.splitlines()
    images: list[str] = []
    index = 0
    while index < len(lines):
        match = re.match(r"^(\s*)container:\s*(.*?)\s*$", lines[index])
        if not match:
            index += 1
            continue
        block_indent = len(match.group(1))
        value = match.group(2).strip()
        if value:
            images.extend(parse_literal_value_list(value))
            index += 1
            continue
        index += 1
        while index < len(lines):
            line = lines[index]
            stripped = line.strip()
            if stripped and leading_spaces(line) <= block_indent:
                break
            image_match = re.match(r"^\s*image:\s*(.+?)\s*$", line)
            if image_match:
                images.extend(parse_literal_value_list(image_match.group(1)))
            index += 1
    return [parse_image_ref(image) for image in dedupe_strings(images)]



def extract_services(text: str) -> list[dict]:
    lines = text.splitlines()
    services: list[dict] = []
    index = 0
    while index < len(lines):
        match = re.match(r"^(\s*)services:\s*$", lines[index])
        if not match:
            index += 1
            continue
        block_indent = len(match.group(1))
        index += 1
        while index < len(lines):
            line = lines[index]
            stripped = line.strip()
            if stripped and leading_spaces(line) <= block_indent:
                break
            service_match = re.match(r"^\s*([A-Za-z0-9_.-]+):\s*$", line)
            if service_match and leading_spaces(line) > block_indent:
                service_indent = leading_spaces(line)
                name = service_match.group(1)
                image = ""
                build = ""
                probe = index + 1
                while probe < len(lines):
                    next_line = lines[probe]
                    next_stripped = next_line.strip()
                    if next_stripped and leading_spaces(next_line) <= service_indent:
                        break
                    image_match = re.match(r"^\s*image:\s*(.+?)\s*$", next_line)
                    build_match = re.match(r"^\s*build:\s*(.+?)\s*$", next_line)
                    if image_match and not image:
                        image = normalize_scalar(image_match.group(1))
                    if build_match and not build:
                        build = normalize_scalar(build_match.group(1))
                    probe += 1
                services.append(
                    {
                        "name": name,
                        "image": parse_image_ref(image) if image else None,
                        "build": build,
                    }
                )
                index = probe
                continue
            index += 1

    deduped: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for service in services:
        image_raw = service["image"]["raw"] if service["image"] else ""
        key = (service["name"], service["build"], image_raw)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(service)
    return deduped



def detect_package_manager_hints(text: str, run_commands: list[str]) -> list[str]:
    haystack = "\n".join([text.lower(), *[command.lower() for command in run_commands]])
    hints: list[str] = []
    for name, patterns in PACKAGE_MANAGER_HINTS.items():
        if any(re.search(pattern, haystack) for pattern in patterns):
            hints.append(name)
    return hints



def extract_cache_hints(text: str) -> list[str]:
    hints: list[str] = []
    for match in re.finditer(r"(?m)^\s*cache:\s*(.+?)\s*$", text):
        hints.extend(parse_literal_value_list(match.group(1)))
    if "actions/cache@" in text:
        hints.append("actions/cache")
    if "cache-dependency-path:" in text:
        hints.append("cache-dependency-path")
    return dedupe_strings(hints)



def extract_docker_hints(text: str, run_commands: list[str]) -> list[str]:
    lowered = text.lower()
    hints: list[str] = []
    for action in DOCKER_ACTION_HINTS:
        if action in lowered:
            hints.append(action)
    for command in run_commands:
        command_lower = command.lower()
        if any(pattern in command_lower for pattern in DOCKER_COMMAND_HINT_PATTERNS):
            hints.append(command)
    return dedupe_strings(hints)



def extract_guidance_markers(text: str) -> list[str]:
    lowered = text.lower()
    markers = [marker for marker in GUIDANCE_MARKERS if marker.lower() in lowered]
    return dedupe_strings(markers)



def scan_workflows(root: Path) -> tuple[list[str], list[dict]]:
    workflows_dir = root / ".github" / "workflows"
    workflow_paths: list[Path] = []
    if workflows_dir.is_dir():
        for ext in ("*.yml", "*.yaml"):
            workflow_paths.extend(sorted(workflows_dir.glob(ext)))
    workflow_paths = sorted(set(workflow_paths))
    details: list[dict] = []
    for path in workflow_paths:
        text = read_text(path)
        run_commands = extract_run_commands(text)
        details.append(
            {
                "path": relpath(root, path),
                "setup_actions": extract_setup_actions(text),
                "matrix_versions": extract_matrix_versions(text),
                "package_manager_hints": detect_package_manager_hints(text, run_commands),
                "cache_hints": extract_cache_hints(text),
                "env_var_names": extract_block_mapping_keys(text, "env"),
                "referenced_env_var_names": dedupe_strings(ENV_REF_RE.findall(text)),
                "secret_names": dedupe_strings(SECRET_RE.findall(text)),
                "vars_names": dedupe_strings(VAR_RE.findall(text)),
                "services": extract_services(text),
                "container_images": extract_container_images(text),
                "docker_hints": extract_docker_hints(text, run_commands),
                "run_commands": run_commands,
            }
        )
    return [relpath(root, path) for path in workflow_paths], details



def scan_python(root: Path) -> dict:
    packaging_surfaces = sorted(
        {
            relpath(root, path)
            for pattern in (
                "pyproject.toml",
                "requirements*.txt",
                "tox.ini",
                "setup.cfg",
                "setup.py",
                "Pipfile",
                "poetry.lock",
                "uv.lock",
                "environment.yml",
                "environment.yaml",
                "runtime.txt",
            )
            for path in glob_sorted(root, pattern)
        }
    )

    source_files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        dirnames[:] = [name for name in dirnames if name not in PYTHON_SOURCE_SKIP_DIRS and name != ".git"]
        base = Path(dirpath)
        for filename in filenames:
            path = base / filename
            if path.suffix.lower() in PYTHON_SOURCE_SUFFIXES:
                source_files.append(relpath(root, path))
    source_files = sorted(source_files)

    return {
        "packaging_surfaces": packaging_surfaces,
        "source_files": {
            "count": len(source_files),
            "sample_paths": limit_values(source_files, PYTHON_SOURCE_SAMPLE_LIMIT),
        },
    }



def scan_dockerfiles(root: Path) -> tuple[list[str], list[dict]]:
    dockerfile_paths = sorted(
        {
            *glob_sorted(root, "Dockerfile"),
            *glob_sorted(root, "Dockerfile*"),
        }
    )
    details: list[dict] = []
    for path in dockerfile_paths:
        from_lines: list[dict] = []
        for line_number, line in enumerate(read_text(path).splitlines(), start=1):
            match = re.match(r"^\s*FROM\s+([^\s]+)(?:\s+AS\s+([A-Za-z0-9_.-]+))?\s*$", line, re.IGNORECASE)
            if not match:
                continue
            from_lines.append(
                {
                    "line": line_number,
                    "raw": line.strip(),
                    "image": parse_image_ref(match.group(1)),
                    "stage_name": match.group(2) or "",
                }
            )
        details.append(
            {
                "path": relpath(root, path),
                "stage_count": len(from_lines),
                "multi_stage": len(from_lines) > 1,
                "from_lines": from_lines,
            }
        )
    return [relpath(root, path) for path in dockerfile_paths], details



def scan_compose(root: Path) -> tuple[list[str], list[dict]]:
    compose_paths = sorted(
        {
            relpath(root, path): path
            for pattern in ("docker-compose*.yml", "docker-compose*.yaml", "compose*.yml", "compose*.yaml")
            for path in glob_sorted(root, pattern)
        }.values()
    )
    details: list[dict] = []
    for path in compose_paths:
        details.append({"path": relpath(root, path), "services": extract_services(read_text(path))})
    return [relpath(root, path) for path in compose_paths], details



def parse_json_object(text: str) -> dict:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}



def json_string_field(payload: dict, key: str) -> str:
    value = payload.get(key)
    return value if isinstance(value, str) else ""



def json_string_list_field(payload: dict, key: str) -> list[str]:
    value = payload.get(key)
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return dedupe_strings([item for item in value if isinstance(item, str)])
    return []



def scan_devcontainers(root: Path) -> tuple[list[str], list[dict]]:
    surfaces = sorted([relpath(root, path) for path in glob_sorted(root, ".devcontainer/*")])
    details: list[dict] = []
    for path in glob_sorted(root, ".devcontainer/*.json"):
        payload = parse_json_object(read_text(path))
        details.append(
            {
                "path": relpath(root, path),
                "image": json_string_field(payload, "image"),
                "dockerfile": json_string_field(payload, "dockerFile"),
                "docker_compose_files": json_string_list_field(payload, "dockerComposeFile"),
                "service": json_string_field(payload, "service"),
                "run_services": json_string_list_field(payload, "runServices"),
            }
        )
    return surfaces, details



def collect_root_guidance_paths(root: Path) -> list[Path]:
    candidate_paths: list[Path] = []
    for path in sorted(root.glob("README*")):
        if path.is_file():
            candidate_paths.append(path)
    for name in ("AGENTS.md", "CLAUDE.md"):
        path = root / name
        if path.is_file():
            candidate_paths.append(path)

    unique_paths: list[Path] = []
    seen: set[str] = set()
    for path in candidate_paths:
        relative = relpath(root, path)
        if relative in seen:
            continue
        seen.add(relative)
        unique_paths.append(path)
    return unique_paths



def scan_markdown_guidance_surface(root: Path, path: Path) -> dict:
    text = read_text(path)
    fence_matches = list(DOC_FENCE_RE.finditer(text))
    shell_fence_matches = [
        match for match in fence_matches if (match.group("lang") or "").strip().lower() in SHELL_FENCE_LANGUAGES
    ]
    commands: list[str] = []
    for match in shell_fence_matches:
        commands.extend(extract_command_lines(match.group("body"), root=root))
    command_hints = limit_values(dedupe_strings(commands), DOC_COMMAND_LIMIT)
    return {
        "path": relpath(root, path),
        "top_level_headings": limit_values(extract_markdown_top_level_headings(text), ROOT_GUIDANCE_HEADING_LIMIT),
        "fenced_block_count": len(fence_matches),
        "shell_fenced_block_count": len(shell_fence_matches),
        "command_hints": command_hints,
        "command_starts": limit_values(
            dedupe_strings([extract_command_start(command) for command in command_hints]),
            ROOT_GUIDANCE_COMMAND_START_LIMIT,
        ),
        "literal_markers": extract_guidance_markers(text),
    }



def scan_root_guidance_surfaces(root: Path) -> list[dict]:
    surfaces: list[dict] = []
    for path in collect_root_guidance_paths(root):
        surface = scan_markdown_guidance_surface(root, path)
        surface["kind"] = (
            "agents_md"
            if path.name == "AGENTS.md"
            else "claude_md"
            if path.name == "CLAUDE.md"
            else "readme"
        )
        surfaces.append(surface)
    return surfaces



def scan_documented_commands(root: Path) -> tuple[list[dict], list[dict]]:
    candidate_paths = collect_root_guidance_paths(root)
    docs_dir = root / "docs"
    if docs_dir.is_dir():
        candidate_paths.extend(sorted(path for path in docs_dir.rglob("*.md") if path.is_file()))

    unique_paths: list[Path] = []
    seen: set[str] = set()
    for path in candidate_paths:
        relative = relpath(root, path)
        if relative in seen:
            continue
        seen.add(relative)
        unique_paths.append(path)
    unique_paths = unique_paths[:DOC_FILE_LIMIT]

    command_hints: list[dict] = []
    literal_markers: list[dict] = []
    for path in unique_paths:
        surface = scan_markdown_guidance_surface(root, path)
        if surface["command_hints"]:
            command_hints.append({"path": surface["path"], "commands": surface["command_hints"]})
        if surface["literal_markers"]:
            literal_markers.append({"path": surface["path"], "markers": surface["literal_markers"]})
    return command_hints, literal_markers



def scan_shell_entry_scripts(root: Path) -> list[dict]:
    candidates: list[dict] = []
    for relative_dir in (".", "scripts", "bin", "tools"):
        directory = root if relative_dir == "." else root / relative_dir
        if not directory.is_dir():
            continue
        for path in sorted(directory.iterdir()):
            if not path.is_file() or path.name.startswith("."):
                continue
            try:
                with path.open("r", encoding="utf-8", errors="replace") as handle:
                    first_line = handle.readline().strip()
            except OSError:
                first_line = ""
            shebang = first_line if first_line.startswith("#!") else ""
            try:
                executable = bool(path.stat().st_mode & 0o111)
            except OSError:
                executable = False
            is_shell = path.suffix == ".sh" or any(token in shebang for token in ("/sh", "bash", "zsh"))
            if not is_shell:
                continue
            candidates.append(
                {
                    "path": relpath(root, path),
                    "executable": executable,
                    "shebang": shebang,
                }
            )
    return dedupe_objects(candidates, ("path",))



def build_candidate_entrypoints(scan: dict) -> list[dict]:
    candidates: list[dict] = []
    for makefile in scan["makefiles"]:
        for target in makefile["public_targets"]:
            candidates.append(
                {
                    "source": makefile["path"],
                    "kind": "make-target",
                    "label": target,
                    "invocation_hint": f"make {target}",
                    "classification": classify_name(target),
                    "validated_local_flow": False,
                }
            )
    for package in scan["package_json"]:
        for script in package["scripts"]:
            candidates.append(
                {
                    "source": package["path"],
                    "kind": "package-script",
                    "label": script,
                    "invocation_hint": f"package script key `{script}` (package manager not inferred)",
                    "classification": classify_name(script),
                    "validated_local_flow": False,
                }
            )
    for composer in scan.get("composer_json", []):
        for script in composer["scripts"]:
            candidates.append(
                {
                    "source": composer["path"],
                    "kind": "composer-script",
                    "label": script,
                    "invocation_hint": f"composer run-script {script}",
                    "classification": classify_name(script),
                    "validated_local_flow": False,
                }
            )
    for workflow in scan["workflow_details"]:
        for command in workflow["run_commands"]:
            candidates.append(
                {
                    "source": workflow["path"],
                    "kind": "workflow-run-command",
                    "label": command,
                    "invocation_hint": "literal GitHub Actions run step",
                    "classification": classify_name(command),
                    "validated_local_flow": False,
                }
            )
    for doc in scan["documented_command_hints"]:
        for command in doc["commands"]:
            candidates.append(
                {
                    "source": doc["path"],
                    "kind": "documented-command",
                    "label": command,
                    "invocation_hint": "literal fenced-code command",
                    "classification": classify_name(command),
                    "validated_local_flow": False,
                }
            )
    for script in scan["shell_entry_scripts"]:
        candidates.append(
            {
                "source": script["path"],
                "kind": "shell-script",
                "label": script["path"],
                "invocation_hint": f"./{script['path']}",
                "classification": classify_name(script["path"]),
                "validated_local_flow": False,
            }
        )
    return dedupe_objects(candidates, ("source", "kind", "label"))



def scan_repo(root: Path) -> dict:
    root_readmes = sorted([path.name for path in root.glob("README*") if path.is_file()])
    workflows, workflow_details = scan_workflows(root)

    makefiles = []
    for path in glob_sorted(root, "Makefile*"):
        makefiles.append(
            {
                "path": relpath(root, path),
                "public_targets": parse_make_public_targets(read_text(path)),
            }
        )

    package_json = []
    for path in glob_sorted(root, "package.json"):
        package_json.append(
            {
                "path": relpath(root, path),
                "scripts": parse_package_scripts(read_text(path)),
            }
        )

    python = scan_python(root)

    go_mods = []
    for path in glob_sorted(root, "go.mod"):
        go_mods.append({"path": relpath(root, path), "go_version": extract_go_version(read_text(path))})

    composer_json = []
    for path in glob_sorted(root, "composer.json"):
        parsed = parse_composer_json(read_text(path))
        composer_json.append({
            "path": relpath(root, path),
            "scripts": parsed["scripts"],
            "require": parsed["require"],
            "require_dev": parsed["require_dev"],
            "platform": parsed["platform"],
        })

    cargo_toml = sorted([relpath(root, path) for path in glob_sorted(root, "Cargo.toml")])

    docker_surfaces, dockerfiles = scan_dockerfiles(root)
    compose_surfaces, compose_details = scan_compose(root)
    devcontainer_surfaces, devcontainer_details = scan_devcontainers(root)

    version_tooling_surfaces = sorted(
        [
            relpath(root, path)
            for pattern in (
                "mise.toml",
                ".mise.toml",
                ".tool-versions",
                ".nvmrc",
                ".python-version",
                ".node-version",
                ".ruby-version",
                ".java-version",
                "rust-toolchain",
                "rust-toolchain.toml",
            )
            for path in glob_sorted(root, pattern)
        ]
    )

    runtime_manifests = scan_runtime_manifests(root)

    gitignore_surfaces = sorted([relpath(root, path) for path in glob_sorted(root, ".gitignore")])
    root_guidance_surfaces = scan_root_guidance_surfaces(root)

    prompt_agent_surfaces: list[str] = []
    for candidate in ("prompt-sources", "agents", "agent-prompts", ".codex", ".claude"):
        if (root / candidate).exists():
            prompt_agent_surfaces.append(candidate)
    for candidate in ("AGENTS.md", "CLAUDE.md"):
        if (root / candidate).is_file():
            prompt_agent_surfaces.append(candidate)

    documented_command_hints, literal_guidance_markers = scan_documented_commands(root)
    shell_entry_scripts = scan_shell_entry_scripts(root)

    scan = {
        "important_files": {
            "readme": root_readmes,
            "agents_md": ["AGENTS.md"] if (root / "AGENTS.md").is_file() else [],
            "claude_md": ["CLAUDE.md"] if (root / "CLAUDE.md").is_file() else [],
            "gitignore": gitignore_surfaces,
        },
        "workflows": workflows,
        "workflow_details": workflow_details,
        "root_guidance_surfaces": root_guidance_surfaces,
        "makefiles": makefiles,
        "package_json": package_json,
        "composer_json": composer_json,
        "python": python,
        "go_mods": go_mods,
        "cargo_toml": cargo_toml,
        "runtime_manifests": runtime_manifests,
        "docker_surfaces": docker_surfaces,
        "dockerfiles": dockerfiles,
        "compose_surfaces": compose_surfaces,
        "compose_details": compose_details,
        "devcontainer_surfaces": devcontainer_surfaces,
        "devcontainer_details": devcontainer_details,
        "version_tooling_surfaces": version_tooling_surfaces,
        "prompt_agent_surfaces": sorted(prompt_agent_surfaces),
        "documented_command_hints": documented_command_hints,
        "literal_guidance_markers": literal_guidance_markers,
        "shell_entry_scripts": shell_entry_scripts,
    }
    scan["candidate_entrypoints"] = build_candidate_entrypoints(scan)
    return scan



def build_findings(scan: dict) -> list[dict]:
    findings: list[dict] = []

    if scan["workflows"]:
        findings.append(
            {
                "kind": "ci-only",
                "confidence": "medium",
                "summary": "GitHub Actions workflows and literal workflow metadata were detected. Treat workflow commands as CI hints, not validated local flows.",
                "evidence": limit_values(scan["workflows"], 5),
            }
        )

    release_evidence: list[str] = []
    release_evidence.extend(
        [path for path in scan["workflows"] if any(keyword in path.lower() for keyword in KEYWORD_RELEASE)]
    )
    for entrypoint in scan["candidate_entrypoints"]:
        if entrypoint["classification"] == "release/deploy":
            release_evidence.append(f"{entrypoint['source']}::{entrypoint['label']}")
    for workflow in scan["workflow_details"]:
        for hint in workflow["docker_hints"]:
            if "build-push" in hint.lower() or "docker push" in hint.lower():
                release_evidence.append(f"{workflow['path']}::{hint}")
    release_evidence = dedupe_strings(release_evidence)
    if release_evidence:
        findings.append(
            {
                "kind": "release/deploy",
                "confidence": "medium",
                "summary": "Release/deploy-shaped names or docker publish hints were detected in deterministic metadata.",
                "evidence": limit_values(release_evidence, 8),
            }
        )

    if scan["candidate_entrypoints"]:
        findings.append(
            {
                "kind": "manual-review",
                "confidence": "medium",
                "summary": "Candidate entrypoints were cataloged from files, docs, and workflows, but they are not validated as a local runbook.",
                "evidence": limit_values(
                    [
                        f"{entrypoint['kind']}::{entrypoint['source']}::{entrypoint['label']}"
                        for entrypoint in scan["candidate_entrypoints"]
                    ],
                    10,
                ),
            }
        )
    else:
        findings.append(
            {
                "kind": "manual-review",
                "confidence": "low",
                "summary": "No candidate entrypoints were detected from Makefiles, package scripts, workflow run steps, docs, or shell entry scripts.",
                "evidence": [],
            }
        )

    low_signal = not any(
        (
            scan["workflows"],
            scan["candidate_entrypoints"],
            scan["dockerfiles"],
            scan["compose_details"],
            scan["documented_command_hints"],
            scan["python"]["packaging_surfaces"],
            scan["python"]["source_files"]["count"],
            scan["go_mods"],
            scan["cargo_toml"],
            scan.get("composer_json"),
        )
    )
    if low_signal:
        findings.append(
            {
                "kind": "low-confidence",
                "confidence": "low",
                "summary": "Repository has very limited deterministic execution metadata. Additional manual inspection is required before running commands.",
                "evidence": [],
            }
        )

    return findings



def build_unknowns(scan: dict) -> list[str]:
    unknowns = [
        "Which candidate entrypoints are currently valid local commands versus stale hints.",
        "Which package manager or wrapper should invoke package.json script keys.",
        "Which credentials, services, containers, or external systems are required for each candidate flow.",
        "Whether documented commands, workflow commands, and shell entry scripts still match the current repo state.",
        "Semantic contradictions or prose intent are intentionally not inferred by this deterministic scanner.",
    ]
    if not scan["workflows"]:
        unknowns.append("No .github/workflows definitions were detected.")
    if not scan["candidate_entrypoints"]:
        unknowns.append("No candidate entrypoints were detected from deterministic patterns.")
    if not scan["python"]["packaging_surfaces"] and not scan["python"]["source_files"]["count"]:
        unknowns.append("No Python packaging/config surfaces or Python source/script files were detected.")
    if not scan["dockerfiles"] and not scan["compose_details"] and not scan["devcontainer_details"]:
        unknowns.append("No Dockerfile, Compose, or devcontainer metadata was detected.")
    return unknowns



def build_next_actions(scan: dict) -> list[str]:
    actions = [
        "Use this contract as a dumb catalog of candidate entrypoints, setup metadata, guardrails, and unknowns — not as a validated runbook.",
        "Inspect the referenced Makefiles, package.json files, workflow files, docs, and shell scripts before running any non-trivial command.",
        "Reconstruct local environment requirements from literal workflow/docker metadata instead of assuming CI maps 1:1 to local execution.",
        "Treat manual-review, ci-only, release/deploy, and low-confidence findings as guardrails, not permission to guess.",
    ]
    if scan["documented_command_hints"]:
        actions.append("Validate documented command hints against current repo files; they are literal extracts, not semantic recommendations.")
    if any(item["kind"] == "package-script" for item in scan["candidate_entrypoints"]):
        actions.append("Determine the correct package manager from repo tooling before invoking any package.json script key.")
    if scan["workflows"]:
        actions.append("Inspect workflow steps for exact env, secret, service, and container requirements before attempting local reproduction.")
    return actions



def build_contract(root: Path, repo_name: str, verify: bool) -> dict:
    scan = scan_repo(root)
    findings = build_findings(scan)
    has_low = any(finding["kind"] == "low-confidence" for finding in findings)
    status = "manual-review" if has_low else "hybrid"
    confidence = "low" if has_low else "medium"

    contract = {
        "schema_version": SCHEMA_VERSION,
        "repo": repo_name,
        "status": status,
        "confidence": confidence,
        "deterministic_facts": scan,
        "findings": findings,
        "guardrails": [
            "manual-review findings mean inspect the referenced files before execution; do not improvise a runbook.",
            "ci-only findings indicate workflow-only evidence; local execution still needs explicit validation.",
            "release/deploy findings require guarded operator context and explicit intent.",
            "low-confidence findings mean the scanner found too little metadata to safely reconstruct execution from patterns alone.",
        ],
        "unknowns": build_unknowns(scan),
        "next_actions": build_next_actions(scan),
        "verification": {
            "requested": verify,
            "mode": "compat-no-op",
            "results": [],
            "notes": [
                "--verify-supported is preserved for hook compatibility.",
                "No repo-specific truth table verification is executed in this generic scanner.",
            ]
            if verify
            else [],
        },
        "compat": {
            "verify_supported_flag": "accepted",
            "enforce_supported_flag": "accepted-no-op",
        },
    }
    return contract



def render_section_list(lines: list[str], title: str, values: list[str]) -> None:
    lines.append(f"### {title}")
    if not values:
        lines.append("- none")
    else:
        for value in values:
            lines.append(f"- `{value}`")
    lines.append("")



def render_inline_list(values: list[str], limit: int | None = None) -> str:
    unique = dedupe_strings(values)
    if not unique:
        return "none"
    if limit is None or len(unique) <= limit:
        return ", ".join(f"`{value}`" for value in unique)
    visible = ", ".join(f"`{value}`" for value in unique[:limit])
    return f"{visible}, `+{len(unique) - limit} more`"



def render_root_guidance_surfaces(lines: list[str], surfaces: list[dict]) -> None:
    lines.append("### Root guidance surface metadata")
    if not surfaces:
        lines.append("- none")
        lines.append("")
        return
    for surface in surfaces:
        lines.append(f"- `{surface['path']}` (`{surface['kind']}`)")
        lines.append(f"  - top-level headings: {render_inline_list(surface['top_level_headings'], limit=ROOT_GUIDANCE_HEADING_LIMIT)}")
        lines.append(
            f"  - fenced blocks: `{surface['fenced_block_count']}`; shell/console fenced blocks: `{surface['shell_fenced_block_count']}`"
        )
        lines.append(
            f"  - command starts: {render_inline_list(surface['command_starts'], limit=ROOT_GUIDANCE_COMMAND_START_LIMIT)}"
        )
        lines.append(f"  - command hints: {render_inline_list(surface['command_hints'], limit=DOC_COMMAND_LIMIT)}")
        lines.append(f"  - literal markers: {render_inline_list(surface['literal_markers'], limit=6)}")
    lines.append("")



def render_workflow_details(lines: list[str], workflows: list[dict]) -> None:
    lines.append("### Workflow metadata")
    if not workflows:
        lines.append("- none")
        lines.append("")
        return
    for workflow in workflows:
        lines.append(f"- `{workflow['path']}`")
        setup_actions = workflow["setup_actions"]
        if setup_actions:
            for tool in ("node", "python", "go"):
                entries = setup_actions.get(tool) or []
                if not entries:
                    continue
                versions = dedupe_strings([value for entry in entries for value in entry["versions"]])
                version_files = dedupe_strings([value for entry in entries for value in entry["version_files"]])
                cache_hints = dedupe_strings([value for entry in entries for value in entry["cache"]])
                lines.append(
                    f"  - setup-{tool}: versions {render_inline_list(versions, limit=4)}; version files {render_inline_list(version_files, limit=4)}; cache {render_inline_list(cache_hints, limit=4)}"
                )
        matrix_versions = workflow["matrix_versions"]
        if matrix_versions:
            parts = [f"{tool}={render_inline_list(values, limit=6)}" for tool, values in matrix_versions.items()]
            lines.append(f"  - matrix versions: {', '.join(parts)}")
        lines.append(
            f"  - package manager hints: {render_inline_list(workflow['package_manager_hints'], limit=6)}; cache hints: {render_inline_list(workflow['cache_hints'], limit=6)}"
        )
        lines.append(
            f"  - env vars: {render_inline_list(workflow['env_var_names'], limit=6)}; referenced env vars: {render_inline_list(workflow['referenced_env_var_names'], limit=6)}"
        )
        lines.append(
            f"  - secrets: {render_inline_list(workflow['secret_names'], limit=6)}; vars: {render_inline_list(workflow['vars_names'], limit=6)}"
        )
        if workflow["services"]:
            rendered_services = []
            for service in workflow["services"]:
                image = service["image"]["raw"] if service["image"] else ""
                build = service["build"] or ""
                details = ", ".join(value for value in (image, build) if value) or "metadata only"
                rendered_services.append(f"{service['name']} ({details})")
            lines.append(f"  - services: {render_inline_list(rendered_services, limit=4)}")
        else:
            lines.append("  - services: none")
        container_images = [image["raw"] for image in workflow["container_images"] if image["raw"]]
        lines.append(f"  - container images: {render_inline_list(container_images, limit=4)}")
        lines.append(f"  - docker/build hints: {render_inline_list(workflow['docker_hints'], limit=4)}")
        lines.append(
            f"  - workflow run commands (sample): {render_inline_list(limit_values(workflow['run_commands'], WORKFLOW_RUN_DISPLAY_LIMIT), limit=4)}"
        )
    lines.append("")



def render_candidate_entrypoints(lines: list[str], entrypoints: list[dict]) -> None:
    lines.append("### Candidate entrypoints")
    if not entrypoints:
        lines.append("- none")
        lines.append("")
        return
    for entrypoint in limit_values(entrypoints, ENTRYPOINT_DISPLAY_LIMIT):
        lines.append(
            "- "
            f"`{entrypoint['kind']}` from `{entrypoint['source']}` -> `{entrypoint['label']}` "
            f"(hint: {entrypoint['invocation_hint']}; classification: `{entrypoint['classification']}`; validated: `false`)"
        )
    remaining = len(entrypoints) - ENTRYPOINT_DISPLAY_LIMIT
    if remaining > 0:
        lines.append(f"- `{remaining}` more candidate entrypoints are preserved in the JSON artifact")
    lines.append("")



def render_documented_commands(lines: list[str], hints: list[dict]) -> None:
    lines.append("### Documented command hints")
    if not hints:
        lines.append("- none")
        lines.append("")
        return
    for hint in hints:
        lines.append(f"- `{hint['path']}` -> {render_inline_list(hint['commands'])}")
    lines.append("")



def render_guidance_markers(lines: list[str], markers: list[dict]) -> None:
    lines.append("### Literal guidance markers")
    if not markers:
        lines.append("- none")
        lines.append("")
        return
    for marker in markers:
        lines.append(f"- `{marker['path']}` -> {render_inline_list(marker['markers'])}")
    lines.append("")



def render_python(lines: list[str], python: dict) -> None:
    render_section_list(lines, "Python packaging/config surfaces", python["packaging_surfaces"])
    lines.append("### Python source/script presence")
    lines.append(f"- count: `{python['source_files']['count']}`")
    sample_paths = python["source_files"]["sample_paths"]
    if sample_paths:
        lines.append(f"- sample paths: {render_inline_list(sample_paths)}")
    else:
        lines.append("- sample paths: none")
    lines.append("")



def render_go(lines: list[str], go_mods: list[dict]) -> None:
    lines.append("### Go module surfaces")
    if not go_mods:
        lines.append("- none")
        lines.append("")
        return
    for item in go_mods:
        version = item["go_version"] or "unknown"
        lines.append(f"- `{item['path']}` -> go `{version}`")
    lines.append("")



def render_docker(lines: list[str], facts: dict) -> None:
    lines.append("### Dockerfile metadata")
    if not facts["dockerfiles"]:
        lines.append("- none")
    else:
        for dockerfile in facts["dockerfiles"]:
            images = [entry["image"]["raw"] for entry in dockerfile["from_lines"] if entry["image"]["raw"]]
            mode = "multi-stage" if dockerfile["multi_stage"] else "single-stage"
            lines.append(
                f"- `{dockerfile['path']}` -> stages: `{dockerfile['stage_count']}` ({mode}); FROM images: {render_inline_list(images)}"
            )
    lines.append("")

    lines.append("### Compose metadata")
    if not facts["compose_details"]:
        lines.append("- none")
    else:
        for compose in facts["compose_details"]:
            services = []
            for service in compose["services"]:
                image = service["image"]["raw"] if service["image"] else ""
                build = service["build"] or ""
                detail = ", ".join(value for value in (image, build) if value) or "metadata only"
                services.append(f"{service['name']} ({detail})")
            lines.append(f"- `{compose['path']}` -> services: {render_inline_list(services)}")
    lines.append("")

    lines.append("### Devcontainer metadata")
    if not facts["devcontainer_details"]:
        lines.append("- none")
    else:
        for devcontainer in facts["devcontainer_details"]:
            details = []
            if devcontainer["image"]:
                details.append(f"image={devcontainer['image']}")
            if devcontainer["dockerfile"]:
                details.append(f"dockerfile={devcontainer['dockerfile']}")
            if devcontainer["docker_compose_files"]:
                details.append(f"compose={', '.join(devcontainer['docker_compose_files'])}")
            if devcontainer["service"]:
                details.append(f"service={devcontainer['service']}")
            if devcontainer["run_services"]:
                details.append(f"runServices={', '.join(devcontainer['run_services'])}")
            rendered = ", ".join(details) if details else "metadata only"
            lines.append(f"- `{devcontainer['path']}` -> {rendered}")
    lines.append("")



def render_markdown(contract: dict) -> str:
    facts = contract["deterministic_facts"]
    lines = [
        "# Repo execution contract",
        "",
        f"- Repo: `{contract['repo']}`",
        f"- Schema: `{contract['schema_version']}`",
        f"- Status: `{contract['status']}`",
        f"- Confidence: `{contract['confidence']}`",
        "",
        "## How to use this contract",
        "",
        "- This is a dumb deterministic scanner output: candidate entrypoints, setup metadata, guardrails, and unknowns.",
        "- Deterministic facts in this document come from the JSON artifact and only reflect files, structured metadata, and literal pattern matches.",
        "- The JSON artifact is authoritative; this markdown is a rendered summary.",
        "- This is not a validated local runbook. Read the referenced files before executing ambiguous or operationally sensitive commands.",
        "- manual-review / ci-only / release/deploy / low-confidence findings are guardrails, not permission to guess.",
        "",
        "## Deterministic facts",
        "",
    ]

    render_section_list(lines, "README surfaces", facts["important_files"]["readme"])
    render_section_list(lines, "AGENTS.md surfaces", facts["important_files"]["agents_md"])
    render_section_list(lines, "CLAUDE.md surfaces", facts["important_files"]["claude_md"])
    render_root_guidance_surfaces(lines, facts["root_guidance_surfaces"])
    render_section_list(lines, "Gitignore surfaces", facts["important_files"]["gitignore"])
    render_section_list(lines, "Workflow surfaces", facts["workflows"])
    render_workflow_details(lines, facts["workflow_details"])

    lines.append("### Makefile surfaces")
    if not facts["makefiles"]:
        lines.append("- none")
    else:
        for item in facts["makefiles"]:
            targets = render_inline_list(item["public_targets"])
            lines.append(f"- `{item['path']}` -> public targets: {targets}")
    lines.append("")

    lines.append("### package.json script surfaces")
    if not facts["package_json"]:
        lines.append("- none")
    else:
        for item in facts["package_json"]:
            scripts = render_inline_list(item["scripts"])
            lines.append(f"- `{item['path']}` -> scripts: {scripts}")
    lines.append("")

    render_candidate_entrypoints(lines, facts["candidate_entrypoints"])
    render_documented_commands(lines, facts["documented_command_hints"])
    render_guidance_markers(lines, facts["literal_guidance_markers"])

    lines.append("### composer.json surfaces")
    if not facts.get("composer_json"):
        lines.append("- none")
    else:
        for item in facts["composer_json"]:
            scripts = render_inline_list(item["scripts"])
            php_ver = item["require"].get("php", "")
            php_info = f"; php version: `{php_ver}`" if php_ver else ""
            lines.append(f"- `{item['path']}` -> scripts: {scripts}{php_info}")
            require_keys = [k for k in sorted(item["require"].keys()) if k != "php"][:10]
            if require_keys:
                lines.append(f"  - require: {render_inline_list(require_keys, limit=10)}")
            require_dev_keys = sorted(item["require_dev"].keys())[:10]
            if require_dev_keys:
                lines.append(f"  - require-dev: {render_inline_list(require_dev_keys, limit=10)}")
            if item["platform"]:
                platform_items = [f"{k}={v}" for k, v in sorted(item["platform"].items())]
                lines.append(f"  - config.platform: {render_inline_list(platform_items, limit=6)}")
    lines.append("")

    render_python(lines, facts["python"])
    render_go(lines, facts["go_mods"])
    render_section_list(lines, "Cargo surfaces", facts["cargo_toml"])
    render_section_list(lines, "Docker/Compose surfaces", dedupe_strings(facts["docker_surfaces"] + facts["compose_surfaces"]))
    render_docker(lines, facts)
    render_section_list(lines, "Devcontainer surfaces", facts["devcontainer_surfaces"])
    render_section_list(lines, "Version/tooling surfaces", facts["version_tooling_surfaces"])

    lines.append("### Runtime manifests (version pins)")
    runtime_manifests = facts.get("runtime_manifests", [])
    if not runtime_manifests:
        lines.append("- none")
    else:
        for entry in runtime_manifests:
            tool = entry.get("tool") or "unknown"
            version = entry.get("version")
            source = entry.get("source", "")
            note = entry.get("note", "")
            if version:
                lines.append(f"- `{tool}` = `{version}` (from `{source}`)")
            elif note:
                lines.append(f"- `{source}`: {note}")
            else:
                lines.append(f"- `{tool}` from `{source}`: version not specified")
    lines.append("")

    render_section_list(lines, "Prompt/agent surfaces", facts["prompt_agent_surfaces"])

    lines.extend(["## Findings", ""])
    for finding in contract["findings"]:
        evidence = render_inline_list(finding["evidence"])
        lines.append(f"- `{finding['kind']}` (`{finding['confidence']}`): {finding['summary']} (evidence: {evidence})")
    lines.append("")

    lines.extend(["## Guardrails", ""])
    for guardrail in contract["guardrails"]:
        lines.append(f"- {guardrail}")
    lines.append("")

    lines.extend(["## Unknowns", ""])
    for unknown in contract["unknowns"]:
        lines.append(f"- {unknown}")
    lines.append("")

    lines.extend(["## Next actions", ""])
    for action in contract["next_actions"]:
        lines.append(f"- {action}")
    lines.append("")

    lines.extend(["## Verification compatibility", ""])
    verification = contract["verification"]
    lines.append(f"- `--verify-supported` requested: `{verification['requested']}`")
    lines.append(f"- Mode: `{verification['mode']}`")
    if verification["notes"]:
        for note in verification["notes"]:
            lines.append(f"- {note}")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"



def main() -> int:
    args = parse_args()
    root = Path(args.repo_root).resolve()
    repo_name = resolve_repo_name(root, args.repo_name)
    contract = build_contract(root, repo_name, verify=args.verify_supported)

    output_path = (root / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output)
    json_path = (root / args.json_output).resolve() if not Path(args.json_output).is_absolute() else Path(args.json_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown(contract), encoding="utf-8")
    json_path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        f"Generated repo execution contract for {repo_name}: "
        f"status={contract['status']} confidence={contract['confidence']}"
    )

    _ = args.enforce_supported
    return 0


if __name__ == "__main__":
    sys.exit(main())
