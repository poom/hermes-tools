#!/usr/bin/env python3
import importlib.util
import os
import pathlib
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).with_name("linear_ticket_context.py")
spec = importlib.util.spec_from_file_location("linear_ticket_context", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class LinearTicketContextTest(unittest.TestCase):
    def test_render_markdown_includes_core_fields_comments_and_github_attachments(self):
        issue = {
            "identifier": "DEV-123",
            "title": "Add guardrail",
            "url": "https://linear.app/finn/issue/DEV-123",
            "state": {"name": "In Progress"},
            "assignee": {"displayName": "Poom"},
            "labels": [{"name": "backend"}, "review"],
            "branchName": "poom/dev-123",
            "description": "Acceptance criteria here",
            "comments": [{"user": {"name": "Alice"}, "createdAt": "2026-01-01", "body": "Looks good"}],
            "attachments": [{"sourceType": "github", "title": "PR #1", "url": "https://github.com/org/repo/pull/1"}],
        }

        rendered = mod.render_markdown(issue)

        self.assertIn("# DEV-123: Add guardrail", rendered)
        self.assertIn("State: In Progress", rendered)
        self.assertIn("Assignee: Poom", rendered)
        self.assertIn("Labels: backend, review", rendered)
        self.assertIn("## Description", rendered)
        self.assertIn("Acceptance criteria here", rendered)
        self.assertIn("### Alice 2026-01-01", rendered)
        self.assertIn("- PR #1: https://github.com/org/repo/pull/1", rendered)

    def test_load_dotenv_preserves_existing_env_and_parses_quotes(self):
        with tempfile.TemporaryDirectory() as td:
            env_path = pathlib.Path(td) / ".env"
            env_path.write_text("EXISTING=from-file\nNEW_VALUE='quoted value'\n# ignored\n", encoding="utf-8")
            old_home = os.environ.get("HERMES_HOME")
            old_existing = os.environ.get("EXISTING")
            old_new = os.environ.pop("NEW_VALUE", None)
            os.environ["HERMES_HOME"] = td
            os.environ["EXISTING"] = "from-env"
            try:
                mod.load_dotenv()
                self.assertEqual(os.environ["EXISTING"], "from-env")
                self.assertEqual(os.environ["NEW_VALUE"], "quoted value")
            finally:
                if old_home is None:
                    os.environ.pop("HERMES_HOME", None)
                else:
                    os.environ["HERMES_HOME"] = old_home
                if old_existing is None:
                    os.environ.pop("EXISTING", None)
                else:
                    os.environ["EXISTING"] = old_existing
                if old_new is None:
                    os.environ.pop("NEW_VALUE", None)
                else:
                    os.environ["NEW_VALUE"] = old_new


if __name__ == "__main__":
    unittest.main()
