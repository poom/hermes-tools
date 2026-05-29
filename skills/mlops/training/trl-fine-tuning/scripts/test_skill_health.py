from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import skill_health


class SkillHealthTest(unittest.TestCase):
    def test_missing_skill_md_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIn('SKILL.md is missing', skill_health.check_skill(Path(tmp)))

    def test_minimal_valid_fixture_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for directory in skill_health.REQUIRED_DIRS:
                (root / directory).mkdir()
            (root / 'references' / 'guide.md').write_text('# Guide\n', encoding='utf-8')
            (root / 'SKILL.md').write_text('---\nname: trl-fine-tuning\n---\n# Skill\n[Guide](references/guide.md)\n', encoding='utf-8')
            self.assertEqual([], skill_health.check_skill(root))


if __name__ == '__main__':
    unittest.main()
