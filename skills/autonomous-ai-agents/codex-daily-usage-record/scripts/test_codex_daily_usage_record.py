#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).with_name("codex_daily_usage_record.py")


def load_module():
    spec = importlib.util.spec_from_file_location("codex_daily_usage_record_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")


class CodexDailyUsageRecordTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tmp_path = Path(self.tmp.name)
        self.module.CODEX_SESSIONS = self.tmp_path / ".codex" / "sessions"
        self.module.OUT_DIR = self.tmp_path / ".hermes" / "usage"
        self.module.MACHINE_ID = "Hermione"
        self.module.CSV_PATH = self.module.OUT_DIR / "codex_daily_usage_Hermione.csv"
        self.module.JSON_PATH = self.module.OUT_DIR / "codex_daily_usage_latest_Hermione.json"

    def test_safe_machine_id_aliases_hostname_and_sanitizes_override(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(self.module.socket, "gethostname", return_value="Wynn-MBP.local"):
            self.assertEqual("Hermione", self.module.safe_machine_id())
        with mock.patch.dict(os.environ, {"CODEX_USAGE_MACHINE_ID": "Work Laptop !!"}, clear=True):
            self.assertEqual("Work-Laptop", self.module.safe_machine_id())

    def test_parse_logs_uses_max_usage_per_session_and_captures_rate_limits(self) -> None:
        session_file = self.module.CODEX_SESSIONS / "2026" / "05" / "07" / "session.jsonl"
        write_jsonl(session_file, [
            {
                "timestamp": "2026-05-07T01:00:00Z",
                "payload": {
                    "model": "gpt-5.5",
                    "info": {"total_token_usage": {"input_tokens": 5, "cached_input_tokens": 1, "output_tokens": 2, "reasoning_output_tokens": 0, "total_tokens": 7}},
                },
            },
            {
                "timestamp": "2026-05-07T01:10:00Z",
                "payload": {
                    "model": "gpt-5.5",
                    "info": {"total_token_usage": {"input_tokens": 20, "cached_input_tokens": 10, "output_tokens": 5, "reasoning_output_tokens": 3, "total_tokens": 25}},
                    "rate_limits": {"plan_type": "pro", "primary": {"used_percent": 13.0}},
                },
            },
        ])

        sessions, rate_events = self.module.parse_logs()
        self.assertEqual(1, len(sessions))
        self.assertEqual("Hermione", sessions[0]["machine"])
        self.assertEqual("gpt-5.5", sessions[0]["model"])
        self.assertEqual(25, sessions[0]["usage"]["total_tokens"])
        self.assertEqual(1, len(rate_events))

    def test_aggregate_and_write_outputs(self) -> None:
        sessions = [
            {"machine": "Hermione", "day": "2026-05-07", "model": "gpt-5.5", "usage": {"input_tokens": 20, "cached_input_tokens": 10, "output_tokens": 5, "reasoning_output_tokens": 3, "total_tokens": 25}},
            {"machine": "Hermione", "day": "2026-05-07", "model": "gpt-5.5", "usage": {"input_tokens": 1, "cached_input_tokens": 0, "output_tokens": 2, "reasoning_output_tokens": 1, "total_tokens": 3}},
        ]
        rows = self.module.aggregate(sessions)
        self.assertEqual(1, len(rows))
        self.assertEqual(2, rows[0]["sessions"])
        self.assertEqual(28, rows[0]["total_tokens"])

        self.module.write_outputs(rows, sessions, [])
        with self.module.CSV_PATH.open(newline="", encoding="utf-8") as f:
            csv_rows = list(csv.DictReader(f))
        self.assertEqual("Hermione", csv_rows[0]["machine"])
        self.assertEqual("28", csv_rows[0]["total_tokens"])
        payload = json.loads(self.module.JSON_PATH.read_text(encoding="utf-8"))
        self.assertEqual("Hermione", payload["machine"])
        self.assertEqual("codex_cli_local_session_logs_only", payload["scope"])
        self.assertIn("Hermes/OpenAI provider calls outside Codex CLI", payload["excludes"])
        self.assertEqual(1, payload["days_recorded"])

    def test_no_logs_writes_empty_outputs(self) -> None:
        sessions, rate_events = self.module.parse_logs()
        rows = self.module.aggregate(sessions)
        self.module.write_outputs(rows, sessions, rate_events)
        self.assertTrue(self.module.CSV_PATH.exists())
        self.assertTrue(self.module.JSON_PATH.exists())
        payload = json.loads(self.module.JSON_PATH.read_text(encoding="utf-8"))
        self.assertEqual(0, payload["days_recorded"])


if __name__ == "__main__":
    unittest.main()
