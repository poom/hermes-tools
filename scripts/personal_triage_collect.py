#!/usr/bin/env python3
"""Collect unread email + Google Chat triage data for a Hermes cron job."""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from typing import Any

from hermes_tools_common import hermes_scripts_dir, portable_env, which_executable

ENV = portable_env()
ACCOUNTS = [a.strip() for a in os.getenv("GOG_ACCOUNTS", "work,personal").split(",") if a.strip()]
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
    """Strip prompt-scanner triggers from untrusted email/chat text."""
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


def run(cmd: list[str], timeout: int) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=ENV)
        return {
            "cmd": " ".join(cmd),
            "exit": p.returncode,
            "stdout": p.stdout,
            "stderr": p.stderr,
        }
    except subprocess.TimeoutExpired as e:
        return {
            "cmd": " ".join(cmd),
            "exit": "timeout",
            "stdout": e.stdout or "",
            "stderr": (e.stderr or "") + f"\nTIMEOUT after {timeout}s",
        }
    except Exception as e:
        return {"cmd": " ".join(cmd), "exit": "error", "stdout": "", "stderr": repr(e)}


def parse_json(stdout: str) -> Any:
    if not stdout.strip():
        return []
    try:
        return json.loads(stdout)
    except Exception:
        return {"_parse_error": True, "raw": stdout[:4000]}


def collect_email() -> list[dict[str, Any]]:
    results = []
    query = "is:unread newer_than:14d"
    for account in ACCOUNTS:
        cmd = [
            "gog",
            "--account",
            account,
            "gmail",
            "messages",
            "search",
            query,
            "--max",
            "8",
            "--json",
            "--results-only",
            "--include-body",
            "--no-input",
        ]
        r = run(cmd, timeout=90)
        messages = parse_json(r["stdout"])
        if isinstance(messages, list):
            compact = []
            for m in messages[:8]:
                compact.append(
                    {
                        "id": m.get("id"),
                        "threadId": m.get("threadId"),
                        "date": m.get("date"),
                        "from": m.get("from"),
                        "subject": m.get("subject"),
                        "labels": m.get("labels", []),
                        "body": truncate(m.get("body", ""), 400),
                    }
                )
            messages = compact
        results.append(
            {
                "account": account,
                "query": query,
                "exit": r["exit"],
                "stderr": truncate(r["stderr"], 1000),
                "messages": messages,
            }
        )
    return results


def compact_chat_sections(sections: Any) -> Any:
    if not isinstance(sections, list):
        return sections
    compact = []
    for sec in sections[:18]:
        items = sec.get("items", []) if isinstance(sec, dict) else []
        compact.append(
            {
                "group": sec.get("group", {}) if isinstance(sec, dict) else {},
                "unread_count": len(items),
                "latest_items": truncate(items[-2:], 350),
            }
        )
    return {"total_sections": len(sections), "shown_sections": compact}


def collect_chat() -> dict[str, Any]:
    poke = which_executable("poke", "POKE_CLI") or "poke"
    r = run([poke, "chat", "-f", "json", "--timeout", "180"], timeout=210)
    return {
        "exit": r["exit"],
        "stderr": truncate(r["stderr"], 2000),
        "sections": compact_chat_sections(parse_json(r["stdout"])),
    }


def ensure_daily_discord_thread() -> dict[str, Any]:
    r = run([str(hermes_scripts_dir() / "discord_daily_reminder_thread.py")], timeout=45)
    parsed = parse_json(r["stdout"])
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


def main() -> None:
    payload = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "timezone": os.getenv("HERMES_TOOLS_TIMEZONE", "Asia/Bangkok"),
        "discord_daily_thread": ensure_daily_discord_thread(),
        "email": collect_email(),
        "google_chat": collect_chat(),
    }
    payload = sanitize(payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
