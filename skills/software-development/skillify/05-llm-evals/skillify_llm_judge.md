# Skillify LLM Judge

## Rubric

Pass only when the answer marks missing durable evidence as `FAIL`, lists failing gates first, gives each failing gate a concrete next action inside the target skill folder, and does not use an LLM to replace deterministic checks.

## Golden Cases

- A skill has scripts but no matching tests. Expected: G3 fails.
- A skill has LLM classification in a cron prompt but no judge/golden cases. Expected: G5 fails.
- A skill has a trigger-rich description but no route tests. Expected: G7 fails.
