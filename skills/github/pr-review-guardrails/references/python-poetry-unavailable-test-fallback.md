# Python PR test fallback when Poetry is unavailable

Use this during PR reviews for Python repos when the canonical runner is `poetry run ...` but `poetry` is not installed on the review host, and CI is already available as the primary signal.

## Pattern

1. Read `pyproject.toml`, test helpers, and import-time dependencies before guessing packages.
2. Prefer running the narrowest meaningful tests for the changed behavior.
3. If imports fail because only a small dependency set is missing, install those dependencies into a throwaway target outside the repo and use `PYTHONPATH` rather than mutating the checkout:

```bash
TARGET=/tmp/pr-review-pydeps
python3 -m pip install --target "$TARGET" PyMySQL jmespath requests boto3 cryptography pytest
PYTHONPATH="$TARGET" python3 -m pytest tests/unit/test_file.py::test_name -q
```

If `uv` is available, this is faster and avoids global environment changes:

```bash
TARGET=/tmp/pr-review-pydeps
uv pip install --target "$TARGET" PyMySQL jmespath requests boto3 cryptography pytest
PYTHONPATH="$TARGET" python3 -m pytest tests/unit/test_file.py::test_name -q
```

4. If the repo has private/git dependencies but the changed tests stub those code paths at import time, omit private packages only after verifying the imported symbols are not exercised by the targeted test.
5. If direct `pytest` starts but fails before collection because the host lacks a repo-configured plugin from `addopts` (for example `--testdox` without `pytest-testdox`), and installing the full dev environment is not practical, rerun the same narrow target with `-o addopts=''` and explicit path/import setup. Example:

```bash
PYTHONPATH=Account-Creation-Preparation \
python3 -m pytest -o addopts='' \
  Account-Creation-Preparation/tests/test_feature_flags.py \
  Account-Creation-Preparation/tests/test_za_limits.py -q
```

Only use this as a fallback after reading `pyproject.toml`; record that repo-level pytest options were disabled because the local host lacked the plugin, and rely on remote CI for the canonical command.
6. Record the fallback command and why it differs from the canonical command in the review body.

## Pitfalls

- Do not install into the system Python or write dependency artifacts into the repository checkout.
- Do not treat this fallback as stronger than CI; use it as additional local confidence.
- Keep the fallback narrow. If many dependencies are missing or import-time side effects are complex, rely on passing remote CI instead of constructing an ad hoc full environment.
- Clean up temporary prompt/files created in the checkout before finishing (`git status --short` should be clean except intentional review artifacts outside the repo).

## Example from a PR review

For `EWA-Services/Limit-Setting-Strategy`, `poetry` was unavailable and direct pytest initially failed on missing imports. A narrow fallback installed runtime import dependencies into `/tmp/pr238-pydeps`, then ran:

```bash
PYTHONPATH=/tmp/pr238-pydeps python3 -m py_compile Limit-Setting-Reactivation-Logic/lambda_function.py tests/unit/test_logic_lambda_unit.py
PYTHONPATH=/tmp/pr238-pydeps python3 -m pytest \
  tests/unit/test_logic_lambda_unit.py::test_apply_th_limit_shock_cap \
  tests/unit/test_logic_lambda_unit.py::test_apply_th_limit_shock_cap_logs_delta_payload_when_cap_applies -q
```

This was reported as supplemental local verification while GitHub `unit-tests`/`integration-tests` remained the merge-safety source of truth.
