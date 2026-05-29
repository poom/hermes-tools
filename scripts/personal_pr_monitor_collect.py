#!/usr/bin/env python3
"""Collect open PR status for Poom's authored GitHub PRs without mutating state."""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_tools_common import hermes_home, hermes_scripts_dir, portable_env

ENV = portable_env()
STATE_PATH = hermes_home() / "state" / "personal_pr_monitor_state.json"
INVISIBLE_CHARS = "\u200b\u200c\u200d\u2060\ufeff\u202a\u202b\u202c\u202d\u202e"
THREATLIKE_PATTERNS = [
    (re.compile(r"ignore\s+(?:\w+\s+)*(?:previous|all|above|prior)\s+(?:\w+\s+)*instructions", re.I), "[sanitized prompt-injection phrase]"),
    (re.compile(r"do\s+not\s+tell\s+the\s+user", re.I), "[sanitized deception phrase]"),
    (re.compile(r"system\s+prompt\s+override", re.I), "[sanitized system-prompt phrase]"),
    (re.compile(r"disregard\s+(your|all|any)\s+(instructions|rules|guidelines)", re.I), "[sanitized prompt-injection phrase]"),
    (re.compile(r"(curl|wget)\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)\w*", re.I), "[sanitized command-like secret-exfiltration text]"),
    (re.compile(r"cat\s+[^\n]*(\.env|credentials|\.netrc|\.pgpass)", re.I), "[sanitized command-like secret-read text]"),
    (re.compile(r"authorized_keys", re.I), "authorized keys"),
    (re.compile(r"/etc/sudoers|visudo", re.I), "[sanitized sudoers text]"),
    (re.compile(r"rm\s+-rf\s+/", re.I), "[sanitized destructive command text]"),
]


def sanitize(value: Any) -> Any:
    """Strip prompt-scanner triggers from untrusted PR/comment text."""
    if isinstance(value, str):
        cleaned = value.translate({ord(c): None for c in INVISIBLE_CHARS})
        for pattern, replacement in THREATLIKE_PATTERNS:
            cleaned = pattern.sub(replacement, cleaned)
        return cleaned
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, dict):
        return {k: sanitize(v) for k, v in value.items()}
    return value


def truncate(value: Any, limit: int = 1200) -> Any:
    if isinstance(value, str):
        value = sanitize(value)
        return value if len(value) <= limit else value[:limit] + "…[truncated]"
    if isinstance(value, list):
        return [truncate(v, limit) for v in value]
    if isinstance(value, dict):
        return {k: truncate(v, limit) for k, v in value.items()}
    return value


def run(cmd: list[str], timeout: int = 60) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=ENV)
        return {"exit": p.returncode, "stdout": p.stdout, "stderr": p.stderr, "cmd": " ".join(cmd)}
    except subprocess.TimeoutExpired as e:
        return {"exit": "timeout", "stdout": e.stdout or "", "stderr": (e.stderr or "") + f"\nTIMEOUT after {timeout}s", "cmd": " ".join(cmd)}
    except Exception as e:
        return {"exit": "error", "stdout": "", "stderr": repr(e), "cmd": " ".join(cmd)}


def json_or(value: str, default: Any) -> Any:
    try:
        return json.loads(value) if value.strip() else default
    except Exception:
        return default


def load_state() -> dict[str, Any]:
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {"prs": {}}


def simplify_check(c: dict[str, Any]) -> dict[str, Any]:
    typ = c.get("__typename")
    if typ == "CheckRun":
        return {
            "type": "check",
            "name": c.get("name"),
            "workflow": c.get("workflowName"),
            "status": c.get("status"),
            "conclusion": c.get("conclusion"),
            "detailsUrl": c.get("detailsUrl"),
        }
    if typ == "StatusContext":
        return {
            "type": "status",
            "name": c.get("context"),
            "state": c.get("state"),
            "targetUrl": c.get("targetUrl"),
        }
    return c


def latest_timestamp(items: list[dict[str, Any]]) -> str | None:
    vals = []
    for item in items:
        for key in ("createdAt", "submittedAt", "updatedAt"):
            if item.get(key):
                vals.append(item[key])
    return max(vals) if vals else None


def ensure_daily_discord_thread() -> dict[str, Any]:
    r = run([str(hermes_scripts_dir() / "discord_daily_reminder_thread.py")], timeout=45)
    parsed = json_or(r["stdout"], None)
    if isinstance(parsed, dict):
        parsed["helper_exit"] = r["exit"]
        parsed["helper_stderr"] = truncate(r["stderr"], 1000)
        return parsed
    return {
        "ok": False,
        "helper_exit": r["exit"],
        "helper_stdout": truncate(r["stdout"], 1000),
        "helper_stderr": truncate(r["stderr"], 1000),
    }


def collect() -> dict[str, Any]:
    state = load_state()
    search = run([
        "gh", "search", "prs", "--author=@me", "--state=open", "--limit", "100",
        "--json", "repository,number,title,url,updatedAt,isDraft,commentsCount,labels"
    ], timeout=80)
    prs = json_or(search["stdout"], []) if search["exit"] == 0 else []
    detailed = []
    for pr in prs:
        url = pr.get("url")
        if not url:
            continue
        view = run([
            "gh", "pr", "view", url,
            "--json", "number,title,url,state,isDraft,author,baseRefName,headRefName,headRepository,headRepositoryOwner,reviewDecision,latestReviews,comments,mergeStateStatus,statusCheckRollup,updatedAt"
        ], timeout=100)
        data = json_or(view["stdout"], {"_error": view["stderr"], "url": url})
        key = url
        prev = state.get("prs", {}).get(key, {})
        comments = data.get("comments", []) if isinstance(data, dict) else []
        reviews = data.get("latestReviews", []) if isinstance(data, dict) else []
        # Keep the latest records, with bodies truncated. Exclude very noisy self-authored comments from new_items.
        comments_sorted = sorted(comments, key=lambda x: x.get("createdAt", ""))[-2:]
        reviews_sorted = sorted(reviews, key=lambda x: x.get("submittedAt", ""))[-2:]
        last_seen = prev.get("last_seen_activity_at")
        new_comments = []
        new_reviews = []
        if last_seen:
            new_comments = [c for c in comments if c.get("createdAt", "") > last_seen and c.get("author", {}).get("login") != "poom"]
            new_reviews = [r for r in reviews if r.get("submittedAt", "") > last_seen and r.get("author", {}).get("login") != "poom"]
        checks = [simplify_check(c) for c in (data.get("statusCheckRollup") or [])] if isinstance(data, dict) else []
        failing_checks = [c for c in checks if (c.get("conclusion") and c.get("conclusion") not in ("SUCCESS", "SKIPPED", "NEUTRAL")) or c.get("state") in ("FAILURE", "ERROR")]
        pending_checks = [c for c in checks if c.get("status") not in (None, "COMPLETED") or c.get("state") == "PENDING"]
        activity_items = comments + reviews
        detailed.append({
            "url": url,
            "repo": pr.get("repository", {}).get("nameWithOwner") or data.get("headRepository", {}).get("nameWithOwner"),
            "number": pr.get("number") or data.get("number"),
            "title": pr.get("title") or data.get("title"),
            "isDraft": data.get("isDraft", pr.get("isDraft")),
            "updatedAt": data.get("updatedAt", pr.get("updatedAt")),
            "baseRefName": data.get("baseRefName"),
            "headRefName": data.get("headRefName"),
            "headRepositoryOwner": (data.get("headRepositoryOwner") or {}).get("login"),
            "reviewDecision": data.get("reviewDecision"),
            "mergeStateStatus": data.get("mergeStateStatus"),
            "previous_last_seen_activity_at": prev.get("last_seen_activity_at"),
            "latest_activity_at": latest_timestamp(activity_items) or data.get("updatedAt"),
            "new_comments_since_last_seen": truncate(new_comments[-2:], 450),
            "new_reviews_since_last_seen": truncate(new_reviews[-2:], 600),
            "latest_comments": truncate(comments_sorted, 350),
            "latest_reviews": truncate(reviews_sorted, 500),
            "failing_checks": truncate(failing_checks[:4], 400),
            "pending_checks": truncate(pending_checks[:4], 400),
            "view_error": None if view["exit"] == 0 else truncate(view["stderr"], 1000),
        })
    return {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "timezone": os.getenv("HERMES_TOOLS_TIMEZONE", "Asia/Bangkok"),
        "discord_daily_thread": ensure_daily_discord_thread(),
        "state_path": str(STATE_PATH),
        "previous_state": state,
        "search_exit": search["exit"],
        "search_stderr": truncate(search["stderr"], 2000),
        "open_authored_prs": detailed,
    }


if __name__ == "__main__":
    print(json.dumps(sanitize(collect()), ensure_ascii=False, indent=2))
