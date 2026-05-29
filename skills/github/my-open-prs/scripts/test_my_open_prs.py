#!/usr/bin/env python3
"""Offline unit tests for my_open_prs."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import my_open_prs


def make_pr(**overrides):
    pr = {
        "number": 12,
        "title": "Improve checkout",
        "url": "https://github.com/EWA-Services/web/pull/12",
        "state": "OPEN",
        "merged": False,
        "createdAt": "2026-05-17T00:00:00Z",
        "updatedAt": "2026-05-18T00:00:00Z",
        "closedAt": None,
        "mergedAt": None,
        "reviewDecision": "REVIEW_REQUIRED",
        "mergeStateStatus": "CLEAN",
        "repository": {"name": "web", "nameWithOwner": "EWA-Services/web"},
        "reviewRequests": {"nodes": []},
        "latestReviews": {"nodes": []},
        "statusCheckRollup": {"state": "SUCCESS", "contexts": {"nodes": []}},
    }
    pr.update(overrides)
    return pr


class MyOpenPrsTest(unittest.TestCase):
    def test_classifies_clean_review_required_as_waiting_on_review(self) -> None:
        entry = my_open_prs.classify(
            make_pr(
                reviewRequests={
                    "nodes": [{"requestedReviewer": {"__typename": "User", "login": "alice"}}]
                }
            )
        )

        self.assertEqual("Waiting on Review", entry.bucket)
        self.assertEqual("waiting for review from @alice", entry.summary)
        self.assertEqual("EWA-Services/web", entry.repo_full)

    def test_classifies_blocked_approved_with_review_request_as_waiting_on_review(self) -> None:
        entry = my_open_prs.classify(
            make_pr(
                reviewDecision="APPROVED",
                mergeStateStatus="BLOCKED",
                reviewRequests={
                    "nodes": [{"requestedReviewer": {"__typename": "User", "login": "faiq-ewa"}}]
                },
                statusCheckRollup={
                    "state": "PENDING",
                    "contexts": {
                        "nodes": [
                            {
                                "__typename": "StatusContext",
                                "context": "policy-bot: main",
                                "state": "PENDING",
                            }
                        ]
                    },
                },
            )
        )

        self.assertEqual("Waiting on Review", entry.bucket)
        self.assertEqual("waiting for review from @faiq-ewa", entry.summary)

    def test_classifies_changes_requested_and_dedupes_checks(self) -> None:
        entry = my_open_prs.classify(
            make_pr(
                reviewDecision="CHANGES_REQUESTED",
                mergeStateStatus="BLOCKED",
                latestReviews={
                    "nodes": [
                        {"state": "CHANGES_REQUESTED", "author": {"login": "jai"}},
                        {"state": "CHANGES_REQUESTED", "author": {"login": "jai"}},
                    ]
                },
                statusCheckRollup={
                    "state": "FAILURE",
                    "contexts": {
                        "nodes": [
                            {
                                "__typename": "CheckRun",
                                "name": "policy-bot",
                                "status": "COMPLETED",
                                "conclusion": "FAILURE",
                            },
                            {
                                "__typename": "CheckRun",
                                "name": "policy-bot",
                                "status": "COMPLETED",
                                "conclusion": "FAILURE",
                            },
                        ]
                    },
                },
            )
        )

        self.assertEqual("Needs My Feedback", entry.bucket)
        self.assertIn("changes requested by @jai", entry.summary)
        self.assertIn("failing checks: policy-bot", entry.summary)
        self.assertEqual(1, entry.summary.count("policy-bot"))

    def test_uses_rollup_fallback_when_contexts_are_missing(self) -> None:
        entry = my_open_prs.classify(
            make_pr(
                reviewDecision="APPROVED",
                statusCheckRollup={"state": "FAILURE", "contexts": {"nodes": []}},
            )
        )

        self.assertEqual("Needs My Feedback", entry.bucket)
        self.assertIn("failing checks: status checks", entry.summary)

    def test_render_omits_empty_sections_by_default(self) -> None:
        entry = my_open_prs.classify(make_pr())
        rendered = my_open_prs.render_markdown([entry], include_empty=False)

        self.assertIn("## Waiting on Review", rendered)
        self.assertNotIn("## Needs My Feedback", rendered)

    def test_actions_create_channel_and_record_channel(self) -> None:
        entry = my_open_prs.classify(make_pr())
        with tempfile.TemporaryDirectory() as td:
            status_dir = Path(td)
            result = my_open_prs.update_status_and_actions(
                [entry],
                status_dir,
                parent_target="discord:forum",
                fetch_closed=False,
                observed_at="2026-05-18T01:00:00Z",
            )
            self.assertEqual(1, len(result["actions"]))
            action = result["actions"][0]
            self.assertEqual("create_channel", action["type"])
            self.assertEqual("discord:forum", action["target"])
            self.assertEqual("web-pr-12", action["channel_name"])
            self.assertEqual("web #12 Improve checkout", action["topic_title"])
            self.assertIn("web #12 Improve checkout", action["message"])

            rec = my_open_prs.update_record_posted(
                status_dir,
                "EWA-Services/web",
                12,
                signature=action["signature"],
                channel_id="12345",
                message_id="67890",
                posted_at="2026-05-18T01:01:00Z",
            )
            self.assertEqual("12345", rec.channel_id)
            self.assertEqual(action["signature"], rec.last_posted_signature)

            repeat = my_open_prs.update_status_and_actions(
                [entry],
                status_dir,
                parent_target="discord:forum",
                fetch_closed=False,
                observed_at="2026-05-18T02:00:00Z",
            )
            self.assertEqual([], repeat["actions"])

    def test_actions_post_update_when_blocker_changes(self) -> None:
        entry = my_open_prs.classify(make_pr())
        changed = my_open_prs.classify(
            make_pr(
                reviewDecision="CHANGES_REQUESTED",
                latestReviews={"nodes": [{"state": "CHANGES_REQUESTED", "author": {"login": "sam"}}]},
            )
        )
        with tempfile.TemporaryDirectory() as td:
            status_dir = Path(td)
            first = my_open_prs.update_status_and_actions([entry], status_dir, parent_target="discord:forum", fetch_closed=False)
            action = first["actions"][0]
            my_open_prs.update_record_posted(status_dir, "EWA-Services/web", 12, signature=action["signature"], channel_id="12345")

            second = my_open_prs.update_status_and_actions([changed], status_dir, parent_target="discord:forum", fetch_closed=False)
            self.assertEqual(1, len(second["actions"]))
            self.assertEqual("post_update", second["actions"][0]["type"])

    def test_github_activity_only_change_does_not_post_duplicate_update(self) -> None:
        entry = my_open_prs.classify(make_pr(updatedAt="2026-05-18T00:00:00Z"))
        only_activity_changed = my_open_prs.classify(make_pr(updatedAt="2026-05-18T01:00:00Z"))
        with tempfile.TemporaryDirectory() as td:
            status_dir = Path(td)
            first = my_open_prs.update_status_and_actions([entry], status_dir, parent_target="discord:forum", fetch_closed=False)
            action = first["actions"][0]
            my_open_prs.update_record_posted(status_dir, "EWA-Services/web", 12, signature=action["signature"], channel_id="12345")

            second = my_open_prs.update_status_and_actions(
                [only_activity_changed],
                status_dir,
                parent_target="discord:forum",
                fetch_closed=False,
                observed_at="2026-05-18T01:05:00Z",
            )
            self.assertEqual([], second["actions"])

    def test_stale_ping_after_24_hours(self) -> None:
        entry = my_open_prs.classify(make_pr(updatedAt="2026-05-17T00:00:00Z"))
        with tempfile.TemporaryDirectory() as td:
            status_dir = Path(td)
            first = my_open_prs.update_status_and_actions([entry], status_dir, parent_target="discord:forum", fetch_closed=False, observed_at="2026-05-17T01:00:00Z")
            action = first["actions"][0]
            my_open_prs.update_record_posted(status_dir, "EWA-Services/web", 12, signature=action["signature"], channel_id="12345", posted_at="2026-05-17T01:01:00Z")

            stale = my_open_prs.update_status_and_actions([entry], status_dir, parent_target="discord:forum", fetch_closed=False, observed_at="2026-05-18T01:02:00Z")
            self.assertEqual(1, len(stale["actions"]))
            self.assertEqual("ping_stale", stale["actions"][0]["type"])
            self.assertIn("no GitHub activity", stale["actions"][0]["message"])

    def test_classifies_closed_pr(self) -> None:
        entry = my_open_prs.classify(
            make_pr(state="CLOSED", merged=True, mergedAt="2026-05-18T03:00:00Z", closedAt="2026-05-18T03:00:00Z")
        )
        self.assertEqual("Closed / Merged", entry.bucket)
        self.assertTrue(entry.merged)
        self.assertIn("merged", entry.summary)


if __name__ == "__main__":
    unittest.main()
