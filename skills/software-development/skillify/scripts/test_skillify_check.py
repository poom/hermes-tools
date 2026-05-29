#!/usr/bin/env python3
"""Unit tests for the skill gate checker."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("skillify_check.py")
SPEC = importlib.util.spec_from_file_location("skillify_check", SCRIPT_PATH)
skillify_check = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = skillify_check
SPEC.loader.exec_module(skillify_check)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_passing_skill(root: Path) -> Path:
    skill = root / "sample-skill"
    write(
        skill / "SKILL.md",
        """---
name: sample-skill
description: Use when validating sample skill promotion readiness. Triggered by requests to create, promote, or audit this sample skill against the gate checklist.
required-skills: []
required-binaries:
  - python3
---

# Sample Skill

## Protocol

Follow the contract and failure rules. See [details](references/details.md). Run `scripts/do_work.py`.
""",
    )
    write(skill / "agents" / "openai.yaml", "interface:\n  display_name: Sample Skill\n")
    write(skill / "references" / "details.md", "# Details\n\nDurable reference.\n")
    write(skill / "scripts" / "do_work.py", "def main():\n    return 1\n")
    write(skill / "scripts" / "test_do_work.py", "import do_work\n\ndef test_main():\n    assert do_work.main() == 1\n")
    write(
        skill / "04-integration-tests" / "test_live_integration.py",
        "# INTEGRATION_TEST skip when credentials are absent\n# command: python3 scripts/do_work.py\n",
    )
    write(
        skill / "05-llm-evals" / "sample_llm_judge.py",
        "# judge rubric golden expected semantic classification cases\n",
    )
    write(
        skill / "07-resolver-evals" / "test_resolver_trigger.py",
        "# should trigger: routes to this skill\n# should not trigger: unrelated prompt\n",
    )
    write(
        skill / "09-e2e-smoke" / "e2e_smoke.md",
        "# E2E smoke test\n\nCommand: python3 scripts/do_work.py\n",
    )
    return skill


class SkillGateTests(unittest.TestCase):
    def test_passing_skill_passes_all_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill = make_passing_skill(Path(tmpdir))
            results = skillify_check.evaluate(skill)
            failures = [result for result in results if result.status == "FAIL"]
            self.assertEqual([], failures)

    def test_missing_unit_test_fails_gate_three(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill = make_passing_skill(Path(tmpdir))
            (skill / "scripts" / "test_do_work.py").unlink()
            results = skillify_check.evaluate(skill)
            gate_three = next(result for result in results if result.gate == 3)
            self.assertEqual("FAIL", gate_three.status)
            self.assertIn("scripts/do_work.py", gate_three.evidence[0])

    def test_top_level_report_fails_filing_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill = make_passing_skill(Path(tmpdir))
            write(skill / "skill-compliance-report.md", "# Report\n")
            results = skillify_check.evaluate(skill)
            gate_ten = next(result for result in results if result.gate == 10)
            self.assertEqual("FAIL", gate_ten.status)

    def test_top_level_readme_and_changelog_pass_filing_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill = make_passing_skill(Path(tmpdir))
            write(skill / "README.md", "# Sample Skill\n\nDurable readme.\n")
            write(skill / "CHANGELOG.md", "# Changelog\n\n## 0.1.0\n- Initial release.\n")
            results = skillify_check.evaluate(skill)
            gate_ten = next(result for result in results if result.gate == 10)
            self.assertEqual("PASS", gate_ten.status)

    def test_numbered_framework_folder_is_required_for_integration_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill = make_passing_skill(Path(tmpdir))
            integration_file = skill / "04-integration-tests" / "test_live_integration.py"
            integration_file.unlink()
            write(
                skill / "evals" / "test_live_integration.py",
                "# INTEGRATION_TEST legacy evals folder should not satisfy G4\n",
            )
            results = skillify_check.evaluate(skill)
            gate_four = next(result for result in results if result.gate == 4)
            self.assertEqual("FAIL", gate_four.status)

    def test_resolver_metadata_is_required_for_resolver_trigger_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill = make_passing_skill(Path(tmpdir))
            (skill / "agents" / "openai.yaml").unlink()

            results = skillify_check.evaluate(skill)
            gate_six = next(result for result in results if result.gate == 6)

            self.assertEqual("FAIL", gate_six.status)

    def test_release_please_version_frontmatter_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill = make_passing_skill(Path(tmpdir))
            skill_md = skill / "SKILL.md"
            skill_md.write_text(
                skill_md.read_text(encoding="utf-8").replace(
                    "description:",
                    "version: 0.1.0 # x-release-please-version\ndescription:",
                    1,
                ),
                encoding="utf-8",
            )
            results = skillify_check.evaluate(skill)
            gate_one = next(result for result in results if result.gate == 1)
            self.assertEqual("PASS", gate_one.status)

    def test_catalog_schema_failures_fail_gate_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            skill = make_passing_skill(root)
            skill_md = skill / "SKILL.md"
            skill_md.write_text(
                """---
name: sample-skill
description: Use when validating sample skill promotion readiness. Triggered by requests to create, promote, or audit this sample skill against the gate checklist.
required-skills:
  - missing-skill
required-binaries:
  - bad binary
---

# Sample Skill

## Protocol

Follow the contract and failure rules.
""",
                encoding="utf-8",
            )

            results = skillify_check.evaluate(skill)
            gate_one = next(result for result in results if result.gate == 1)

            self.assertEqual("FAIL", gate_one.status)
            self.assertIn("required_skills_unknown=missing-skill", gate_one.evidence)
            self.assertIn("invalid_required-binaries_entry=bad binary", gate_one.evidence)


if __name__ == "__main__":
    unittest.main()
