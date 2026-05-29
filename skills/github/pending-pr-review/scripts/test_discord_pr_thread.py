#!/usr/bin/env python3
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).with_name("discord_pr_thread.py")
spec = importlib.util.spec_from_file_location("discord_pr_thread", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class DiscordPrThreadTest(unittest.TestCase):
    def test_resolve_token_from_env_and_file(self):
        os.environ["DISCORD_TEST_TOKEN"] = " env-token \n"
        self.assertEqual(mod._resolve_token("env:DISCORD_TEST_TOKEN"), "env-token")
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            f.write(" file-token \n")
            path = f.name
        try:
            self.assertEqual(mod._resolve_token("@" + path), "file-token")
        finally:
            os.unlink(path)

    def test_validate_snowflake_and_name_fail_fast_without_network(self):
        with self.assertRaises(SystemExit):
            mod._validate_snowflake("abc", "THREAD_ID")
        with self.assertRaises(SystemExit):
            mod._validate_name("", "THREAD_NAME")
        with self.assertRaises(SystemExit):
            mod._validate_name("x" * 101, "THREAD_NAME")

    def test_create_and_send_use_expected_discord_paths(self):
        calls = []

        def fake_request(method, path, token, payload=None):
            calls.append((method, path, token, payload))
            if path.endswith("/threads"):
                return 201, {"id": "98765", "name": payload["name"]}
            return 200, {"id": "555"}

        original = mod._request
        mod._request = fake_request
        try:
            self.assertEqual(mod.main(["prog", "token", "create", "12345", "repo-pr-1", "hello"]), 0)
            self.assertEqual(mod.main(["prog", "token", "send", "98765", "done"]), 0)
        finally:
            mod._request = original

        self.assertEqual(calls[0], ("POST", "/channels/12345/threads", "token", {"name": "repo-pr-1", "type": mod.PUBLIC_THREAD_TYPE, "auto_archive_duration": mod.DEFAULT_AUTO_ARCHIVE_MINUTES}))
        self.assertEqual(calls[1], ("POST", "/channels/98765/messages", "token", {"content": "hello"}))
        self.assertEqual(calls[2], ("POST", "/channels/98765/messages", "token", {"content": "done"}))


if __name__ == "__main__":
    unittest.main()
