#!/usr/bin/env python3
"""Offline tests for action-summary_llm_judge."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

JUDGE_PATH = Path(__file__).with_name("action-summary_llm_judge.py")
SPEC = importlib.util.spec_from_file_location("action_summary_llm_judge", JUDGE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["action_summary_llm_judge"] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ActionSummaryJudgeTest(unittest.TestCase):
    def test_passes_when_summary_contains_required_terms(self) -> None:
        verdict = MODULE.judge_summary(
            "changes requested by @jai; policy-bot is failing",
            {"must_include": ["changes requested", "@jai", "policy-bot"], "must_not_include": []},
        )

        self.assertEqual("pass", verdict.status)

    def test_fails_when_summary_is_vague(self) -> None:
        verdict = MODULE.judge_summary(
            "needs attention",
            {"must_include": ["base branch"], "must_not_include": []},
        )

        self.assertEqual("fail", verdict.status)


if __name__ == "__main__":
    unittest.main()
