#!/usr/bin/env python3
import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).with_name("rmux_claude_interactive_reviewer.py")
spec = importlib.util.spec_from_file_location("rmux_claude_interactive_reviewer", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class RmuxClaudeInteractiveReviewerTest(unittest.TestCase):
    def test_clean_screen_strips_ansi_carriage_returns_and_trailing_spaces(self):
        raw = "\x1b[31mred\x1b[0m  \r\nnext   "
        self.assertEqual(mod.clean_screen(raw), "red\nnext")

    def test_shell_quote_handles_spaces_and_quotes(self):
        quoted = mod.shell_quote("path with ' quote")
        self.assertIn("path with", quoted)
        self.assertNotEqual(quoted, "path with ' quote")

    def test_default_sentinel_is_plain_text(self):
        self.assertIn("HERMESCLAUDEREVIEWDONE", mod.DEFAULT_SENTINEL)
        self.assertNotIn("_", mod.DEFAULT_SENTINEL)

    def test_detects_idle_claude_startup_prompt(self):
        text = '❯ Try "create a util logging.py that..."\n  gh auth login · ← for agents'
        self.assertTrue(mod.looks_like_idle_startup_prompt(text))

    def test_idle_prompt_detector_ignores_assistant_output(self):
        text = '⏺ Reviewing the PR\n❯ Try "create a util logging.py that..."\n  gh auth login'
        self.assertFalse(mod.looks_like_idle_startup_prompt(text))


if __name__ == "__main__":
    unittest.main()
