from __future__ import annotations

import unittest
from pathlib import Path


class ScriptPresenceTest(unittest.TestCase):
    def test_script_exists(self) -> None:
        self.assertTrue((Path(__file__).parent / 'google_api.py').exists())


if __name__ == '__main__':
    unittest.main()
