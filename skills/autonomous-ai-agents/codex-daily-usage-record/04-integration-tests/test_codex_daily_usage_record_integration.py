#!/usr/bin/env python3
"""INTEGRATION_TEST: run the bundled Codex usage recorder as a subprocess.

This live-test harness uses a temporary HOME with fixture Codex logs. It requires
no network and no credentials; if the runtime cannot create temporary files it
fails explicitly rather than touching a real home directory.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "codex_daily_usage_record.py"


class CodexDailyUsageRecordIntegrationTest(unittest.TestCase):
    def test_subprocess_fixture_home_writes_expected_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            session = home / ".codex" / "sessions" / "2026" / "05" / "07" / "session.jsonl"
            session.parent.mkdir(parents=True, exist_ok=True)
            session.write_text(json.dumps({
                "timestamp": "2026-05-07T01:00:00Z",
                "payload": {
                    "model": "gpt-5.5",
                    "info": {"total_token_usage": {"input_tokens": 10, "cached_input_tokens": 4, "output_tokens": 2, "reasoning_output_tokens": 1, "total_tokens": 12}},
                    "rate_limits": {"plan_type": "pro", "primary": {"used_percent": 13.0}, "secondary": {"used_percent": 11.0}},
                },
            }) + "\n", encoding="utf-8")
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["CODEX_USAGE_MACHINE_ID"] = "Hermione"
            result = subprocess.run([sys.executable, str(SCRIPT)], env=env, text=True, capture_output=True, timeout=30)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("Codex CLI local token usage recorded", result.stdout)
            self.assertIn("Machine: Hermione", result.stdout)
            csv_path = home / ".hermes" / "usage" / "codex_daily_usage_Hermione.csv"
            json_path = home / ".hermes" / "usage" / "codex_daily_usage_latest_Hermione.json"
            self.assertTrue(csv_path.exists())
            self.assertTrue(json_path.exists())
            self.assertIn("total_tokens", csv_path.read_text(encoding="utf-8"))
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual("Hermione", payload["machine"])
            self.assertEqual(1, payload["sessions_with_usage"])


if __name__ == "__main__":
    unittest.main()
