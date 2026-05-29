#!/usr/bin/env python3
"""Find or create today's Discord reminder thread.

Prints compact JSON for scheduled Hermes jobs. Does not print tokens.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

API_BASE = "https://discord.com/api/v10"
DEFAULT_CHANNEL_ID = os.getenv("DISCORD_REMINDER_CHANNEL_ID", "")
DEFAULT_TZ = os.getenv("HERMES_TOOLS_TIMEZONE", "Asia/Bangkok")


from hermes_tools_common import hermes_home, load_hermes_dotenv


def request(method: str, path: str, token: str, *, params: dict[str, str] | None = None, body: dict[str, Any] | None = None, timeout: int = 20) -> Any:
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
            "User-Agent": "Hermes-Agent daily-reminder-thread",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 204:
                return None
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")[:1200]
        raise RuntimeError(f"Discord API {method} {path} failed with HTTP {e.code}: {raw}") from e


def thread_summary(thread: dict[str, Any], source: str, channel_id: str) -> dict[str, Any]:
    tid = str(thread.get("id"))
    name = thread.get("name")
    return {
        "ok": True,
        "source": source,
        "channel_id": channel_id,
        "thread_id": tid,
        "thread_name": name,
        "discord_target": f"discord:{channel_id}:{tid}",
        "thread_metadata": thread.get("thread_metadata", {}),
    }


def find_thread_in_list(threads: list[dict[str, Any]], *, channel_id: str, name: str) -> dict[str, Any] | None:
    for t in threads:
        if str(t.get("parent_id")) == str(channel_id) and t.get("name") == name:
            return t
    return None


def find_or_create(channel_id: str, name: str, token: str, auto_archive_duration: int = 1440) -> dict[str, Any]:
    channel = request("GET", f"/channels/{channel_id}", token)
    guild_id = channel.get("guild_id")
    if not guild_id:
        raise RuntimeError(f"Channel {channel_id} is not a guild channel or is inaccessible")

    active = request("GET", f"/guilds/{guild_id}/threads/active", token)
    thread = find_thread_in_list(active.get("threads", []), channel_id=channel_id, name=name)
    if thread:
        # If someone archived it between active listing and send time, unarchive defensively.
        meta = thread.get("thread_metadata") or {}
        if meta.get("archived"):
            thread = request("PATCH", f"/channels/{thread['id']}", token, body={"archived": False, "locked": False})
        return thread_summary(thread, "existing_active", channel_id)

    # Search recent public archived threads too, so we do not create duplicates if the daily
    # thread auto-archived before a later reminder run.
    archived = request("GET", f"/channels/{channel_id}/threads/archived/public", token, params={"limit": "100"})
    thread = find_thread_in_list(archived.get("threads", []), channel_id=channel_id, name=name)
    if thread:
        thread = request("PATCH", f"/channels/{thread['id']}", token, body={"archived": False, "locked": False, "name": name})
        return thread_summary(thread, "existing_archived_unarchived", channel_id)

    thread = request(
        "POST",
        f"/channels/{channel_id}/threads",
        token,
        body={
            "name": name,
            "type": 11,  # PUBLIC_THREAD
            "auto_archive_duration": auto_archive_duration,
        },
    )
    return thread_summary(thread, "created", channel_id)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel-id", default=os.getenv("DISCORD_REMINDER_CHANNEL_ID", DEFAULT_CHANNEL_ID))
    parser.add_argument("--timezone", default=DEFAULT_TZ)
    parser.add_argument("--date", default="", help="YYYY-MM-DD; defaults to today in --timezone")
    parser.add_argument("--prefix", default="Reminder")
    parser.add_argument("--auto-archive-duration", type=int, default=1440)
    args = parser.parse_args()

    load_hermes_dotenv(hermes_home() / ".env")
    if not args.channel_id:
        print("ERROR: set --channel-id or DISCORD_REMINDER_CHANNEL_ID", file=sys.stderr)
        return 2
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        print(json.dumps({"ok": False, "error": "DISCORD_BOT_TOKEN is not configured"}))
        return 2

    date_str = args.date or datetime.now(ZoneInfo(args.timezone)).strftime("%Y-%m-%d")
    name = f"{args.prefix} {date_str}"
    try:
        result = find_or_create(args.channel_id, name, token, args.auto_archive_duration)
        result.update({"date": date_str, "timezone": args.timezone})
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "date": date_str, "thread_name": name, "channel_id": args.channel_id, "error": str(e)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
