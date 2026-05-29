#!/usr/bin/env python3
"""Offline unit tests for discord_pr_channels."""

from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest import mock

import discord_pr_channels as helper


class FakeResponse:
    def __init__(self, payload=None, status=200):
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class DiscordPrChannelsTest(unittest.TestCase):
    def test_sanitize_channel_name(self) -> None:
        self.assertEqual("web-pr-12", helper.sanitize_channel_name("web PR #12"))
        self.assertEqual("web-12", helper.sanitize_channel_name("web 12"))
        self.assertTrue(helper.is_managed_pr_channel_name("web-pr-12"))
        self.assertTrue(helper.is_managed_pr_channel_name("pr-web-12"))
        self.assertFalse(helper.is_managed_pr_channel_name("web-12"))
        self.assertLessEqual(len(helper.sanitize_channel_name("x" * 200)), 90)

    def test_create_channel_reuses_source_guild_and_category(self) -> None:
        calls = []

        def fake_urlopen(req, timeout=20):
            calls.append(req)
            if req.get_method() == "GET" and req.full_url.endswith("/channels/parent"):
                return FakeResponse({"id": "parent", "guild_id": "guild", "parent_id": "category", "type": 0})
            if req.get_method() == "GET" and req.full_url.endswith("/guilds/guild/channels"):
                return FakeResponse([])
            body = json.loads(req.data.decode("utf-8"))
            self.assertEqual("web-pr-12", body["name"])
            self.assertEqual(0, body["type"])
            self.assertEqual("category", body["parent_id"])
            return FakeResponse({"id": "created", "guild_id": "guild", "parent_id": "category", "name": body["name"], "type": 0})

        args = SimpleNamespace(source_channel_id="parent", name="web-pr-12", category_id="", category_name="", topic="")
        with mock.patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "token"}), mock.patch("urllib.request.urlopen", fake_urlopen):
            result = helper.create_channel(args)

        self.assertTrue(result["success"])
        self.assertFalse(result["reused"])
        self.assertEqual("created", result["channel_id"])
        self.assertEqual("web-pr-12", result["name"])
        self.assertEqual(["GET", "GET", "POST"], [call.get_method() for call in calls])

    def test_create_channel_reuses_and_renames_legacy_same_pr_channel(self) -> None:
        calls = []

        def fake_urlopen(req, timeout=20):
            calls.append(req)
            if req.get_method() == "GET" and req.full_url.endswith("/channels/parent"):
                return FakeResponse({"id": "parent", "guild_id": "guild", "parent_id": "category", "type": 0})
            if req.get_method() == "GET" and req.full_url.endswith("/guilds/guild/channels"):
                return FakeResponse([
                    {
                        "id": "existing",
                        "guild_id": "guild",
                        "parent_id": "category",
                        "name": "pr-web-12",
                        "topic": "EWA-Services/web #12 — managed by Hermes gh-pr-queue",
                        "type": 0,
                    }
                ])
            if req.get_method() == "PATCH":
                body = json.loads(req.data.decode("utf-8"))
                self.assertIn("my-open-prs", body["topic"])
                self.assertEqual("web-pr-12", body["name"])
                return FakeResponse({"id": "existing", "guild_id": "guild", "parent_id": "category", "name": "web-pr-12", "topic": body["topic"], "type": 0})
            raise AssertionError(f"unexpected request {req.get_method()} {req.full_url}")

        args = SimpleNamespace(source_channel_id="parent", name="web-pr-12", category_id="", category_name="", topic="")
        with mock.patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "token"}), mock.patch("urllib.request.urlopen", fake_urlopen):
            result = helper.create_channel(args)

        self.assertTrue(result["success"])
        self.assertTrue(result["reused"])
        self.assertEqual("reuse", result["action"])
        self.assertEqual("existing", result["channel_id"])
        self.assertEqual(["GET", "GET", "PATCH"], [call.get_method() for call in calls])

    def test_delete_channel_refuses_source_channel(self) -> None:
        args = SimpleNamespace(channel_id="parent", source_channel_id="parent", force=False)
        with mock.patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "token"}):
            with self.assertRaises(SystemExit):
                helper.delete_channel(args)

    def test_delete_channel_requires_pr_prefix_unless_forced(self) -> None:
        def fake_urlopen(req, timeout=20):
            return FakeResponse({"id": "chan", "name": "general", "type": 0})

        args = SimpleNamespace(channel_id="chan", source_channel_id="parent", force=False)
        with mock.patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "token"}), mock.patch("urllib.request.urlopen", fake_urlopen):
            with self.assertRaises(SystemExit):
                helper.delete_channel(args)

    def test_delete_channel_calls_delete_for_pr_channel(self) -> None:
        methods = []

        def fake_urlopen(req, timeout=20):
            methods.append(req.get_method())
            if req.get_method() == "GET":
                return FakeResponse({"id": "chan", "name": "web-pr-12", "type": 0})
            return FakeResponse(None, status=204)

        args = SimpleNamespace(channel_id="chan", source_channel_id="parent", force=False)
        with mock.patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "token"}), mock.patch("urllib.request.urlopen", fake_urlopen):
            result = helper.delete_channel(args)

        self.assertTrue(result["success"])
        self.assertEqual(["GET", "DELETE"], methods)

    def test_rename_channel_updates_managed_pr_channel_name(self) -> None:
        methods = []

        def fake_urlopen(req, timeout=20):
            methods.append(req.get_method())
            if req.get_method() == "GET":
                return FakeResponse({"id": "chan", "name": "pr-web-12", "type": 0})
            body = json.loads(req.data.decode("utf-8"))
            self.assertEqual("web-pr-12", body["name"])
            return FakeResponse({"id": "chan", "name": body["name"], "type": 0})

        args = SimpleNamespace(channel_id="chan", source_channel_id="parent", name="web-pr-12", force=False)
        with mock.patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "token"}), mock.patch("urllib.request.urlopen", fake_urlopen):
            result = helper.rename_channel(args)

        self.assertTrue(result["success"])
        self.assertEqual("pr-web-12", result["previous_name"])
        self.assertEqual("web-pr-12", result["name"])
        self.assertEqual(["GET", "PATCH"], methods)


if __name__ == "__main__":
    unittest.main()
