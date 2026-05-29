---
name: skillify
description: Use when creating, promoting, hardening, or auditing a skill in this repository against the 10 pass/fail skill creation gates. Triggered by requests to skillify a workflow, validate or harden a skill, turn a feature into a durable skill, add skill tests/evals/resolver coverage, or run the skill gate checklist.
version: 0.1.0 # x-release-please-version
required-skills: []
required-binaries:
  - python3
required-env: []
required-mcps: []
mutates: ""
---

# Skillify

Use this skill to decide whether a workflow is actually ready to be a durable skill, and to drive it from raw script to fully-gated. Start with a hard pass/fail baseline, then close failing gates in order.

## Protocol

1. Run the deterministic gate checker first:

```bash
python3 skills/skillify/scripts/skillify_check.py skills/<target-skill> --format markdown
```

2. Treat every gate as binary. `FAIL` means the skill is not promoted yet, even if the missing work is manual evidence.
3. Report failing gates first with evidence and the next concrete fix.
4. Improve the target skill in gate order. Put code, tests, evals, and smoke evidence inside the target skill, not in scratch reports.
5. Re-run the checker and the target skill's own tests after each material fix.

## Gates

| # | Gate | Pass criteria |
|---|---|---|
| 1 | `SKILL.md` contract | `SKILL.md` exists, frontmatter follows the repo schema (`name`, trigger-rich `description`, `required-skills`, `required-binaries`), the folder name matches, no leftover placeholder markers, and the body states the rules/workflow/failure behavior. |
| 2 | Deterministic code | Repeated or fragile operations live in `scripts/` as executable/importable code. The skill does not rely on an LLM for work that code can do deterministically. |
| 3 | Unit tests | Every non-test script has a matching offline unit test. Tests must not require network, credentials, or live endpoints. |
| 4 | Integration tests | Live endpoint or runtime behavior has an explicit integration test or live-test harness with a clear command and skip behavior when credentials are absent. |
| 5 | LLM evals | Any LLM-owned judgment has golden cases, a rubric, and an eval/judge harness. Deterministic assertions still cover format, schema, and invariants. |
| 6 | Resolver trigger | The skill has a resolver-visible trigger: trigger-rich frontmatter description and, where the runtime requires it, an `AGENTS.md`/router entry or `agents/openai.yaml`. |
| 7 | Resolver eval | Prompt/route tests prove realistic user requests select this skill and non-matching requests do not. |
| 8 | Resolvable and DRY audit | Markdown links resolve, reference files are reachable, scripts are mentioned by durable docs, and there is no duplicated source of truth. If the workflow used or created a deterministic helper, the helper is bundled under `scripts/` rather than described only in prose or left only in an external runtime path. |
| 9 | E2E smoke test | A documented smoke command exercises the skill through the same path an operator or scheduled runtime uses and records durable evidence. |
| 10 | Filing rules | Durable artifacts live in the skill folder, scratch files live under ignored `tmp/`, and there are no top-level scratch reports (compliance dumps, installation guides, quick-reference summaries). Standard `README.md`, `CHANGELOG.md`, `LICENSE`, and `CONTRIBUTING.md` are allowed. |

## Applying To A Skill

Pick any skill folder in this repository and run:

```bash
python3 skills/skillify/scripts/skillify_check.py skills/<target-skill> --format markdown
```

Expected early failures are useful, not surprising: `04-integration-tests/`, `05-llm-evals/`, `07-resolver-evals/`, `09-e2e-smoke/`, and filing cleanup are usually the gaps after deterministic scripts exist.

## Fix Order

1. Fix contract validity first because every downstream agent reads `SKILL.md`.
2. Add or repair deterministic code and offline unit tests before live checks. If a session already produced a helper script or deterministic recorder, copy it into the target skill's `scripts/` directory and point to it from `SKILL.md`; do not claim the skill is complete while the script exists only in `~/.hermes/scripts`, `/tmp`, or another runtime path.
3. Add integration tests and LLM evals for behavior code cannot fully judge.
4. Add resolver trigger coverage and resolver evals.
5. Run the resolvable/DRY audit, then the E2E smoke.
6. Clean filing issues last so evidence from the work remains available until it is moved into durable homes.

## Reporting Format

Report in this shape:

```text
Overall: FAIL

Failing gates:
- G5 LLM evals: no judge harness found. Next: add 05-llm-evals/<domain>_llm_judge.py with golden cases.
- G7 Resolver eval: no route test found. Next: add 07-resolver-evals/ prompts that should and should not trigger the skill.

Passing gates:
- G2 Deterministic code: scripts/ contains report generators with matching tests.
```

Do not create a standalone compliance report unless the user asks for an artifact. The baseline can live in the chat response while fixes land in the target skill.

## Prior art

This skill converged independently on the same 10-checklist shape Garry Tan documented in [garrytan/gbrain/skills/skillify](https://github.com/garrytan/gbrain/tree/master/skills/skillify) (April 2026). His framework has the same insight: hold the human responsible for judgment, hold the tooling responsible for the checklist. Same contract, different runtime — his targets the gbrain knowledge graph; ours targets agent-resources skill folders.

## Scripts

- `scripts/skillify_check.py` - emits the 10-gate pass/fail baseline as Markdown or JSON.
- `scripts/test_skillify_check.py` - unit coverage for the gate checker.

## References

- [`references/patterns.md`](references/patterns.md) - the seven skill types (Mutation, Periodic report, Synthesis, Review, Generation, Tool guide, Meta) crossed against each gate. Variable gates (G2, G4, G5, G9) are in a matrix; uniform gates (G1, G3, G6, G7, G8, G10) listed separately. The canonical G5 LLM-judge section covers eligibility (which steps need a judge), where `--rubric` should point (the same source the production runner reads), and the one-judge-per-LLM-step pattern. Pick a type before designing tests for a new skill.
- [`references/gate-examples.md`](references/gate-examples.md) - concrete copyable templates for each of the 10 gates: passing `SKILL.md` frontmatter, idempotent script shape, offline test harness, sandbox integration test, judge skeleton, resolver eval prompts, G8 failure-mode table, three-tier smoke command, folder/`.gitignore` shape. Pair with `patterns.md` when filling out a new skill.
- [`references/support-file-validation.md`](references/support-file-validation.md) - checklist for avoiding false "Skillify pass" reports when a skill references scripts/templates/references that must be bundled with the package.
- [`references/periodic-discord-monitor-skills.md`](references/periodic-discord-monitor-skills.md) - promotion/migration checklist for scheduled Discord monitor skills: deterministic action emitters, Markdown state files, per-item channels, cron quietness, backup sync, and rename verification.
