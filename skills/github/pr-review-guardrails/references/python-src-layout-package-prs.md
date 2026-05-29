# Python src-layout package PR reviews

Use for Python package-skeleton or shared-module PRs that introduce a `src/` layout and `pyproject.toml` metadata.

## Local test invocation

If `python -m pytest package-dir/tests -q` fails during collection with `ModuleNotFoundError: No module named '<package>'`, do not immediately treat it as a product test failure. For `src/` layouts, first rerun with the package source directory on `PYTHONPATH` or install the package editable in an isolated environment:

```bash
PYTHONPATH=<package-dir>/src python3 -m pytest <package-dir>/tests -q
# or, where safe/available:
python3 -m pip install -e <package-dir>
python3 -m pytest <package-dir>/tests -q
```

Record both outcomes in the review: the raw host invocation failed due to import path, while the src-layout invocation is the meaningful package test signal.

## Metadata/runtime compatibility

Check that `[project]` metadata matches stdlib/runtime imports. Examples:

- `zoneinfo` requires Python >= 3.9; require `requires-python = ">=3.9"` (or a backport dependency if supporting older Python).
- If the PR body claims a minimum Python version, verify the actual `pyproject.toml` contains the matching `requires-python`.

Missing minimum-version metadata is high-priority when downstream consumers could install on unsupported Python and fail later at import/runtime.

## Non-fatal helper contracts

For shared helpers documented as non-fatal (heartbeats, notifications, telemetry, cleanup hooks), verify setup/construction code is inside the guarded failure path, not only the network call. For example, `urllib.request.Request(url, ...)` can raise `ValueError` for malformed URLs before `urlopen`; if it sits outside `try`, a malformed config can abort the report despite a "log but do not fail" contract.

Prefer a regression test for malformed configuration values, not only transport errors such as `URLError` or non-2xx responses.

## Review posting

When an existing current-head bot/human review thread already identifies the same issue and remains unresolved, avoid duplicate inline comments. Use the formal review body to say the existing thread remains blocking and summarize the fix direction.
