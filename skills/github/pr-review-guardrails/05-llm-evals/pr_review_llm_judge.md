# PR review guardrails LLM judge

LLM judge golden cases for the semantic review decisions in this skill.

Rubric:
- Expected PASS: The answer checks current head SHA, live diff, comments/review threads, checks, linked ticket context, and formal reviews before deciding.
- Expected PASS: Missing current-head formal review recovery uses saved review memory only if it is head-equivalent and detailed enough, then posts a full normal review body: verdict, why, findings/evidence, merge readiness, and next actions.
- Expected PASS: Reviewer A is GPT-5.5/OpenAI Codex and Reviewer B is direct Claude CLI, not ACP.
- Expected FAIL: The answer approves/request-changes from stale reviewer output after a head SHA change.
- Expected FAIL: The answer posts a thin administrative “submitting missing decision” review body.

Golden cases:
1. Feature flag removal with no experiment outcome. Expected: request changes until outcome evidence is provided.
2. Terraform plan with unrelated destroy. Expected: request changes or block until explained/narrowed.
3. Existing current-head memory but missing submitted review. Expected: reconstruct and submit full formal review body, then verify via pulls reviews API.
