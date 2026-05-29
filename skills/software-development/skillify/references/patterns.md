# Skill Patterns by Type

A skill's **type** predicts what each gate looks like. Type is the *shape* of the work, not the *topic*. Two recruiting skills can have very different types if one mutates Greenhouse and the other only synthesizes a report.

This is the matrix you scan when you start a new skill: pick a type, then read across the row to see what each gate has to look like.

## Pick a type

First match wins.

| If the skill... | Type |
|---|---|
| Writes / edits state in an external SaaS (Notion page, Google Sheet row, Linear issue, Chat message) | **Mutation** |
| Reads from external systems and writes a recurring artifact on a schedule (digest, sheet update, weekly post) | **Periodic report** |
| Reads from external systems and emits an analysis or recommendation on demand | **Synthesis** |
| Looks at an existing artifact (PR, doc, roadmap, runbook, skill) and emits a verdict / score / issue list | **Review** |
| Generates novel structured content (slides, diagrams, drafts) from input | **Generation** |
| Documents how to drive an external CLI / desktop / browser tool so the LLM can use it | **Tool guide** |
| Manages other skills, the framework, runtime, environments, or developer plumbing | **Meta** |

## Matrix: gate × type

Six gates are uniform — same shape regardless of type — and four gates vary. Variations are listed first; uniform gates are summarised at the bottom.

### Variable gates

| Gate | Mutation | Periodic report | Synthesis | Review | Generation | Tool guide | Meta |
|---|---|---|---|---|---|---|---|
| **G2 Deterministic code** | API client, payload builder, idempotent write helper | Dump script, render script, send script — one each | Fetcher + transformer + formatter | Rule checker + decision logic | Template + assembler + format validator | Verification script in `scripts/` runs the documented command vocabulary against the real tool | Meta script that operates on other skills' files |
| **G4 Integration tests** | Sandbox doc/sheet/space + read-back diff | Five-phase: validate scratch targets → snapshot → runner → readback → validators | Fixture replay + golden output diff. Live mode hits real read APIs and asserts schema only | Should-pass / should-fail corpus of fixture artifacts | Format/render validation (Mermaid CLI parses, PPTX schema valid, etc.) | Verified-commands script: execute every documented command against the real tool (no-op mode where possible) and assert success. Skip on no creds. Catches doc drift when the underlying tool changes flags | Self-application + idempotence on a sandbox skill |
| **G5 LLM judge** | N/A unless the skill drafts content the LLM owns. Then judge tone/factuality before the deterministic write asserts the mutation landed | Required per LLM step (see eligibility below). Single judge file with `--live` and `--from`. Golden cases include real production misses | Required when synthesis is LLM-owned. Grade for factual fidelity, completeness, no hallucinated entities | Always required — the verdict *is* the judgment. False-positive checks weigh equally with true-positive | Required when the content is creative. Format check covers structural floor; judge covers semantic ceiling | Required when the documented surface has command-choice ambiguity (LLM picks between similar commands). Judge that the LLM stayed inside the documented vocabulary and used documented flags. Skip when each user intent maps unambiguously to one command | Required when the meta-skill emits judgments (e.g., gate verdicts). Single-mode judge usually enough |
| **G9 E2E smoke** | Three-tier: offline (stubbed write) / structural (sandbox sheet) / live (read-only post-write check) | Three-tier: offline (fake runner) / structural (scratch sheets via env) / live (real cron path against scratch outputs) | Three-tier: offline (fixture) / structural (real read API) / live (full report rendered) | Run skill on the test corpus and diff verdicts; live tier optional | Render the output in the target format and inspect (operator opens the deck / diagram) | Run a representative documented command against the real tool, capture stdout, attach to evidence | Run the meta-skill on a sandbox skill, verify artifacts |

### Uniform gates

These look the same regardless of type. Cells differ only in **what** is being audited, not **how**.

- **G1 SKILL.md contract** — frontmatter follows the repo schema (`name`, trigger-rich `description`, `required-skills`, `required-binaries`), folder name matches, no leftover placeholders, body states rules / workflow / failure behavior.
- **G3 Unit tests** — every non-test script in `scripts/` has a matching offline test. No network, no credentials, no live endpoints.
- **G6 Resolver trigger** — trigger-rich frontmatter description plus `agents/openai.yaml` (or runtime equivalent) when the runtime needs it.
- **G7 Resolver eval** — `07-resolver-evals/` has should-trigger and should-not-trigger prompts that distinguish the skill from siblings.
- **G8 Resolvable / DRY audit** — markdown links resolve, every reference is mentioned by a durable doc, every script is mentioned, no duplicated source of truth.
- **G10 Filing rules** — durable artifacts in the skill folder, scratch under ignored `tmp/`, no top-level scratch reports (compliance dumps, installation guides, quick-reference summaries). Standard `README.md`, `CHANGELOG.md`, `LICENSE`, and `CONTRIBUTING.md` are allowed.

## Per-type detail

The matrix is the cheat sheet. Read the type entry below when you need the *why* behind the row.

### Mutation

The skill changes durable state in an external system. Success means a write reached the system; failure means it did not, or worse, hit the wrong target.

Typical shape: posts to Linear, edits a Notion page, appends rows to a Google Sheet, sends a Chat message.

The two non-obvious decisions:

- **Sandbox is mandatory.** Use a dedicated test page / sheet / space. Never write to production from a test, even read-back-after-write tests. The sandbox lives as long as the skill does.
- **G5 is rare.** The mutation is deterministic — read-back proves the write landed. G5 only fires when the LLM also drafted the content. Then split the test: G5 grades the draft against a rubric (tone, length, factuality); G4 asserts the deterministic write reached the system.

### Periodic report

Runs on a schedule (cron, weekly review, daily digest) and emits an artifact someone consumes (Chat thread, sheet, posted update, mail). Often owns one or more LLM-classification or LLM-synthesis steps inside an otherwise deterministic pipeline.

The five-phase G4 orchestration is the model: **validate scratch targets → snapshot inputs → run runner → readback → run validators**. Each phase has its own concern, fails independently, and writes durable evidence. The runner is the production runner invoked as a subprocess (no parallel implementation) — what the cron sends is what the test sends. Inputs from external systems are snapshotted at run start so re-runs replay against the exact same data.

G4 applies to **every** report. G5 applies **per LLM step** — a report with no LLM step gets no G5; a report with two LLM steps gets two judges. See "G5 LLM judge" below for the eligibility checklist and the canonical judge shape.

### Synthesis

Reads from external systems and emits a synthesis (report, dashboard, recommendation, summary) on demand. No durable side-effects.

Typical shape: triage dashboards, headcount reviews, roadmap assessments, lab-result interpreters.

Fixture replay is enough for G4. Capture a known input snapshot (Linear export, calendar export, blood test PDF) and run the skill against it; diff the synthesis against a golden output. Live mode calls real read APIs and asserts schema-only.

G5 only when the synthesis includes LLM-owned interpretation (priority ordering, narrative, recommendations). Grade for factual fidelity to the input snapshot, completeness against a checklist, no hallucinated entities.

### Review

Looks at an existing artifact (PR, design doc, roadmap, runbook, skill) and emits a structured verdict — pass / fail, score, list of issues, approve / request-changes.

Maintain a small corpus of "should-pass" and "should-fail" examples. Run the skill, capture the verdict, diff against expected. The corpus replaces the live system entirely — these skills do not need API access for tests.

G5 is always required. The verdict *is* the LLM-owned judgment. False-positive checks (the skill must *not* fail valid artifacts) carry equal weight with true-positive checks. Many review skills are also Meta-type — that's fine, pick whichever fits the testing surface better.

### Generation

Generates novel structured content from input — slides, diagrams, drafts, scaffolds. The output has a strict format the consumer expects.

Run the generator, validate the output against the format's parser (Mermaid CLI, PPTX schema, Markdown linter). The renderability check replaces a hand-judged "is this any good?" — if it parses, the skill did not break the format. Source-data fidelity (did the slides include the right OKR list?) is asserted by deterministic field checks.

G5 is required when the content is creative (slide narrative, diagram layout choice). Judge for clarity, completeness against an outline, no hallucinated facts.

### Tool guide

Documents the surface area of an external tool (CLI, desktop app, browser, MCP server) so the LLM can drive it. The skill itself ships **no wrapper code** — it ships a verified command vocabulary that the LLM reads and uses.

The G4 contract is **every documented command actually works**. Ship a verification script that runs each command in the doc against the real tool (no-op mode where possible — `op whoami`, `wrangler whoami`, `gh auth status`) and asserts a non-error response. The `verified_ok:` lines in the tool reference are the source of truth: if a command is listed, it has been executed. When the underlying tool changes a flag, this script breaks before drift reaches the LLM.

G5 is **conditional on command-choice ambiguity**. If each user intent maps unambiguously to one documented command, no judge is needed — the verification script is enough. If multiple commands could apply (e.g., Wrangler's overlapping `dev`/`deploy`/`tail` surface), add a judge with golden cases of `{user_request, expected_command_template}` and grade whether the LLM stayed inside the documented vocabulary, used documented flags, and parameterized correctly.

### Meta

Skills that operate on the framework, the runtime, or other skills — skill creation, skill audit, environment harness, runtime management, workspace optimization.

Run the meta-skill on a sandbox skill / repo / workspace and verify the artifacts it produced. Re-run and verify nothing changes (idempotence). Validate against the framework rules the skill enforces.

G5 fires when the meta-skill emits judgments (e.g., a skill-quality reviewer rates other skills, `skillify` grades against 10 gates). Use the same single-judge pattern. Option-style splits — "grade-only" vs "live" — only make sense when there's an LLM call worth amortizing; for pure deterministic meta-skills the judge is just the rule checker.

## G5 LLM judge

The canonical pattern for any G5 judge, regardless of type.

### Eligibility

Add G5 only when the skill has at least one **LLM-owned step** — a place where the runtime hands data to the model and uses the model's output. Common shapes:

- **Bucketing / classification** — assign each input to a category from a fixed vocabulary (e.g., breach severity, candidate strength, alert priority).
- **Routing** — pick which of N owners gets the alert / which downstream step runs next.
- **Comparison / judgment** — does X match Y? Is this artifact ready? (review-type skills always have this).
- **Synthesis / drafting** — write the summary paragraph, draft the message body, narrate the slide.

Pure deterministic pipelines do not need G5 even if an agent is the runner — if the agent only invokes deterministic scripts, there's nothing for a judge to grade. Add G5 the moment a step's output depends on model choice.

### One judge per LLM step, not per skill

A skill with no LLM step needs no G5. A skill with two LLM steps gets two judge files. A digest report that classifies each row → one judge. If it later added an LLM-drafted summary line at the end of each thread, that would be a second LLM step and a second judge.

### Where `--rubric` points

To whatever file holds the production rules for that step. The judge must read **the same source the production runner reads** — if they diverge, the judge stops catching prompt drift.

Common sources:

- **A cron prompt** (e.g., `references/<report>-cron.md`) — the runtime hands this directly to the model.
- **A template file** loaded by a Python runner.
- **A section inside `references/<report>.md`** when the rules are short.

The judge's `extract_classification_rubric` (or equivalent) pulls the relevant section out of the source file. The rubric is never inlined in the judge code.

### File layout

```text
05-llm-evals/
  golden_cases.json
  <step-name>_llm_judge.py         # one per LLM step
  <step-name>_llm_judge.md         # rubric documentation
  test_<step-name>_llm_judge.py    # offline tests
```

### CLI shape

```text
05-llm-evals/<step-name>_llm_judge.py
  --golden <path>     # always
  --rubric <path>     # required with --live; points at the production prompt source
  --live              # call the model end-to-end
  --from <path>       # replay pre-recorded classifications
  --output <path>     # write captured output for later replay
```

`--live` and `--from` are mutually exclusive; one is required. `--live` lazy-imports the SDK, skips cleanly without API key, captures output via `--output` so a later `--from` run regrades for free.

### Required components

- `judge_<thing>(input, actual, golden) -> Verdict` — pure rubric function. Three states: `pass`, `fail`, `needs_human`.
- `golden_cases.json` — input + expected output per case. Includes a regression case for every real production miss.
- `<step-name>_llm_judge.md` — rubric documentation: pass criteria, golden case shape, when to add cases.
- `LLMClient` Protocol with `StubClient` (test) and `AnthropicClient` (live, lazy-import).
- `build_prompt(rubric_text, input)` — pulls the relevant section from the rubric file, embeds the input.
- `parse_response(text)` — extracts JSON from model output. Lenient on surface artifacts (code fences, prose wrap), strict on schema.
- Tests in `test_<step-name>_llm_judge.py`: rubric grader (every status path), prompt construction, response parsing, stub-driven runner, replay round-trip, CLI dispatch. No anthropic SDK required to run.

### Why this shape

The rubric, the prompt, and the parser are shared between modes. `--live` captures, `--from` replays. CI runs `--from` against a committed baseline; humans run `--live` before a prompt change to detect drift. The mode flag is a CLI affordance, not two competing implementations.
