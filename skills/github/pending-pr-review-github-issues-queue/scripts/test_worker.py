#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import queue_common as qc

MODULE_PATH = SCRIPT_DIR / "worker.py"


def load_worker():
    spec = importlib.util.spec_from_file_location("pending_queue_worker_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_item() -> qc.QueueItem:
    return qc.QueueItem(
        queue_key="EWA-Services/finn-web-app#4974@abc123456789",
        repo="EWA-Services/finn-web-app",
        pr_number=4974,
        pr_url="https://github.com/EWA-Services/finn-web-app/pull/4974",
        head_sha="abc123456789",
        reviewer="poom",
        source="pending-pr-review",
        created_by="test",
        created_at="2026-05-28T17:52:28Z",
    )


class WorkerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.worker = load_worker()

    def test_default_main_uses_run_subcommand(self) -> None:
        with mock.patch.object(self.worker, "run_once", return_value=0) as run_once:
            rc = self.worker.main(["--queue-repo", "poom/hermes-pr-review-queue"])

        self.assertEqual(0, rc)
        self.assertEqual("run", run_once.call_args.args[0].command)

    def test_record_result_dry_run_prints_label_plan_without_github_calls(self) -> None:
        args = Namespace(
            queue_repo="poom/hermes-pr-review-queue",
            issue_number=123,
            worker_name="mac",
            lease_id="mac-test",
            queue_key="EWA-Services/finn-web-app#4974@abc123456789",
            result="approved",
            pr_review_id="999",
            review_state="APPROVED",
            commit_id="abc123456789",
            summary="Approved current head",
            apply=False,
        )

        with mock.patch("builtins.print") as printed:
            self.worker.record_result_command(args)

        output = "\n".join(" ".join(str(part) for part in call.args) for call in printed.call_args_list)
        self.assertIn("hermes-pr-review-result", output)
        self.assertIn("Would add labels: hermes:done, result:approved", output)
        self.assertIn("Would close issue #123 as completed", output)

    def test_local_worker_lock_prevents_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lock_dir = Path(td) / "worker.lock"
            with self.worker.local_worker_lock("mac", str(lock_dir)) as first_lock:
                self.assertEqual(lock_dir, first_lock)
                with self.worker.local_worker_lock("mac", str(lock_dir)) as second_lock:
                    self.assertIsNone(second_lock)
            self.assertFalse(lock_dir.exists())

    def test_build_review_prompt_contains_queue_context_and_safety_gates(self) -> None:
        item = make_item()
        issue = {"number": 123, "url": "https://github.com/poom/hermes-pr-review-queue/issues/123"}
        claimed = self.worker.ClaimedIssue(issue=issue, item=item, lease_id="mac-test")
        args = Namespace(
            queue_repo="poom/hermes-pr-review-queue",
            worker_name="mac",
            reviewer="poom",
        )

        prompt = self.worker.build_review_prompt(args, claimed)

        self.assertIn("Queue issue number: 123", prompt)
        self.assertIn("Expected head SHA: abc123456789", prompt)
        self.assertIn("Re-fetch the live PR state", prompt)
        self.assertIn("python3 ", prompt)
        self.assertIn("record-result", prompt)
        self.assertIn("pr-review-guardrails", prompt)

    def test_run_once_dry_run_does_not_claim_issue(self) -> None:
        item = make_item()
        issue = {
            "number": 123,
            "url": "https://github.com/poom/hermes-pr-review-queue/issues/123",
            "body": qc.render_queue_issue_body(item),
            "labels": [{"name": "hermes:queued"}, {"name": "source:pending-pr-review"}],
            "createdAt": "2026-05-28T17:52:28Z",
        }
        args = Namespace(
            worker_name="mac",
            queue_repo="poom/hermes-pr-review-queue",
            source_label=["source:pending-pr-review"],
            limit=50,
            apply=False,
            schedule_hermes=False,
            claim_only=False,
        )

        with (
            mock.patch.object(self.worker, "list_candidate_issues", return_value=[issue]),
            mock.patch.object(self.worker, "claim_issue") as claim_issue,
            mock.patch("builtins.print"),
        ):
            rc = self.worker.run_once(args)

        self.assertEqual(0, rc)
        claim_issue.assert_not_called()


if __name__ == "__main__":
    unittest.main()
