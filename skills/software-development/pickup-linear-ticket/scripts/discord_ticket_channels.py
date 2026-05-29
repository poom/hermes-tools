#!/usr/bin/env python3
"""Create or reuse Discord text channels for Linear ticket work.

This helper intentionally prints only Discord object metadata, never the bot token.
It creates/reuses a named category (default: tickets) in the same guild as a source
channel/thread, then creates/reuses one text channel per Linear ticket.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DISCORD_API_BASE = "https://discord.com/api/v10"
TEXT_CHANNEL = 0
CATEGORY_CHANNEL = 4
MAX_DISCORD_CHANNEL_NAME = 100
DEFAULT_CATEGORY = "tickets"
DEFAULT_TOPIC_PREFIX = "Managed by Hermes pickup-linear-ticket."


class DiscordAPIError(RuntimeError):
    def __init__(self, status: int, body: str):
        self.status = status
        self.body = body
        super().__init__(f"Discord API error {status}: {body}")


def load_dotenv_token() -> str:
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    if token:
        return token
    hermes_home = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    env_path = hermes_home / ".env"
    if env_path.exists():
        for line in env_path.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "DISCORD_BOT_TOKEN":
                return value.strip().strip('"').strip("'")
    raise SystemExit("DISCORD_BOT_TOKEN is not available in env or ~/.hermes/.env")


def discord_request(method: str, path: str, token: str, *, body: dict[str, Any] | None = None) -> Any:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        f"{DISCORD_API_BASE}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "Hermes-pickup-linear-ticket",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            if resp.status == 204:
                return None
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        raise DiscordAPIError(exc.code, body_text) from exc


def slugify(value: str, *, max_len: int) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    if len(value) > max_len:
        value = value[:max_len].rstrip("-")
    return value or "ticket"


def ticket_channel_name(ticket_id: str, title: str) -> str:
    normalized_ticket = re.sub(r"[^A-Z0-9-]+", "-", ticket_id.upper()).strip("-")
    prefix = normalized_ticket.lower()
    budget = MAX_DISCORD_CHANNEL_NAME - len(prefix) - 1
    # Keep names readable and stable; do not consume the whole 100-char Discord limit.
    slug_budget = max(12, min(60, budget))
    return f"{prefix}-{slugify(title, max_len=slug_budget)}"[:MAX_DISCORD_CHANNEL_NAME].rstrip("-")


def managed_topic(ticket_id: str, title: str, linear_url: str = "") -> str:
    parts = [DEFAULT_TOPIC_PREFIX, f"Ticket: {ticket_id.upper()} — {title}"]
    if linear_url:
        parts.append(f"Linear: {linear_url}")
    return " ".join(parts)[:1024]


def get_channel(token: str, channel_id: str) -> dict[str, Any]:
    channel = discord_request("GET", f"/channels/{channel_id}", token)
    if not isinstance(channel, dict):
        raise SystemExit(f"Could not fetch channel {channel_id}")
    return channel


def guild_channels(token: str, guild_id: str) -> list[dict[str, Any]]:
    channels = discord_request("GET", f"/guilds/{guild_id}/channels", token)
    return channels if isinstance(channels, list) else []


def find_or_create_category(token: str, guild_id: str, name: str) -> tuple[dict[str, Any], bool]:
    channels = guild_channels(token, guild_id)
    for channel in channels:
        if channel.get("type") == CATEGORY_CHANNEL and (channel.get("name") or "").lower() == name.lower():
            return channel, False
    channel = discord_request("POST", f"/guilds/{guild_id}/channels", token, body={"name": name, "type": CATEGORY_CHANNEL})
    return channel, True


def find_existing_ticket_channel(
    token: str,
    guild_id: str,
    parent_id: str,
    ticket_id: str,
    desired_name: str,
) -> dict[str, Any] | None:
    """Find existing channel by exact name or ticket-ID prefix; prefer the target category."""
    normalized_prefix = re.sub(r"[^a-z0-9-]+", "-", ticket_id.lower()).strip("-")
    pattern = re.compile(rf"^{re.escape(normalized_prefix)}(?:-|$)")
    matches = [
        channel
        for channel in guild_channels(token, guild_id)
        if channel.get("type") == TEXT_CHANNEL
        and ((channel.get("name") == desired_name) or pattern.match(channel.get("name") or ""))
    ]
    if not matches:
        return None
    matches.sort(
        key=lambda channel: (
            channel.get("parent_id") != parent_id,
            "pickup-linear-ticket" not in (channel.get("topic") or ""),
            int(channel.get("position") or 0),
        )
    )
    return matches[0]


def ensure_ticket_channel(args: argparse.Namespace) -> dict[str, Any]:
    token = load_dotenv_token()
    source = get_channel(token, args.source_channel_id)
    guild_id = source.get("guild_id")
    if not guild_id:
        raise SystemExit(f"Source channel/thread {args.source_channel_id} does not have a guild_id")

    name = ticket_channel_name(args.ticket_id, args.title)
    topic = args.topic[:1024] if args.topic else managed_topic(args.ticket_id, args.title, args.linear_url)
    category, category_created = find_or_create_category(token, guild_id, args.category_name)
    parent_id = category.get("id")
    if not parent_id:
        raise SystemExit(f"Could not resolve category ID for {args.category_name!r}")

    existing = find_existing_ticket_channel(token, guild_id, parent_id, args.ticket_id, name)
    if existing:
        patch_body: dict[str, Any] = {}
        previous_name = existing.get("name") or ""
        previous_topic = existing.get("topic") or ""
        previous_parent_id = existing.get("parent_id")
        if previous_name != name:
            patch_body["name"] = name
        if previous_topic != topic:
            patch_body["topic"] = topic
        if previous_parent_id != parent_id:
            patch_body["parent_id"] = parent_id
        channel = discord_request("PATCH", f"/channels/{existing.get('id')}", token, body=patch_body) if patch_body else existing
        return {
            "success": True,
            "action": "reuse",
            "reused": True,
            "channel_id": channel.get("id"),
            "name": channel.get("name"),
            "previous_name": previous_name,
            "guild_id": channel.get("guild_id"),
            "parent_id": channel.get("parent_id"),
            "previous_parent_id": previous_parent_id,
            "category_name": args.category_name,
            "category_id": parent_id,
            "category_created": category_created,
            "topic": channel.get("topic"),
        }

    channel = discord_request(
        "POST",
        f"/guilds/{guild_id}/channels",
        token,
        body={"name": name, "type": TEXT_CHANNEL, "parent_id": parent_id, "topic": topic},
    )
    return {
        "success": True,
        "action": "create",
        "reused": False,
        "channel_id": channel.get("id"),
        "name": channel.get("name"),
        "guild_id": channel.get("guild_id"),
        "parent_id": channel.get("parent_id"),
        "category_name": args.category_name,
        "category_id": parent_id,
        "category_created": category_created,
        "topic": channel.get("topic"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    ensure = sub.add_parser("ensure", help="Create or reuse one Discord text channel for a Linear ticket")
    ensure.add_argument("--source-channel-id", required=True, help="Any channel/thread ID in the target Discord guild")
    ensure.add_argument("--ticket-id", required=True, help="Linear ticket identifier, e.g. FE-2470")
    ensure.add_argument("--title", required=True, help="Linear ticket title")
    ensure.add_argument("--linear-url", default="", help="Linear ticket URL for the channel topic")
    ensure.add_argument("--category-name", default=DEFAULT_CATEGORY, help="Category to create/reuse; default: tickets")
    ensure.add_argument("--topic", default="", help="Override Discord channel topic")
    ensure.set_defaults(func=ensure_ticket_channel)

    args = parser.parse_args()
    try:
        result = args.func(args)
    except DiscordAPIError as exc:
        print(json.dumps({"success": False, "status": exc.status, "error": exc.body}), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
