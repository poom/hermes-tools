#!/usr/bin/env python3
from __future__ import annotations

import unittest
from datetime import UTC, datetime

import queue_common as qc


def make_item(**overrides):
    data = {
        "queue_key": "EWA-Services/finn-web-app#4974@abc123456789",
        "repo": "EWA-Services/finn-web-app",
        "pr_number": 4974,
        "pr_url": "https://github.com/EWA-Services/finn-web-app/pull/4974",
        "head_sha": "abc123456789",
        "reviewer": "poom",
        "source": "pending-pr-review",
        "created_by": "test",
        "created_at": "2026-05-28T17:52:28Z",
    }
    data.update(overrides)
    return qc.QueueItem(**data)


def comment(comment_id: int, body: str, created_at: str = "2026-05-28T17:52:28Z") -> dict:
    return {"id": comment_id, "body": body, "created_at": created_at}


class QueueCommonTest(unittest.TestCase):
    def test_render_and_parse_queue_item_body(self) -> None:
        item = make_item()
        body = qc.render_queue_issue_body(item)

        parsed = qc.parse_queue_item(body)

        self.assertEqual(item, parsed)
        self.assertIn("hermes-pr-review-queue-item", body)
        self.assertIn("Before posting any GitHub review", body)

    def test_missing_queue_metadata_returns_none(self) -> None:
        self.assertIsNone(qc.parse_queue_item("ordinary issue body"))

    def test_compute_queue_key(self) -> None:
        self.assertEqual(
            "EWA-Services/tools#133@def456",
            qc.compute_queue_key("EWA-Services/tools", "133", "def456"),
        )

    def test_parse_pr_identifier_accepts_url_and_shorthand(self) -> None:
        self.assertEqual(
            ("EWA-Services/finn-web-app", 4974),
            qc.parse_pr_identifier("https://github.com/EWA-Services/finn-web-app/pull/4974"),
        )
        self.assertEqual(
            ("EWA-Services/tools", 133),
            qc.parse_pr_identifier("please queue EWA-Services/tools#133"),
        )

    def test_claim_winner_is_earliest_non_expired_claim(self) -> None:
        item = make_item()
        mac = qc.render_claim_comment(
            item,
            worker="mac",
            lease_id="mac-1",
            claimed_at="2026-05-28T17:52:28Z",
            expires_at="2026-05-28T19:22:28Z",
        )
        ubuntu = qc.render_claim_comment(
            item,
            worker="ubuntu",
            lease_id="ubuntu-1",
            claimed_at="2026-05-28T17:52:29Z",
            expires_at="2026-05-28T19:22:29Z",
        )

        winner = qc.choose_winning_claim(
            [comment(101, ubuntu), comment(100, mac)],
            queue_key=item.queue_key,
            now=datetime(2026, 5, 28, 18, 0, tzinfo=UTC),
        )

        self.assertIsNotNone(winner)
        self.assertEqual("mac", winner.worker)
        self.assertEqual("mac-1", winner.lease_id)

    def test_claim_tie_breaks_on_lowest_comment_id(self) -> None:
        item = make_item()
        claim_a = qc.render_claim_comment(
            item,
            worker="mac",
            lease_id="mac-1",
            claimed_at="2026-05-28T17:52:28Z",
            expires_at="2026-05-28T19:22:28Z",
        )
        claim_b = qc.render_claim_comment(
            item,
            worker="ubuntu",
            lease_id="ubuntu-1",
            claimed_at="2026-05-28T17:52:28Z",
            expires_at="2026-05-28T19:22:28Z",
        )

        winner = qc.choose_winning_claim(
            [comment(200, claim_a), comment(199, claim_b)],
            queue_key=item.queue_key,
            now=datetime(2026, 5, 28, 18, 0, tzinfo=UTC),
        )

        self.assertIsNotNone(winner)
        self.assertEqual("ubuntu", winner.worker)

    def test_expired_claim_with_valid_heartbeat_stays_active(self) -> None:
        item = make_item()
        claim = qc.render_claim_comment(
            item,
            worker="mac",
            lease_id="mac-1",
            claimed_at="2026-05-28T17:00:00Z",
            expires_at="2026-05-28T18:00:00Z",
        )
        heartbeat = qc.render_heartbeat_comment(
            queue_key=item.queue_key,
            worker="mac",
            lease_id="mac-1",
            heartbeat_at="2026-05-28T17:55:00Z",
            expires_at="2026-05-28T20:00:00Z",
        )

        winner = qc.choose_winning_claim(
            [comment(100, claim), comment(110, heartbeat)],
            queue_key=item.queue_key,
            now=datetime(2026, 5, 28, 18, 30, tzinfo=UTC),
        )

        self.assertIsNotNone(winner)
        self.assertEqual("mac-1", winner.lease_id)

    def test_expired_claim_without_heartbeat_has_no_winner(self) -> None:
        item = make_item()
        claim = qc.render_claim_comment(
            item,
            worker="mac",
            lease_id="mac-1",
            claimed_at="2026-05-28T17:00:00Z",
            expires_at="2026-05-28T18:00:00Z",
        )

        winner = qc.choose_winning_claim(
            [comment(100, claim)],
            queue_key=item.queue_key,
            now=datetime(2026, 5, 28, 18, 30, tzinfo=UTC),
        )

        self.assertIsNone(winner)

    def test_current_head_formal_review_matches_reviewer_state_and_commit(self) -> None:
        review = qc.current_head_formal_review(
            [
                {"user": {"login": "poom"}, "state": "APPROVED", "commit_id": "old"},
                {"user": {"login": "other"}, "state": "APPROVED", "commit_id": "abc123456789"},
                {"user": {"login": "poom"}, "state": "COMMENTED", "commit_id": "abc123456789"},
                {"user": {"login": "poom"}, "state": "CHANGES_REQUESTED", "commit_id": "abc123456789", "id": 55},
            ],
            reviewer="poom",
            head_sha="abc123456789",
        )

        self.assertIsNotNone(review)
        self.assertEqual(55, review["id"])

    def test_classifies_stale_and_already_reviewed(self) -> None:
        item = make_item()

        stale = qc.classify_pr_for_queue(item, {"state": "OPEN", "headRefOid": "newsha"}, [], reviewer="poom")
        self.assertEqual("stale", stale.status)

        reviewed = qc.classify_pr_for_queue(
            item,
            {"state": "OPEN", "headRefOid": item.head_sha},
            [{"user": {"login": "poom"}, "state": "APPROVED", "commit_id": item.head_sha, "id": 88}],
            reviewer="poom",
        )
        self.assertEqual("already-reviewed", reviewed.status)
        self.assertFalse(reviewed.should_review)

    def test_classifies_pending_when_aggregate_approved_but_not_by_reviewer(self) -> None:
        item = make_item()
        classification = qc.classify_pr_for_queue(
            item,
            {"state": "OPEN", "headRefOid": item.head_sha, "reviewDecision": "APPROVED"},
            [{"user": {"login": "another-reviewer"}, "state": "APPROVED", "commit_id": item.head_sha}],
            reviewer="poom",
        )

        self.assertEqual("pending", classification.status)
        self.assertTrue(classification.should_review)

    def test_stale_result_labels_are_board_visible(self) -> None:
        remove, add, close_reason = qc.result_labels("stale")

        self.assertEqual(["hermes:queued", "hermes:claimed"], remove)
        self.assertEqual(["hermes:stale", "hermes:superseded", "result:skipped"], add)
        self.assertEqual("not planned", close_reason)


if __name__ == "__main__":
    unittest.main()
