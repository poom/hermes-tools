#!/usr/bin/env python3
"""Create/delete Discord text channels for my-open-prs.

This helper intentionally prints only Discord object metadata, never the bot token.
It creates channels in the same guild/category as a source parent channel.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DISCORD_API_BASE = "https://discord.com/api/v10"
TEXT_CHANNEL = 0
CATEGORY_CHANNEL = 4


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
    raise SystemExit("DISCORD_BOT_TOKEN is not available in env or <home>/.hermes/.env")


def discord_request(method: str, path: str, token: str, *, body: dict[str, Any] | None = None) -> Any:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        f"{DISCORD_API_BASE}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "Hermes-my-open-prs",
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


def sanitize_channel_name(name: str) -> str:
    cleaned = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")
    cleaned = re.sub(r"-+", "-", cleaned)
    return cleaned[:90] or "pr-channel"


def is_managed_pr_channel_name(name: str) -> bool:
    return bool(re.search(r"(^pr-.+-\d+$|.+-pr-\d+$)", name))


def legacy_channel_aliases(name: str) -> set[str]:
    """Return accepted legacy aliases for the requested PR channel name."""
    match = re.fullmatch(r"(.+)-pr-(\d+)", name)
    if not match:
        return set()
    repo, number = match.groups()
    return {f"pr-{repo}-{number}"}


def get_channel(token: str, channel_id: str) -> dict[str, Any]:
    channel = discord_request("GET", f"/channels/{channel_id}", token)
    if not isinstance(channel, dict):
        raise SystemExit(f"Could not fetch channel {channel_id}")
    return channel


DEFAULT_TOPIC = "Managed by Hermes my-open-prs. This channel is deleted when the PR is merged/closed."


def guild_channels(token: str, guild_id: str) -> list[dict[str, Any]]:
    channels = discord_request("GET", f"/guilds/{guild_id}/channels", token)
    return channels if isinstance(channels, list) else []


def find_or_create_category(token: str, guild_id: str, name: str) -> tuple[dict[str, Any], bool]:
    for channel in guild_channels(token, guild_id):
        if channel.get("type") == CATEGORY_CHANNEL and channel.get("name") == name:
            return channel, False
    channel = discord_request("POST", f"/guilds/{guild_id}/channels", token, body={"name": name, "type": CATEGORY_CHANNEL})
    return channel, True


def find_existing_channel(
    token: str,
    guild_id: str,
    preferred_parent_id: str | None,
    name: str,
) -> dict[str, Any] | None:
    """Return an existing same-name text channel, if any.

    Discord permits duplicate channel names. The PR queue should be idempotent, so
    a create request for an already-existing PR channel adopts that channel rather
    than creating a duplicate. Prefer the target category, but search across the
    guild so legacy flat-category channels can be moved into bucket categories.
    """
    candidate_names = {name, *legacy_channel_aliases(name)}
    matches = [
        channel
        for channel in guild_channels(token, guild_id)
        if channel.get("type") == TEXT_CHANNEL and channel.get("name") in candidate_names
    ]
    if not matches:
        return None
    matches.sort(
        key=lambda channel: (
            channel.get("parent_id") != preferred_parent_id,
            "my-open-prs" not in (channel.get("topic") or ""),
            "gh-pr-queue" not in (channel.get("topic") or ""),
            int(channel.get("position") or 0),
        )
    )
    return matches[0]


def create_channel(args: argparse.Namespace) -> dict[str, Any]:
    token = load_dotenv_token()
    source = get_channel(token, args.source_channel_id)
    guild_id = source.get("guild_id")
    if not guild_id:
        raise SystemExit(f"Source channel {args.source_channel_id} does not have a guild_id")

    topic = args.topic[:1024] if args.topic else DEFAULT_TOPIC
    body: dict[str, Any] = {
        "name": sanitize_channel_name(args.name),
        "type": TEXT_CHANNEL,
        "topic": topic,
    }
    category_created = False
    if args.category_name:
        category, category_created = find_or_create_category(token, guild_id, args.category_name)
        parent_id = category.get("id")
    else:
        parent_id = args.category_id or source.get("parent_id")
    if parent_id:
        body["parent_id"] = parent_id

    existing = find_existing_channel(token, guild_id, parent_id, body["name"])
    if existing:
        previous_topic = existing.get("topic") or ""
        patch_body: dict[str, Any] = {}
        if previous_topic != topic:
            patch_body["topic"] = topic
        if existing.get("name") != body["name"]:
            patch_body["name"] = body["name"]
        if parent_id and existing.get("parent_id") != parent_id:
            patch_body["parent_id"] = parent_id
        channel = discord_request("PATCH", f"/channels/{existing.get('id')}", token, body=patch_body) if patch_body else existing
        return {
            "success": True,
            "action": "reuse",
            "reused": True,
            "channel_id": channel.get("id"),
            "name": channel.get("name"),
            "guild_id": channel.get("guild_id"),
            "parent_id": channel.get("parent_id"),
            "category_name": args.category_name,
            "category_created": category_created,
            "type": channel.get("type"),
            "previous_topic": previous_topic,
        }

    channel = discord_request("POST", f"/guilds/{guild_id}/channels", token, body=body)
    return {
        "success": True,
        "action": "create",
        "reused": False,
        "channel_id": channel.get("id"),
        "name": channel.get("name"),
        "guild_id": channel.get("guild_id"),
        "parent_id": channel.get("parent_id"),
        "category_name": args.category_name,
        "category_created": category_created,
        "type": channel.get("type"),
    }


def delete_channel(args: argparse.Namespace) -> dict[str, Any]:
    token = load_dotenv_token()
    if args.source_channel_id and str(args.channel_id) == str(args.source_channel_id):
        raise SystemExit("Refusing to delete the source/parent status channel")

    channel = get_channel(token, args.channel_id)
    name = channel.get("name") or ""
    channel_type = channel.get("type")
    if channel_type != TEXT_CHANNEL:
        raise SystemExit(f"Refusing to delete non-text channel {args.channel_id} type={channel_type}")
    if not args.force and not is_managed_pr_channel_name(name):
        raise SystemExit(f"Refusing to delete channel {args.channel_id} named {name!r}; expected managed PR channel name")

    discord_request("DELETE", f"/channels/{args.channel_id}", token)
    return {
        "success": True,
        "action": "delete",
        "channel_id": args.channel_id,
        "name": name,
    }


def move_channel(args: argparse.Namespace) -> dict[str, Any]:
    token = load_dotenv_token()
    source = get_channel(token, args.source_channel_id)
    guild_id = source.get("guild_id")
    if not guild_id:
        raise SystemExit(f"Source channel {args.source_channel_id} does not have a guild_id")
    channel = get_channel(token, args.channel_id)
    if channel.get("type") != TEXT_CHANNEL:
        raise SystemExit(f"Refusing to move non-text channel {args.channel_id} type={channel.get('type')}")
    category, category_created = find_or_create_category(token, guild_id, args.category_name)
    previous_parent_id = channel.get("parent_id")
    if previous_parent_id != category.get("id"):
        channel = discord_request("PATCH", f"/channels/{args.channel_id}", token, body={"parent_id": category.get("id")})
    return {
        "success": True,
        "action": "move",
        "channel_id": args.channel_id,
        "name": channel.get("name"),
        "previous_parent_id": previous_parent_id,
        "parent_id": channel.get("parent_id"),
        "category_name": args.category_name,
        "category_created": category_created,
    }


def rename_channel(args: argparse.Namespace) -> dict[str, Any]:
    token = load_dotenv_token()
    if args.source_channel_id and str(args.channel_id) == str(args.source_channel_id):
        raise SystemExit("Refusing to rename the source/parent status channel")
    channel = get_channel(token, args.channel_id)
    if channel.get("type") != TEXT_CHANNEL:
        raise SystemExit(f"Refusing to rename non-text channel {args.channel_id} type={channel.get('type')}")
    previous_name = channel.get("name") or ""
    if not args.force and not is_managed_pr_channel_name(previous_name):
        raise SystemExit(f"Refusing to rename channel {args.channel_id} named {previous_name!r}; expected managed PR channel name")
    new_name = sanitize_channel_name(args.name)
    if previous_name != new_name:
        channel = discord_request("PATCH", f"/channels/{args.channel_id}", token, body={"name": new_name})
    return {
        "success": True,
        "action": "rename",
        "channel_id": args.channel_id,
        "previous_name": previous_name,
        "name": channel.get("name"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="Create a PR text channel next to a source channel")
    create.add_argument("--source-channel-id", required=True, help="Existing status channel whose guild/category should be reused")
    create.add_argument("--name", required=True, help="Desired Discord text channel name")
    create.add_argument("--category-id", default="", help="Override category ID; defaults to source channel category")
    create.add_argument("--category-name", default="", help="Create/reuse this Discord category and place the PR channel there")
    create.add_argument("--topic", default="", help="Optional Discord channel topic")
    create.set_defaults(func=create_channel)

    move = sub.add_parser("move", help="Move a PR text channel into a named category")
    move.add_argument("--source-channel-id", required=True, help="Existing status channel used to identify the guild")
    move.add_argument("--channel-id", required=True, help="Discord text channel ID to move")
    move.add_argument("--category-name", required=True, help="Category to create/reuse and move the channel into")
    move.set_defaults(func=move_channel)

    rename = sub.add_parser("rename", help="Rename a managed PR text channel")
    rename.add_argument("--channel-id", required=True, help="Discord text channel ID to rename")
    rename.add_argument("--name", required=True, help="New Discord text channel name")
    rename.add_argument("--source-channel-id", default="", help="Parent/source channel ID to protect from rename")
    rename.add_argument("--force", action="store_true", help="Allow renaming a text channel whose current name is not a managed PR channel name")
    rename.set_defaults(func=rename_channel)

    delete = sub.add_parser("delete", help="Delete a managed PR text channel")
    delete.add_argument("--channel-id", required=True, help="Discord text channel ID to delete")
    delete.add_argument("--source-channel-id", default="", help="Parent/source channel ID to protect from deletion")
    delete.add_argument("--force", action="store_true", help="Allow deleting a text channel whose name is not a managed PR channel name")
    delete.set_defaults(func=delete_channel)

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
