# Gate examples

Concrete, copyable templates for each of the 10 gates. Pair with the sibling reference `patterns.md` (types × variable gates) when designing a new skill.

The examples lean on a representative shape — typically a Mutation skill that posts to Google Chat — to keep the templates concrete. Variations per type are noted inline; deeper detail lives in `patterns.md`.

## G1 SKILL.md contract

A passing `SKILL.md` has trigger-rich frontmatter and a body that states rules, workflow, and failure behaviour. No leftover placeholder markers.

```markdown
---
name: post-chat-message
description: Use when posting messages to Google Chat spaces, sending updates to chat threads, DMing users, replying in a thread, or reacting in Chat. Triggered by "post to chat", "send a chat message", "DM <person>", "@-mention in <space>", "Chat reply".
required-skills:
  - google-chat
required-binaries:
  - gog
  - python3
---

# Post Chat Message

## Protocol

1. Resolve the target space ID from the request — never use a name without a numeric ID lookup.
2. De-dup against the past 60 seconds of messages in that space (by content hash).
3. Post via `scripts/post_to_chat.py`. Capture the returned message ID.

## Failure behavior

- If credentials are missing → exit non-zero with the env-var name that's missing. Never prompt.
- If the target looks like a production space → refuse without the `--confirm-production` flag.

## Scripts

- `scripts/post_to_chat.py` — idempotent message poster.
```

Common failure modes:
- `description_too_short` — fewer than ~80 characters; resolver can't disambiguate. Fix: add 3+ trigger phrases the user will actually say.
- `name_mismatch` — frontmatter `name` doesn't equal the folder name. Fix: align them.
- `missing_dependency_metadata` — `required-skills` or `required-binaries` absent. Fix: list normal-workflow dependencies, or use `[]` when none.
- `unknown_required_skill` — `required-skills` names a missing sibling skill. Fix: add the dependency skill or remove the dependency.
- `placeholder_present` — `<TODO>` / `<FIXME>` / `your-skill-name` markers left behind. Fix: replace with real values.

## G2 Deterministic code

A passing `scripts/` directory keeps repeated or fragile work in importable, testable code — not LLM prose inside `SKILL.md`.

```python
# scripts/post_to_chat.py
"""Post a message to a Google Chat space.

Idempotent: deduplicates on (space_id, content hash) within the past 60 seconds.
"""

from __future__ import annotations

import argparse
import hashlib

from gog import GoogleChatClient


def post_message(client: GoogleChatClient, space_id: str, body: str) -> str:
    """Post and return the message ID. Returns the existing ID if a duplicate
    was posted in the past 60 seconds."""
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
    existing = client.find_recent(space_id, digest, window_seconds=60)
    if existing:
        return existing.message_id
    return client.post(space_id=space_id, body=body, dedup_key=digest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--space-id", required=True)
    parser.add_argument("--body", required=True)
    args = parser.parse_args()
    client = GoogleChatClient.from_env()
    print(post_message(client, args.space_id, args.body))


if __name__ == "__main__":
    main()
```

Key shape per type (see `patterns.md` for the full matrix):
- **Mutation**: API client + payload builder + idempotent write helper.
- **Periodic report**: dump script + render script + send script — one each.
- **Synthesis**: fetcher + transformer + formatter.
- **Review**: rule checker + decision logic.
- **Tool guide**: no wrapper code; ship a verified command vocabulary instead.

## G3 Unit tests

Every non-test script has a matching offline test. No network, no credentials, no live endpoints. Tests import the module rather than running it as a subprocess so individual functions are exercised.

```python
# scripts/test_post_to_chat.py
import unittest
from unittest.mock import MagicMock

import post_to_chat


class PostMessageTest(unittest.TestCase):
    def test_returns_existing_id_on_duplicate(self) -> None:
        client = MagicMock()
        client.find_recent.return_value = MagicMock(message_id="msg-existing")
        result = post_to_chat.post_message(client, "space-1", "hello")
        self.assertEqual("msg-existing", result)
        client.post.assert_not_called()

    def test_posts_when_no_duplicate(self) -> None:
        client = MagicMock()
        client.find_recent.return_value = None
        client.post.return_value = "msg-new"
        result = post_to_chat.post_message(client, "space-1", "hello")
        self.assertEqual("msg-new", result)
        client.post.assert_called_once()


if __name__ == "__main__":
    unittest.main()
```

Common failure modes:
- Tests that import `requests` or open network sockets — these are integration tests, not unit tests. Move them to `04-integration-tests/`.
- Tests that read live credentials — same, move them.
- A script with no matching test file — add `test_<script>.py` next to it.

## G4 Integration tests

Live behavior has an explicit harness with a clear command and credential-skip behavior. The shape varies by type — see `patterns.md`:

**Mutation** — sandbox + read-back diff:

```python
# 04-integration-tests/test_post_to_chat_live.py
"""Live integration test for post_to_chat. Skips without credentials."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


@unittest.skipUnless(
    os.getenv("SCRATCH_CHAT_SPACE_ID"),
    "set SCRATCH_CHAT_SPACE_ID to the scratch test space id to run",
)
class PostToChatLiveTest(unittest.TestCase):
    def test_post_then_readback(self) -> None:
        from post_to_chat import post_message
        from gog import GoogleChatClient

        space = os.environ["SCRATCH_CHAT_SPACE_ID"]
        if "production" in space.lower() or space in PRODUCTION_SPACE_IDS:
            self.fail("refusing to run against a production space")

        client = GoogleChatClient.from_env()
        msg_id = post_message(client, space, body="integration smoke")
        readback = client.get_message(space, msg_id)
        self.assertEqual("integration smoke", readback.body)


PRODUCTION_SPACE_IDS = {"spaces/AAAA...", "spaces/BBBB..."}

if __name__ == "__main__":
    unittest.main()
```

**Periodic report** — five-phase orchestration: validate scratch targets → snapshot inputs → run runner → read back → run validators. Each phase fails independently and writes durable evidence.

**Synthesis** — fixture replay against a golden output diff. Live mode hits real read APIs and asserts schema only.

**Review** — should-pass / should-fail corpus of fixture artifacts. The skill verdicts are diffed against expected.

**Tool guide** — verification script that executes every documented command against the real tool (no-op mode where possible) and asserts non-error response. Catches doc drift when the tool changes flags.

Common failure modes:
- No skip behavior — test fails hard without credentials. Always `@unittest.skipUnless(env_var)`.
- Writes to production — must refuse production target IDs explicitly; never trust the env var alone.
- No read-back — test posts but never verifies the write reached the system.

## G5 LLM evals

Required when the skill has at least one LLM-owned step (classification, routing, drafting, comparison). One judge file per LLM step, not per skill. The canonical pattern lives in the sibling reference `patterns.md` under "G5 LLM judge" — eligibility, file layout, CLI shape (`--live` and `--from`), required components.

Skeleton:

```text
05-llm-evals/
  golden_cases.json                     # input + expected output per case
  <step-name>_llm_judge.py              # one per LLM step
  <step-name>_llm_judge.md              # rubric documentation
  test_<step-name>_llm_judge.py         # offline tests for the judge
```

The `--rubric` flag points at the **same source the production runner reads** — typically a cron prompt at `references/<step>-cron.md`. If they diverge, the judge stops catching prompt drift.

Common failure modes:
- Rubric inlined in judge code instead of read from production source. Fix: extract the rubric section from the production prompt.
- One judge file covering two LLM steps. Fix: split into two.
- Golden cases missing a regression case for a real production miss. Fix: add the case the moment a miss happens.

## G6 Resolver trigger

Trigger-rich `description` plus runtime metadata where the runtime needs it.

Frontmatter (covered by G1, repeated here for the resolver lens):

```yaml
---
name: post-chat-message
description: Use when posting messages to Google Chat spaces, sending updates to chat threads, DMing users, replying in a thread, or reacting in Chat. Triggered by "post to chat", "send a chat message", "DM <person>", "@-mention in <space>", "Chat reply".
required-skills:
  - google-chat
required-binaries:
  - gog
  - python3
---
```

Runtime metadata for OpenAI runtime:

```yaml
# agents/openai.yaml
interface:
  display_name: "Post Chat Message"
  short_description: "Post messages to Google Chat spaces with idempotent dedup"
  default_prompt: "Post this message to <space>: <text>"
```

Common failure modes:
- Description is generic ("Use this skill for chat operations"). Fix: include verbs the user types and nouns that distinguish from siblings.
- Description duplicates a sibling skill's description. Fix: lean on the verbs that differ (read vs. write, schedule vs. send, etc.).
- Runtime metadata missing for a runtime that requires it. Fix: add `agents/openai.yaml` (or equivalent).

## G7 Resolver eval

Should-trigger and should-not-trigger prompts that distinguish this skill from siblings. The "should not" cases are the more important half — they prove the resolver doesn't over-fire.

```markdown
# Resolver Eval

These prompts should trigger `post-chat-message`:

- "Send a Chat message to the eng-leads space."
- "DM @<name> on Google Chat."
- "Post this update in our team's Chat thread."
- "Reply to that Chat thread with the deploy status."
- "React with thumbs-up to the message in #incidents."

These prompts should not trigger it:

- "Send an email to the team." (different channel — use the email skill)
- "Post to Slack." (different platform — separate skill)
- "Schedule a meeting in the eng-leads space." (calendar, not Chat)
- "Pull the last 10 messages from the space." (read, not write — use the chat-read skill)
- "Set up a new Chat space." (admin operation, not message posting)
```

Common failure modes:
- Should-not-trigger list is empty or generic. Fix: include 3+ near-miss siblings — same domain, different verb or platform.
- Should-trigger covers only one phrasing. Fix: include 4+ phrasings the user might actually say.

## G8 Resolvable / DRY audit

Markdown links resolve, every reference is mentioned by a durable doc, every script is mentioned, no duplicated source of truth.

Checker output when something fails:

```text
G8 Resolvable and DRY audit: FAIL
  missing_links=1; unreferenced_references=1; unmentioned_scripts=1; duplicate_headings=1
  missing link: references/usage.md
  unreferenced ref: references/old_notes.md
  unmentioned script: scripts/helper.py
  duplicate: ## Workflow
```

Failure → fix:

| Failure | Cause | Fix |
|---|---|---|
| `missing_link: references/usage.md` | `SKILL.md` links to a file that doesn't exist | Create the file, or remove/correct the link. |
| `unreferenced_reference: references/old_notes.md` | A file in `references/` is not mentioned by `SKILL.md` or another durable doc | Link from `SKILL.md`, or delete the orphan. |
| `unmentioned_script: scripts/helper.py` | Script in `scripts/` is not referenced anywhere | Add it under the `## Scripts` section in `SKILL.md`. |
| `duplicate_heading: ## Workflow` | Same heading used in two durable docs | Rename one to be specific (`## Daily workflow`, `## Backfill workflow`). |

Common failure modes:
- Two reference files describing the same thing. Fix: merge or delete the loser. Skillify's contract: one canonical source per concept.
- A reference file linked from an evidence file under `04-integration-tests/` but not from SKILL.md. Fix: link from SKILL.md too — evidence files are durable but secondary.

## G9 E2E smoke test

One documented command that exercises the same path the runtime uses, with three tiers (offline / structural / live). Each tier records durable evidence under ignored `tmp/`.

```markdown
# E2E Smoke

## Tier 1 — Offline (always safe)

Runs every unit test and offline judge replay. No env vars required.

```bash
python3 -m unittest discover scripts
python3 -m unittest discover 05-llm-evals
```

Pass: all green.

## Tier 2 — Structural (real reads, scratch writes only)

Reads from production sources, writes to scratch outputs. Refuses production output IDs.

```bash
python3 04-integration-tests/run_report.py \
  --output-sheet "$SCRATCH_OUTPUT_SHEET_ID" \
  --confirm-scratch-write
```

Pass: scratch sheet receives the rebuilt tabs; `tmp/04-integration-tests/<run-id>/` contains stdout, stderr, and read-back artifacts.

## Tier 3 — Live (full path)

Runs the production runner end-to-end against scratch outputs. Requires explicit confirmation.

```bash
python3 scripts/runner.py \
  --output-sheet "$SCRATCH_OUTPUT_SHEET_ID" \
  --confirm-live-read-scratch-write
```

Pass: same as Tier 2, plus a PASS line and run-id printed on stdout.
```

Common failure modes:
- Tier 1 needs credentials. Fix: split — offline tier must run with zero env.
- Smoke command exists but doesn't match the runtime path. Fix: invoke the production runner as a subprocess; don't reimplement.
- Smoke writes to production. Fix: add a hard refusal on production IDs; never trust env vars alone.

## G10 Filing rules

Durable artifacts live in the skill folder; scratch under ignored `tmp/`; no rogue scratch reports at the top level. Standard `README.md`, `CHANGELOG.md`, `LICENSE`, and `CONTRIBUTING.md` are allowed.

Folder shape:

```text
my-skill/
├── SKILL.md
├── README.md                    # OK — durable
├── CHANGELOG.md                 # OK — durable, release-please-managed
├── 04-integration-tests/
├── 05-llm-evals/
│   ├── golden_cases.json
│   └── my_skill_llm_judge.py
├── 07-resolver-evals/
├── 09-e2e-smoke/
├── agents/
│   └── openai.yaml
├── references/
│   ├── patterns.md
│   └── gate-examples.md
├── scripts/
│   ├── runner.py
│   └── test_runner.py
├── tmp/                         # gitignored — scratch evidence
└── .gitignore                   # contains: tmp/
```

`.gitignore`:

```text
tmp/
```

Common failure modes:
- `compliance-report.md` or `quick-reference.md` at the skill root. Fix: move durable content into `SKILL.md`/`references/`; delete the scratch dump.
- `tmp/` exists but isn't in `.gitignore`. Fix: add it.
- An evidence artifact (run log, JSON capture) committed at the skill root. Fix: move it under `tmp/` and gitignore.
