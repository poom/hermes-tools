# Pending queue LLM judge

LLM judge golden cases for the operator-owned judgment in this skill: whether to skip, re-review, or submit a missing formal GitHub review decision.

Rubric:
- Expected PASS: The answer requires checking live current head SHA and submitted formal GitHub reviews before skipping.
- Expected PASS: If the matching decision is missing and review memory is current and detailed, the answer reconstructs the normal review body with verdict, why, findings/evidence, merge readiness, and next actions.
- Expected FAIL: The answer posts or suggests a thin administrative note such as “submitting missing decision”.
- Expected FAIL: The answer trusts local memory without checking live formal reviews.

Golden cases:
1. Prompt: “This PR says already reviewed with current-head request-changes; queue still returns it.” Expected: re-check live formal reviews; submit full reconstructed REQUEST_CHANGES if missing.
2. Prompt: “Review pending PRs chat-only.” Expected: no GitHub posting; still report one message per PR.
3. Prompt: “Saved review memory is missing evidence.” Expected: re-run or narrowly re-validate before posting.
