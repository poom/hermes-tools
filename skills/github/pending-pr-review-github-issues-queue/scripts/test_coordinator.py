#!/usr/bin/env python3
from __future__ import annotations

import unittest

import coordinator


class CoordinatorTest(unittest.TestCase):
    def test_normalizes_stats_json_payload(self) -> None:
        payload = {
            "prs": [
                {
                    "repository": {"nameWithOwner": "EWA-Services/finn-web-app"},
                    "number": 4974,
                    "url": "https://github.com/EWA-Services/finn-web-app/pull/4974",
                }
            ],
            "filter_stats": {"dropped_by_local_filter": 0},
        }

        prs = coordinator.normalize_discovery_payload(payload)

        self.assertEqual(1, len(prs))
        self.assertEqual(4974, prs[0]["number"])

    def test_normalizes_array_payload(self) -> None:
        payload = [
            {"repository": {"nameWithOwner": "EWA-Services/tools"}, "number": 133},
            "not a pr",
        ]

        prs = coordinator.normalize_discovery_payload(payload)

        self.assertEqual([{"repository": {"nameWithOwner": "EWA-Services/tools"}, "number": 133}], prs)

    def test_rejects_unknown_discovery_shape(self) -> None:
        with self.assertRaises(ValueError):
            coordinator.normalize_discovery_payload({"items": []})


if __name__ == "__main__":
    unittest.main()
