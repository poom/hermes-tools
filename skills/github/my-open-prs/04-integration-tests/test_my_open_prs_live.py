#!/usr/bin/env python3
"""Live integration test for my-open-prs.

Skips unless MY_OPEN_PRS_LIVE=1 is set. Requires gh authentication and network.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import my_open_prs


@unittest.skipUnless(os.getenv("MY_OPEN_PRS_LIVE") == "1", "set MY_OPEN_PRS_LIVE=1 to run live GitHub check")
class MyOpenPrsLiveTest(unittest.TestCase):
    def test_default_query_returns_classifiable_payload(self) -> None:
        payload = my_open_prs.run_gh(my_open_prs.DEFAULT_QUERY)
        nodes = my_open_prs.extract_nodes(payload)

        self.assertIsInstance(nodes, list)
        for node in nodes[:10]:
            entry = my_open_prs.classify(node)
            self.assertIn(entry.bucket, {"Waiting on Review", "Waiting on Checks / Merge", "Needs My Feedback"})
            self.assertTrue(entry.url.startswith("https://github.com/"))


if __name__ == "__main__":
    unittest.main()
