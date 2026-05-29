#!/usr/bin/env python3
"""Create, send to, and rename Discord PR review threads via REST.

Usage:
  discord_pr_thread.py TOKEN create PARENT_CHANNEL_ID THREAD_NAME [STARTER_MESSAGE|-|@file]
  discord_pr_thread.py TOKEN send THREAD_ID MESSAGE|-|@file
  discord_pr_thread.py TOKEN rename THREAD_ID NEW_NAME

TOKEN may be:
  - the raw bot token
  - env:VAR_NAME to read from an environment variable
  - @/path/to/file to read from a file

The script never prints the token. It includes a DiscordBot-style User-Agent to
avoid misleading Cloudflare 403 / error code 1010 responses.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

USER_AGENT = "DiscordBot (https://hermes-agent.nousresearch.com, 1.0)"
API_BASE = "https://discord.com/api/v10"
PUBLIC_THREAD_TYPE = 11
DEFAULT_AUTO_ARCHIVE_MINUTES = 1440


def _usage() -> int:
    print(__doc__.strip(), file=sys.stderr)
    return 2


def _resolve_token(token_arg: str) -> str:
    if token_arg.startswith("env:"):
        var = token_arg[4:]
        token = os.environ.get(var, "")
        if not token:
            raise SystemExit(f"Token environment variable is empty or missing: {var}")
        return token.strip()
    if token_arg.startswith("@"):
        path = token_arg[1:]
        with open(path, "r", encoding="utf-8") as f:
            token = f.read().strip()
        if not token:
            raise SystemExit(f"Token file is empty: {path}")
        return token
    return token_arg.strip()


def _resolve_text_arg(value: str | None) -> str:
    if value is None:
        return ""
    if value == "-":
        return sys.stdin.read()
    if value.startswith("@"):
        with open(value[1:], "r", encoding="utf-8") as f:
            return f.read()
    return value


def _validate_snowflake(value: str, label: str) -> None:
    if not value or not value.isdigit():
        raise SystemExit(f"{label} must be a numeric Discord channel/thread id")


def _validate_name(value: str, label: str = "THREAD_NAME") -> str:
    value = (value or "").strip()
    if not value:
        raise SystemExit(f"{label} must not be empty")
    if len(value) > 100:
        raise SystemExit(f"{label} must be <= 100 characters for Discord thread names")
    return value


def _request(method: str, path: str, token: str, payload: dict | None = None) -> tuple[int, dict | str]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bot {token}",
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            parsed: dict | str = json.loads(body)
        except json.JSONDecodeError:
            parsed = body
        return e.code, parsed


def _fail(status: int, body: dict | str) -> int:
    print(json.dumps({"ok": False, "status": status, "error": body}, ensure_ascii=False), file=sys.stderr)
    return 1


def _create(token: str, argv: list[str]) -> int:
    # argv layout after action is [parent_channel_id, thread_name, optional_starter_message]
    if len(argv) not in {2, 3}:
        return _usage()
    parent_channel_id = argv[0].strip()
    thread_name = _validate_name(argv[1])
    starter = _resolve_text_arg(argv[2]) if len(argv) == 3 else ""
    _validate_snowflake(parent_channel_id, "PARENT_CHANNEL_ID")

    payload = {
        "name": thread_name,
        "type": PUBLIC_THREAD_TYPE,
        "auto_archive_duration": DEFAULT_AUTO_ARCHIVE_MINUTES,
    }
    status, body = _request("POST", f"/channels/{parent_channel_id}/threads", token, payload)
    if not (200 <= status < 300 and isinstance(body, dict)):
        return _fail(status, body)

    thread_id = str(body.get("id") or "")
    if not thread_id:
        return _fail(status, {"message": "Discord response did not contain a thread id", "body": body})

    message_id = None
    if starter.strip():
        msg_status, msg_body = _request("POST", f"/channels/{thread_id}/messages", token, {"content": starter})
        if not (200 <= msg_status < 300 and isinstance(msg_body, dict)):
            return _fail(msg_status, msg_body)
        message_id = msg_body.get("id")

    print(json.dumps({"ok": True, "action": "create", "status": status, "thread_id": thread_id, "name": body.get("name"), "message_id": message_id}, ensure_ascii=False))
    return 0


def _send(token: str, argv: list[str]) -> int:
    if len(argv) != 2:
        return _usage()
    thread_id = argv[0].strip()
    message = _resolve_text_arg(argv[1])
    _validate_snowflake(thread_id, "THREAD_ID")
    if not message.strip():
        raise SystemExit("MESSAGE must not be empty")
    status, body = _request("POST", f"/channels/{thread_id}/messages", token, {"content": message})
    if 200 <= status < 300 and isinstance(body, dict):
        print(json.dumps({"ok": True, "action": "send", "status": status, "thread_id": thread_id, "message_id": body.get("id")}, ensure_ascii=False))
        return 0
    return _fail(status, body)


def _rename(token: str, argv: list[str]) -> int:
    if len(argv) != 2:
        return _usage()
    thread_id = argv[0].strip()
    new_name = _validate_name(argv[1], "NEW_NAME")
    _validate_snowflake(thread_id, "THREAD_ID")
    status, body = _request("PATCH", f"/channels/{thread_id}", token, {"name": new_name})
    if 200 <= status < 300 and isinstance(body, dict):
        print(json.dumps({"ok": True, "action": "rename", "status": status, "thread_id": thread_id, "name": body.get("name")}, ensure_ascii=False))
        return 0
    return _fail(status, body)


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] in {"-h", "--help"}:
        return _usage()
    token = _resolve_token(argv[1])
    action = argv[2].strip().lower()
    rest = argv[3:]
    if action == "create":
        if len(rest) not in {2, 3}:
            return _usage()
        return _create(token, rest)
    if action == "send":
        return _send(token, rest)
    if action == "rename":
        return _rename(token, rest)
    print(f"Unknown action: {action}", file=sys.stderr)
    return _usage()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
