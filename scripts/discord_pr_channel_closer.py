#!/usr/bin/env python3
"""Delete Discord review-prs text channels when their GitHub PR is closed/merged.

Default runtime is quiet: prints only when it deletes a channel or hits a hard error.
Safe for Hermes cron no_agent jobs. Destructive action is narrowly scoped to text
channels under the review-prs category and only after extracting a GitHub PR URL
from channel metadata/messages and verifying the PR is closed/merged via gh.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_tools_common import hermes_home, load_hermes_dotenv, portable_env

API_BASE = "https://discord.com/api/v10"
DEFAULT_GUILD_ID = os.getenv("DISCORD_PR_REVIEW_GUILD_ID") or os.getenv("DISCORD_GUILD_ID", "")
DEFAULT_CATEGORY_NAME = "review-prs"
ENV = portable_env()
STATE_PATH = hermes_home() / "state" / "discord_pr_channel_closer_state.json"

PR_URL_RE = re.compile(r"https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/pull/(\d+)", re.I)


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


def discord_request(
    method: str,
    path: str,
    token: str,
    *,
    params: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = 30,
) -> Any:
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
            "User-Agent": "Hermes-Agent discord-pr-channel-closer",
        },
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 204:
                    return None
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")[:1000]
            if e.code == 429 and attempt < 3:
                retry_after = 1.0
                try:
                    payload = json.loads(raw or "{}")
                    retry_after = float(payload.get("retry_after") or retry_after)
                except Exception:
                    pass
                time.sleep(min(max(retry_after, 1.0), 10.0))
                continue
            raise RuntimeError(f"Discord API {method} {path} failed with HTTP {e.code}: {raw}") from e


def run(cmd: list[str], timeout: int = 45) -> tuple[int | str, str, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=ENV)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        return "timeout", e.stdout or "", (e.stderr or "") + f"\nTIMEOUT after {timeout}s"
    except Exception as e:
        return "error", "", repr(e)


def list_review_channels(guild_id: str, token: str, category_id: str | None, category_name: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    channels = discord_request("GET", f"/guilds/{guild_id}/channels", token)
    if not isinstance(channels, list):
        raise RuntimeError(f"Could not list guild channels for guild {guild_id}")

    category: dict[str, Any] | None = None
    if category_id:
        for ch in channels:
            if str(ch.get("id")) == str(category_id):
                category = ch
                break
        if not category:
            raise RuntimeError(f"Category id {category_id} not found in guild {guild_id}")
    else:
        matches = [ch for ch in channels if int(ch.get("type", -1)) == 4 and str(ch.get("name") or "").lower() == category_name.lower()]
        if not matches:
            raise RuntimeError(f"No Discord category named {category_name!r} found in guild {guild_id}")
        if len(matches) > 1:
            raise RuntimeError(f"Multiple Discord categories named {category_name!r}; set DISCORD_PR_REVIEW_CATEGORY_ID")
        category = matches[0]

    category_id = str(category.get("id"))
    # Type 0 is GUILD_TEXT. Exclude threads/categories/voice/etc.
    text_channels = [
        ch for ch in channels
        if str(ch.get("parent_id")) == category_id and int(ch.get("type", -1)) == 0
    ]
    text_channels.sort(key=lambda ch: str(ch.get("name") or ""))
    return category, text_channels


def message_haystacks(message: dict[str, Any]) -> list[str]:
    haystacks = [str(message.get("content") or "")]
    for embed in message.get("embeds") or []:
        haystacks.append(str(embed.get("url") or ""))
        haystacks.append(str(embed.get("title") or ""))
        haystacks.append(str(embed.get("description") or ""))
        for field in embed.get("fields") or []:
            haystacks.append(str(field.get("name") or ""))
            haystacks.append(str(field.get("value") or ""))
    for attachment in message.get("attachments") or []:
        haystacks.append(str(attachment.get("url") or ""))
        haystacks.append(str(attachment.get("filename") or ""))
    return haystacks


def extract_pr_from_texts(texts: list[str]) -> PRRef | None:
    for text in texts:
        m = PR_URL_RE.search(text)
        if m:
            return PRRef(m.group(1), m.group(2), int(m.group(3)))
    return None


def extract_pr_ref(channel: dict[str, Any], token: str, max_messages: int = 500) -> PRRef | None:
    # Prefer metadata before paginating history.
    texts = [
        str(channel.get("topic") or ""),
        str(channel.get("name") or ""),
    ]
    pr = extract_pr_from_texts(texts)
    if pr:
        return pr

    before: str | None = None
    scanned = 0
    while scanned < max_messages:
        limit = min(100, max_messages - scanned)
        params = {"limit": str(limit)}
        if before:
            params["before"] = before
        messages = discord_request("GET", f"/channels/{channel['id']}/messages", token, params=params)
        if not isinstance(messages, list) or not messages:
            return None
        for msg in messages:
            pr = extract_pr_from_texts(message_haystacks(msg))
            if pr:
                return pr
        scanned += len(messages)
        before = str(messages[-1].get("id"))
        if len(messages) < limit:
            return None
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


def delete_channel(channel_id: str, token: str, dry_run: bool) -> None:
    if not dry_run:
        discord_request("DELETE", f"/channels/{channel_id}", token)


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
    parser.add_argument("--guild-id", default=os.getenv("DISCORD_PR_REVIEW_GUILD_ID") or os.getenv("DISCORD_GUILD_ID") or DEFAULT_GUILD_ID)
    parser.add_argument("--category-id", default=os.getenv("DISCORD_PR_REVIEW_CATEGORY_ID", ""))
    parser.add_argument("--category-name", default=os.getenv("DISCORD_PR_REVIEW_CATEGORY_NAME", DEFAULT_CATEGORY_NAME))
    parser.add_argument("--max-messages", type=int, default=int(os.getenv("DISCORD_PR_REVIEW_MAX_MESSAGES", "500")))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--json", action="store_true", help="print full summary even when no channel was deleted")
    args = parser.parse_args()

    load_hermes_dotenv(hermes_home() / ".env")
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        print("ERROR: DISCORD_BOT_TOKEN is not configured")
        return 2
    if not args.guild_id:
        print("ERROR: set --guild-id, DISCORD_PR_REVIEW_GUILD_ID, or DISCORD_GUILD_ID")
        return 2

    summary: dict[str, Any] = {
        "ok": True,
        "dry_run": args.dry_run,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "guild_id": str(args.guild_id),
        "category_id": str(args.category_id or ""),
        "category_name": str(args.category_name),
        "checked_channels": 0,
        "deleted_channels": [],
        "skipped_channels": [],
        "errors": [],
    }

    try:
        category, channels = list_review_channels(str(args.guild_id), token, str(args.category_id or "") or None, str(args.category_name))
        summary["category_id"] = str(category.get("id"))
        summary["category_name"] = str(category.get("name") or args.category_name)
        summary["checked_channels"] = len(channels)
    except Exception as e:
        print(f"ERROR: {e}")
        return 1

    state = load_state()
    state.setdefault("last_runs", [])

    for channel in channels:
        channel_id = str(channel.get("id"))
        channel_name = str(channel.get("name") or "")
        try:
            pr = extract_pr_ref(channel, token, max_messages=args.max_messages)
            if not pr:
                if args.verbose:
                    summary["skipped_channels"].append({"channel_id": channel_id, "channel_name": channel_name, "reason": "no GitHub PR URL in topic/name/recent messages"})
                continue
            status = get_pr_status(pr)
            is_closed_or_merged = str(status.get("state") or "").lower() == "closed" or bool(status.get("merged"))
            if not is_closed_or_merged:
                if args.verbose:
                    summary["skipped_channels"].append({"channel_id": channel_id, "channel_name": channel_name, "pr": pr.url, "state": status.get("state"), "merged": status.get("merged")})
                continue
            delete_channel(channel_id, token, args.dry_run)
            summary["deleted_channels"].append({
                "channel_id": channel_id,
                "channel_name": channel_name,
                "pr": pr.url,
                "state": status.get("state"),
                "merged": status.get("merged"),
                "closed_at": status.get("closed_at"),
                "merged_at": status.get("merged_at"),
            })
        except Exception as e:
            summary["errors"].append({"channel_id": channel_id, "channel_name": channel_name, "error": str(e)[:1000]})

    state["last_runs"] = (state.get("last_runs") or [])[-19:] + [summary]
    save_state(state)

    # Cron no_agent mode: empty stdout means silent when no action is needed.
    # When channels are deleted, stdout is delivered verbatim to Discord, so keep it
    # as one compact message with the user's preferred plain closer-summary lines.
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    elif summary["deleted_channels"]:
        suffix = "would delete" if args.dry_run else "deleted"
        print("\n".join(f"{item['channel_name']} - {suffix}" for item in summary["deleted_channels"]))
        if summary["errors"] and (args.verbose or args.dry_run):
            print("\n".join(f"ERROR: {item['channel_name']}: {item['error']}" for item in summary["errors"]))
    elif summary["errors"]:
        print("\n".join(f"ERROR: {item['channel_name']}: {item['error']}" for item in summary["errors"]))
    elif args.dry_run or args.verbose:
        print("No review-prs channels to delete.")
    return 1 if summary["errors"] and not summary["deleted_channels"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
