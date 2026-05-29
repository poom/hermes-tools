#!/usr/bin/env python3
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).with_name("discord_rename_thread.py")
spec = importlib.util.spec_from_file_location("discord_rename_thread", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class DiscordRenameThreadTest(unittest.TestCase):
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

    def test_main_validates_thread_id_without_network(self):
        self.assertEqual(mod.main(["prog", "token", "not-a-number", "Name"]), 2)

    def test_main_patches_discord_channel_name(self):
        calls = []

        def fake_request(method, url, token, payload=None):
            calls.append((method, url, token, payload))
            return 200, {"id": "12345", "name": payload["name"]}

        original = mod._request
        mod._request = fake_request
        try:
            self.assertEqual(mod.main(["prog", "token", "12345", "repo #1 - Approved"]), 0)
        finally:
            mod._request = original

        self.assertEqual(calls, [("PATCH", f"{mod.API_BASE}/channels/12345", "token", {"name": "repo #1 - Approved"})])


if __name__ == "__main__":
    unittest.main()
