#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import queue_common as qc

MODULE_PATH = SCRIPT_DIR / "enqueue_pr.py"


def load_module():
    spec = importlib.util.spec_from_file_location("pending_queue_enqueue_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_args(**overrides) -> Namespace:
    data = {
        "pr": "https://github.com/EWA-Services/user-iam/pull/201",
        "queue_repo": "poom/hermes-pr-review-queue",
        "reviewer": "poom",
        "apply": False,
        "ensure_labels": False,
        "origin": "manual",
        "priority": "normal",
        "requested_by": "manual",
        "request_text": "",
        "source_message_url": "",
        "delivery_target": "",
        "allow_draft": False,
        "allowed_owner": [],
        "force_rereview": False,
    }
    data.update(overrides)
    return Namespace(**data)


def pr_state(head: str = "newsha") -> dict:
    return {
        "headRefOid": head,
        "state": "OPEN",
        "isDraft": False,
        "url": "https://github.com/EWA-Services/user-iam/pull/201",
        "title": "Example PR",
    }


def issue_for(item: qc.QueueItem, number: int = 10, state: str = "OPEN") -> dict:
    return {
        "number": number,
        "state": state,
        "url": f"https://github.com/poom/hermes-pr-review-queue/issues/{number}",
        "labels": [{"name": "hermes:queued"}],
        "body": qc.render_queue_issue_body(item),
    }


class EnqueuePrTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def test_dry_run_creates_current_head_queue_item(self) -> None:
        args = make_args()
        with (
            mock.patch.object(self.module, "fetch_pr_state", return_value=pr_state("newsha")),
            mock.patch.object(self.module, "fetch_reviews", return_value=[]),
            mock.patch.object(self.module, "list_issues_by_queue_key", return_value=[]),
            mock.patch.object(self.module, "list_open_issues_by_pr_ref", return_value=[]),
        ):
            result = self.module.enqueue(args)

        self.assertEqual("would-create", result.action)
        self.assertEqual("EWA-Services/user-iam#201@newsha", result.queue_key)

    def test_existing_open_current_head_is_updated_not_duplicated(self) -> None:
        item = qc.QueueItem(
            queue_key="EWA-Services/user-iam#201@newsha",
            repo="EWA-Services/user-iam",
            pr_number=201,
            pr_url="https://github.com/EWA-Services/user-iam/pull/201",
            head_sha="newsha",
        )
        args = make_args(apply=True)
        with (
            mock.patch.object(self.module, "fetch_pr_state", return_value=pr_state("newsha")),
            mock.patch.object(self.module, "fetch_reviews", return_value=[]),
            mock.patch.object(self.module, "list_issues_by_queue_key", return_value=[issue_for(item)]),
            mock.patch.object(self.module, "list_open_issues_by_pr_ref", return_value=[issue_for(item)]),
            mock.patch.object(self.module, "issue_comment") as issue_comment,
            mock.patch.object(self.module, "issue_add_labels") as issue_add_labels,
        ):
            result = self.module.enqueue(args)

        self.assertEqual("updated-existing", result.action)
        issue_comment.assert_called_once()
        issue_add_labels.assert_called_once()

    def test_old_open_same_pr_issue_is_superseded_when_fresh_issue_is_created(self) -> None:
        old_item = qc.QueueItem(
            queue_key="EWA-Services/user-iam#201@oldsha",
            repo="EWA-Services/user-iam",
            pr_number=201,
            pr_url="https://github.com/EWA-Services/user-iam/pull/201",
            head_sha="oldsha",
        )
        args = make_args(apply=True)
        with (
            mock.patch.object(self.module, "fetch_pr_state", return_value=pr_state("newsha")),
            mock.patch.object(self.module, "fetch_reviews", return_value=[]),
            mock.patch.object(self.module, "list_issues_by_queue_key", return_value=[]),
            mock.patch.object(self.module, "list_open_issues_by_pr_ref", return_value=[issue_for(old_item, number=9)]),
            mock.patch.object(self.module, "create_issue", return_value="https://github.com/poom/hermes-pr-review-queue/issues/10") as create_issue,
            mock.patch.object(self.module, "issue_comment") as issue_comment,
            mock.patch.object(self.module, "issue_edit_labels") as issue_edit_labels,
            mock.patch.object(self.module, "issue_close") as issue_close,
        ):
            result = self.module.enqueue(args)

        self.assertEqual("created", result.action)
        self.assertIn("superseded_old_issue", result.notes[0])
        create_issue.assert_called_once()
        issue_comment.assert_called_once()
        issue_edit_labels.assert_called_once_with(
            args.queue_repo,
            9,
            add=["hermes:superseded"],
            remove=["hermes:queued", "hermes:claimed"],
        )
        issue_close.assert_called_once_with(args.queue_repo, 9, "not planned")

    def test_already_reviewed_current_head_is_not_queued(self) -> None:
        args = make_args()
        reviews = [{"user": {"login": "poom"}, "state": "APPROVED", "commit_id": "newsha", "id": 77}]
        with (
            mock.patch.object(self.module, "fetch_pr_state", return_value=pr_state("newsha")),
            mock.patch.object(self.module, "fetch_reviews", return_value=reviews),
        ):
            result = self.module.enqueue(args)

        self.assertEqual("skipped", result.action)
        self.assertIn("already has APPROVED", result.reason)

    def test_outside_allowed_owner_creates_confirmation_not_queued(self) -> None:
        args = make_args(allowed_owner=["EWA-Services"])
        with (
            mock.patch.object(self.module, "parse_pr_identifier", return_value=("External/repo", 7)),
            mock.patch.object(self.module, "fetch_pr_state", return_value={"headRefOid": "sha", "state": "OPEN", "isDraft": False, "url": "https://github.com/External/repo/pull/7"}),
            mock.patch.object(self.module, "fetch_reviews", return_value=[]),
            mock.patch.object(self.module, "list_issues_by_queue_key", return_value=[]),
            mock.patch.object(self.module, "list_open_issues_by_pr_ref", return_value=[]),
        ):
            result = self.module.enqueue(args)

        self.assertEqual("would-create-confirmation", result.action)
        self.assertEqual("outside allowed owner scope", result.reason)
        self.assertEqual(
            ["source:chat-request", "origin:manual", "priority:normal", "needs:poom-confirmation"],
            self.module.queue_labels(origin="manual", priority="normal", needs_confirmation=True),
        )


if __name__ == "__main__":
    unittest.main()
