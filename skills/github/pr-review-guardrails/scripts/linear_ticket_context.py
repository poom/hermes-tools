#!/usr/bin/env python3
"""Fetch Linear issue context via the linear CLI without curl/piped interpreters.

This helper is intentionally a thin wrapper around `linear issue view --json` so PR
review sessions can gather linked-ticket acceptance criteria without triggering
Hermes terminal approval prompts caused by ad-hoc curl/Python pipelines.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shlex
import subprocess
import sys
from typing import Any


def load_dotenv() -> None:
    """Load ~/.hermes/.env-style variables if they are not already present."""
    hermes_home = pathlib.Path(os.environ.get("HERMES_HOME", pathlib.Path.home() / ".hermes"))
    env_path = hermes_home / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        try:
            parsed = shlex.split(value, posix=True)
            os.environ[key] = parsed[0] if parsed else ""
        except ValueError:
            os.environ[key] = value.strip().strip('"').strip("'")


def run_linear(issue_id: str, workspace: str | None) -> dict[str, Any]:
    cmd = ["linear"]
    if workspace:
        cmd.extend(["--workspace", workspace])
    cmd.extend(["issue", "view", issue_id, "--json", "--no-pager", "--no-download"])
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        sys.stderr.write(result.stderr or result.stdout)
        raise SystemExit(result.returncode)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"linear returned non-JSON output for {issue_id}: {exc}\n")
        sys.stderr.write(result.stdout[:1000])
        raise SystemExit(1)


def text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def render_markdown(issue: dict[str, Any]) -> str:
    state = issue.get("state") or {}
    assignee = issue.get("assignee") or {}
    labels = issue.get("labels") or []
    comments = issue.get("comments") or []
    attachments = issue.get("attachments") or []

    lines: list[str] = []
    lines.append(f"# {text(issue.get('identifier'))}: {text(issue.get('title'))}")
    if issue.get("url"):
        lines.append(f"URL: {issue['url']}")
    if state:
        lines.append(f"State: {text(state.get('name'))}")
    if assignee:
        lines.append(f"Assignee: {text(assignee.get('name') or assignee.get('displayName'))}")
    if labels:
        label_names = [text(l.get("name") if isinstance(l, dict) else l) for l in labels]
        lines.append("Labels: " + ", ".join([l for l in label_names if l]))
    if issue.get("branchName"):
        lines.append(f"Branch: {issue['branchName']}")

    description = text(issue.get("description"), "").strip()
    if description:
        lines.append("\n## Description\n")
        lines.append(description)

    if comments:
        lines.append("\n## Comments\n")
        for c in comments:
            if not isinstance(c, dict):
                continue
            user = (c.get("user") or {}).get("name") if isinstance(c.get("user"), dict) else ""
            created = text(c.get("createdAt"), "")
            body = text(c.get("body"), "").strip()
            lines.append(f"### {user or 'comment'} {created}".rstrip())
            lines.append(body)

    github_attachments = []
    for a in attachments:
        if isinstance(a, dict) and a.get("sourceType") == "github":
            github_attachments.append(a)
    if github_attachments:
        lines.append("\n## GitHub attachments\n")
        for a in github_attachments:
            lines.append(f"- {text(a.get('title'))}: {text(a.get('url'))}")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Linear issue context via linear CLI")
    parser.add_argument("issue_ids", nargs="+", help="Linear issue identifiers, e.g. DEV-2641")
    parser.add_argument("--workspace", default=None, help="Optional Linear workspace slug")
    parser.add_argument("--json", action="store_true", help="Emit raw JSON array instead of Markdown")
    args = parser.parse_args()

    load_dotenv()
    issues = [run_linear(issue_id, args.workspace) for issue_id in args.issue_ids]
    if args.json:
        print(json.dumps(issues if len(issues) > 1 else issues[0], ensure_ascii=False, indent=2))
        return
    for idx, issue in enumerate(issues):
        if idx:
            print("\n---\n")
        print(render_markdown(issue), end="")


if __name__ == "__main__":
    main()
