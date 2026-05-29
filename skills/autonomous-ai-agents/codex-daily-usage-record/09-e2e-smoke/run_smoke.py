#!/usr/bin/env python3
"""E2E smoke command for codex-daily-usage-record.

Run from the skill directory or repository root:

    python3 09-e2e-smoke/run_smoke.py

The smoke test invokes the same production recorder script that operators and
Hermes cron use, against a temporary HOME under tmp/e2e-smoke/latest.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "codex_daily_usage_record.py"
EVIDENCE_DIR = SKILL_DIR / "tmp" / "e2e-smoke" / "latest"
HOME = EVIDENCE_DIR / "home"


def main() -> int:
    if EVIDENCE_DIR.exists():
        shutil.rmtree(EVIDENCE_DIR)
    session = HOME / ".codex" / "sessions" / "2026" / "05" / "07" / "session.jsonl"
    session.parent.mkdir(parents=True, exist_ok=True)
    session.write_text(json.dumps({
        "timestamp": "2026-05-07T01:00:00Z",
        "payload": {
            "model": "gpt-5.5",
            "info": {"total_token_usage": {"input_tokens": 100, "cached_input_tokens": 40, "output_tokens": 20, "reasoning_output_tokens": 5, "total_tokens": 120}},
        },
    }) + "\n", encoding="utf-8")

    env = os.environ.copy()
    env["HOME"] = str(HOME)
    env["CODEX_USAGE_MACHINE_ID"] = "Hermione"
    result = subprocess.run([sys.executable, str(SCRIPT)], env=env, text=True, capture_output=True, timeout=30)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / "stdout.txt").write_text(result.stdout, encoding="utf-8")
    (EVIDENCE_DIR / "stderr.txt").write_text(result.stderr, encoding="utf-8")
    (EVIDENCE_DIR / "returncode.txt").write_text(str(result.returncode), encoding="utf-8")

    csv_path = HOME / ".hermes" / "usage" / "codex_daily_usage_Hermione.csv"
    json_path = HOME / ".hermes" / "usage" / "codex_daily_usage_latest_Hermione.json"
    ok = (
        result.returncode == 0
        and "Codex CLI local token usage recorded" in result.stdout
        and "Machine: Hermione" in result.stdout
        and csv_path.exists()
        and json_path.exists()
        and "120" in csv_path.read_text(encoding="utf-8")
    )
    if ok:
        print(f"E2E_SMOKE PASS evidence={EVIDENCE_DIR}")
        return 0
    print(f"E2E_SMOKE FAIL evidence={EVIDENCE_DIR}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
