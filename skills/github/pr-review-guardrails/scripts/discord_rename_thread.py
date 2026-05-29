#!/usr/bin/env python3
"""Rename a Discord thread/channel using the Discord REST API.

Usage:
  discord_rename_thread.py TOKEN THREAD_ID NEW_NAME

TOKEN may be:
  - the raw bot token
  - env:VAR_NAME to read the token from an environment variable
  - @/path/to/file to read the token from a file

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


def _usage() -> int:
    print("Usage: discord_rename_thread.py TOKEN THREAD_ID NEW_NAME", file=sys.stderr)
    print("TOKEN may be raw, env:VAR_NAME, or @/path/to/token_file", file=sys.stderr)
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


def _request(method: str, url: str, token: str, payload: dict | None = None) -> tuple[int, dict | str]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bot {token}",
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            parsed: dict | str = json.loads(body)
        except json.JSONDecodeError:
            parsed = body
        return e.code, parsed


def main(argv: list[str]) -> int:
    if len(argv) != 4 or argv[1] in {"-h", "--help"}:
        return _usage()

    token = _resolve_token(argv[1])
    thread_id = argv[2].strip()
    new_name = argv[3].strip()

    if not thread_id or not thread_id.isdigit():
        print("THREAD_ID must be a numeric Discord channel/thread id", file=sys.stderr)
        return 2
    if not new_name:
        print("NEW_NAME must not be empty", file=sys.stderr)
        return 2
    if len(new_name) > 100:
        print("NEW_NAME must be <= 100 characters for Discord channel/thread names", file=sys.stderr)
        return 2

    status, body = _request("PATCH", f"{API_BASE}/channels/{thread_id}", token, {"name": new_name})
    if 200 <= status < 300 and isinstance(body, dict):
        print(json.dumps({"ok": True, "status": status, "id": body.get("id"), "name": body.get("name")}, ensure_ascii=False))
        return 0

    # Redact token by construction: token is never included in this object.
    print(json.dumps({"ok": False, "status": status, "error": body}, ensure_ascii=False), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
