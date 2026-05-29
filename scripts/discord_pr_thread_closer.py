#!/usr/bin/env python3
"""Archive Discord PR review threads when their GitHub PR is closed or merged.

Default runtime is quiet: prints only when it archives a thread or hits a hard error.
Safe for Hermes cron no_agent jobs.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_tools_common import hermes_home, load_hermes_dotenv, portable_env

API_BASE = "https://discord.com/api/v10"
DEFAULT_PARENT_CHANNEL_ID = os.getenv("DISCORD_PR_THREAD_PARENT_CHANNEL_ID", "")
ENV = portable_env()
STATE_PATH = hermes_home() / "state" / "discord_pr_thread_closer_state.json"

# Match canonical GitHub pull request URLs in thread messages.
PR_URL_RE = re.compile(r"https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/pull/(\d+)", re.I)
# Match thread names such as "owner/repo #123 - Reviewing" or "owner/repo#123".
PR_NAME_RE = re.compile(r"\b([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\s*#\s*(\d+)\b")


@dataclass(frozen=True)
class PRRef:
    owner: str
    repo: str
    number: int

    @property
    def url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}/pull/{self.number}"

    @property
    def api_path(self) -> str:
        return f"repos/{self.owner}/{self.repo}/pulls/{self.number}"


def load_dotenv(path: Path) -> None:
    try:
        text = path.read_text(errors="ignore")
    except Exception:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in os.environ or key in ENV:
            continue
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value
        ENV[key] = value


def discord_request(method: str, path: str, token: str, *, params: dict[str, str] | None = None, body: dict[str, Any] | None = None, timeout: int = 30) -> Any:
    url = f"{API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "Hermes-Agent discord-pr-thread-closer",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 204:
                return None
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"Discord API {method} {path} failed with HTTP {e.code}: {raw}") from e


def run(cmd: list[str], timeout: int = 45) -> tuple[int | str, str, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=ENV)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        return "timeout", e.stdout or "", (e.stderr or "") + f"\nTIMEOUT after {timeout}s"
    except Exception as e:
        return "error", "", repr(e)


def list_target_active_threads(parent_channel_id: str, token: str) -> tuple[str, list[dict[str, Any]]]:
    channel = discord_request("GET", f"/channels/{parent_channel_id}", token)
    guild_id = str(channel.get("guild_id") or "")
    if not guild_id:
        raise RuntimeError(f"Channel {parent_channel_id} is not an accessible guild channel")
    active = discord_request("GET", f"/guilds/{guild_id}/threads/active", token)
    threads = []
    for thread in active.get("threads", []):
        if str(thread.get("parent_id")) != str(parent_channel_id):
            continue
        meta = thread.get("thread_metadata") or {}
        if meta.get("archived"):
            continue
        threads.append(thread)
    return guild_id, threads


def get_thread_messages(thread_id: str, token: str, limit: int = 50) -> list[dict[str, Any]]:
    messages = discord_request("GET", f"/channels/{thread_id}/messages", token, params={"limit": str(limit)})
    return messages if isinstance(messages, list) else []


def extract_pr_ref(thread: dict[str, Any], messages: list[dict[str, Any]]) -> PRRef | None:
    # Prefer explicit URLs from messages because thread names often omit the owner.
    haystacks: list[str] = []
    for msg in messages:
        haystacks.append(str(msg.get("content") or ""))
        for embed in msg.get("embeds") or []:
            haystacks.append(str(embed.get("url") or ""))
            haystacks.append(str(embed.get("title") or ""))
            haystacks.append(str(embed.get("description") or ""))
    for text in haystacks:
        m = PR_URL_RE.search(text)
        if m:
            return PRRef(m.group(1), m.group(2), int(m.group(3)))

    name = str(thread.get("name") or "")
    m = PR_NAME_RE.search(name)
    if m:
        owner, repo = m.group(1).split("/", 1)
        return PRRef(owner, repo, int(m.group(2)))
    return None


def get_pr_status(ref: PRRef) -> dict[str, Any]:
    code, out, err = run(["gh", "api", ref.api_path, "--jq", "{state:.state, merged:.merged, merged_at:.merged_at, closed_at:.closed_at, title:.title, html_url:.html_url}"], timeout=60)
    if code != 0:
        raise RuntimeError(f"gh api {ref.api_path} failed ({code}): {(err or out).strip()[:1000]}")
    try:
        data = json.loads(out)
    except Exception as e:
        raise RuntimeError(f"Could not parse gh output for {ref.url}: {e}") from e
    return data


def post_thread_notice(thread_id: str, token: str, pr: PRRef, status: dict[str, Any], dry_run: bool) -> None:
    state = str(status.get("state") or "").lower()
    merged = bool(status.get("merged"))
    label = "merged" if merged else state or "closed"
    when = status.get("merged_at") if merged else status.get("closed_at")
    suffix = f" at {when}" if when else ""
    content = f"PR {pr.url} is {label}{suffix}; archiving this review thread."
    if not dry_run:
        discord_request("POST", f"/channels/{thread_id}/messages", token, body={"content": content})


def archive_thread(thread_id: str, token: str, dry_run: bool) -> None:
    if not dry_run:
        discord_request("PATCH", f"/channels/{thread_id}", token, body={"archived": True})


def load_state() -> dict[str, Any]:
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {}


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel-id", default=os.getenv("DISCORD_PR_THREAD_PARENT_CHANNEL_ID", DEFAULT_PARENT_CHANNEL_ID))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--json", action="store_true", help="print full summary even when nothing was archived")
    args = parser.parse_args()

    load_hermes_dotenv(hermes_home() / ".env")
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        print("ERROR: DISCORD_BOT_TOKEN is not configured")
        return 2
    if not args.channel_id:
        print("ERROR: set --channel-id or DISCORD_PR_THREAD_PARENT_CHANNEL_ID")
        return 2

    summary: dict[str, Any] = {
        "ok": True,
        "dry_run": args.dry_run,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "parent_channel_id": str(args.channel_id),
        "checked_threads": 0,
        "closed_threads": [],
        "skipped_threads": [],
        "errors": [],
    }

    try:
        _guild_id, threads = list_target_active_threads(str(args.channel_id), token)
        summary["checked_threads"] = len(threads)
    except Exception as e:
        print(f"ERROR: {e}")
        return 1

    state = load_state()
    state.setdefault("last_runs", [])

    for thread in threads:
        thread_id = str(thread.get("id"))
        thread_name = str(thread.get("name") or "")
        try:
            messages = get_thread_messages(thread_id, token)
            pr = extract_pr_ref(thread, messages)
            if not pr:
                # Most active threads in the channel may not be PR review threads; stay quiet by default.
                if args.verbose:
                    summary["skipped_threads"].append({"thread_id": thread_id, "thread_name": thread_name, "reason": "no GitHub PR URL or owner/repo #number in thread"})
                continue
            status = get_pr_status(pr)
            is_closed_or_merged = str(status.get("state") or "").lower() == "closed" or bool(status.get("merged"))
            if not is_closed_or_merged:
                if args.verbose:
                    summary["skipped_threads"].append({"thread_id": thread_id, "thread_name": thread_name, "pr": pr.url, "state": status.get("state"), "merged": status.get("merged")})
                continue
            post_thread_notice(thread_id, token, pr, status, args.dry_run)
            archive_thread(thread_id, token, args.dry_run)
            summary["closed_threads"].append({
                "thread_id": thread_id,
                "thread_name": thread_name,
                "pr": pr.url,
                "state": status.get("state"),
                "merged": status.get("merged"),
                "closed_at": status.get("closed_at"),
                "merged_at": status.get("merged_at"),
            })
        except Exception as e:
            summary["errors"].append({"thread_id": thread_id, "thread_name": thread_name, "error": str(e)[:1000]})

    state["last_runs"] = (state.get("last_runs") or [])[-19:] + [summary]
    save_state(state)

    # Cron no_agent mode: empty stdout means silent when no action is needed.
    # When threads are archived, stdout is delivered verbatim to Discord, so keep it
    # as a compact one-message human summary instead of JSON.
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    elif summary["closed_threads"]:
        suffix = "would close" if args.dry_run else "closed"
        print("\n".join(f"{item['thread_name']} - {suffix}" for item in summary["closed_threads"]))
        if summary["errors"] and (args.verbose or args.dry_run):
            print("\n".join(f"ERROR: {item['thread_name']}: {item['error']}" for item in summary["errors"]))
    elif summary["errors"]:
        print("\n".join(f"ERROR: {item['thread_name']}: {item['error']}" for item in summary["errors"]))
    elif args.dry_run or args.verbose:
        print("No PR review threads to close.")
    return 1 if summary["errors"] and not summary["closed_threads"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
