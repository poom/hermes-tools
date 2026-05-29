#!/usr/bin/env python3
"""Daily Codex/ChatGPT subscription token usage recorder.

Scans local Codex JSONL session logs for token accounting fields, writes an
idempotent daily CSV + latest JSON summary, and prints a compact daily report.
It deliberately does not read or emit conversation message contents.
"""
from __future__ import annotations

import csv
import json
import os
import re
import socket
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path.home()
CODEX_SESSIONS = HOME / ".codex" / "sessions"
OUT_DIR = HOME / ".hermes" / "usage"


def safe_machine_id() -> str:
    raw = os.environ.get("CODEX_USAGE_MACHINE_ID") or socket.gethostname() or "unknown-machine"
    raw = raw.split(".", 1)[0]
    # Friendly aliases keep reports readable and stable even if the OS hostname changes.
    aliases = {"Wynn-MBP": "Hermione"}
    raw = aliases.get(raw, raw)
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-_") or "unknown-machine"


MACHINE_ID = safe_machine_id()
CSV_PATH = OUT_DIR / f"codex_daily_usage_{MACHINE_ID}.csv"
JSON_PATH = OUT_DIR / f"codex_daily_usage_latest_{MACHINE_ID}.json"

USAGE_KEYS = [
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
]


def local_day(ts: str | None, fallback_path: Path) -> str:
    """Return YYYY-MM-DD from Codex timestamp, falling back to path folders."""
    if ts:
        # Codex timestamps are ISO UTC strings ending in Z. Use local timezone for
        # daily reporting so rows match the user's day.
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.astimezone().strftime("%Y-%m-%d")
        except Exception:
            pass
    parts = fallback_path.parts
    for i in range(len(parts) - 2):
        if parts[i].isdigit() and len(parts[i]) == 4 and parts[i + 1].isdigit() and parts[i + 2].isdigit():
            return f"{parts[i]}-{parts[i + 1]}-{parts[i + 2]}"
    return datetime.now().astimezone().strftime("%Y-%m-%d")


def parse_logs() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sessions: list[dict[str, Any]] = []
    rate_events: list[dict[str, Any]] = []
    if not CODEX_SESSIONS.exists():
        return sessions, rate_events

    for path in CODEX_SESSIONS.rglob("*.jsonl"):
        first_ts = None
        latest_ts = None
        max_usage: dict[str, int] | None = None
        model = "unknown"
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    ts = obj.get("timestamp")
                    if ts and not first_ts:
                        first_ts = ts
                    payload = obj.get("payload") or {}
                    if not isinstance(payload, dict):
                        continue
                    model = payload.get("model") or model

                    info = payload.get("info") or {}
                    usage = info.get("total_token_usage") if isinstance(info, dict) else None
                    if isinstance(usage, dict) and "total_tokens" in usage:
                        normalized = {k: int(usage.get(k) or 0) for k in USAGE_KEYS}
                        if max_usage is None or normalized["total_tokens"] > max_usage["total_tokens"]:
                            max_usage = normalized
                        latest_ts = ts or latest_ts

                    rate_limits = payload.get("rate_limits")
                    if isinstance(rate_limits, dict):
                        rate_events.append({
                            "timestamp": ts,
                            "session_file": str(path),
                            "rate_limits": rate_limits,
                        })
        except Exception:
            continue
        if max_usage:
            sessions.append({
                "machine": MACHINE_ID,
                "day": local_day(first_ts or latest_ts, path),
                "timestamp": latest_ts or first_ts,
                "model": model,
                "session_file": str(path),
                "usage": max_usage,
            })
    return sessions, rate_events


def aggregate(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_day: dict[str, Counter] = defaultdict(Counter)
    models: dict[str, Counter] = defaultdict(Counter)
    for s in sessions:
        day = s["day"]
        by_day[day]["sessions"] += 1
        by_day[day][f"model::{s['model']}"] += 1
        for k in USAGE_KEYS:
            by_day[day][k] += int(s["usage"].get(k) or 0)
    rows: list[dict[str, Any]] = []
    for day in sorted(by_day):
        c = by_day[day]
        model_counts = {
            k.split("::", 1)[1]: v for k, v in c.items() if isinstance(k, str) and k.startswith("model::")
        }
        rows.append({
            "machine": MACHINE_ID,
            "day": day,
            "sessions": int(c["sessions"]),
            "total_tokens": int(c["total_tokens"]),
            "input_tokens": int(c["input_tokens"]),
            "cached_input_tokens": int(c["cached_input_tokens"]),
            "output_tokens": int(c["output_tokens"]),
            "reasoning_output_tokens": int(c["reasoning_output_tokens"]),
            "models": json.dumps(model_counts, sort_keys=True),
        })
    return rows


def write_outputs(rows: list[dict[str, Any]], sessions: list[dict[str, Any]], rate_events: list[dict[str, Any]]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fields = [
        "machine",
        "day",
        "sessions",
        "total_tokens",
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
        "reasoning_output_tokens",
        "models",
    ]
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    latest_rate = None
    if rate_events:
        latest_rate = sorted(rate_events, key=lambda r: r.get("timestamp") or "")[-1]
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "machine": MACHINE_ID,
        "scope": "codex_cli_local_session_logs_only",
        "excludes": [
            "Hermes/OpenAI provider calls outside Codex CLI",
            "direct OpenAI API calls not made by Codex CLI",
            "ChatGPT web/mobile sessions",
            "Codex CLI sessions on other machines unless their logs are synced",
        ],
        "source": str(CODEX_SESSIONS),
        "csv_path": str(CSV_PATH),
        "days_recorded": len(rows),
        "sessions_with_usage": len(sessions),
        "latest_rate_limit_event": latest_rate,
        "daily": rows,
    }
    JSON_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def fmt(n: int) -> str:
    return f"{n:,}"


def main() -> int:
    sessions, rate_events = parse_logs()
    rows = aggregate(sessions)
    write_outputs(rows, sessions, rate_events)

    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    row = next((r for r in rows if r["day"] == today), None)
    if not row and rows:
        row = rows[-1]
        label = f"Latest recorded day ({row['day']})"
    elif row:
        label = f"Today ({today})"
    else:
        print(f"Codex CLI local daily usage record created, but no local usage logs found. CSV: {CSV_PATH}")
        return 0

    rate_line = ""
    if rate_events:
        latest = sorted(rate_events, key=lambda r: r.get("timestamp") or "")[-1]
        rl = latest.get("rate_limits") or {}
        primary = rl.get("primary") or {}
        secondary = rl.get("secondary") or {}
        parts = []
        if "used_percent" in primary:
            parts.append(f"5h {primary['used_percent']}%")
        if "used_percent" in secondary:
            parts.append(f"weekly {secondary['used_percent']}%")
        if rl.get("plan_type"):
            parts.append(f"plan {rl['plan_type']}")
        if parts:
            rate_line = "\nLatest stale rate-limit snapshot: " + ", ".join(parts) + f" @ {latest.get('timestamp')}"

    print(
        f"Codex CLI local token usage recorded.\n"
        f"Machine: {MACHINE_ID}\n"
        f"{label}: {fmt(row['total_tokens'])} total "
        f"({fmt(row['input_tokens'])} input, {fmt(row['cached_input_tokens'])} cached input, "
        f"{fmt(row['output_tokens'])} output, {fmt(row['reasoning_output_tokens'])} reasoning), "
        f"{row['sessions']} sessions.\n"
        f"CSV: {CSV_PATH}\nJSON: {JSON_PATH}"
        f"{rate_line}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
