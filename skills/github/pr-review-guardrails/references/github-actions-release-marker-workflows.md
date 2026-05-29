# GitHub Actions release-marker workflow reviews

Use this when reviewing reusable GitHub Actions workflows that parse and update release/version markers in source files (for example Terraform `lambda-function-versions.tf` lines tagged with comments like `#x-release-production-version-<component>`).

## BE-2956 pattern: exact lookup but stale mutation

A real blocker occurred when a PR fixed marker lookup from prefix matching to exact end-of-line matching, but left the actual update command prefix-based.

Problem shape:

```bash
marker_escaped="$(printf '%s' "${VERSION_MARKER}" | sed -E 's/[][\.^$*+?{}()|/]/\\&/g')"
grep -m1 -E "${marker_escaped}[[:space:]]*$" "${VERSION_FILE}"
# ...later...
sed -E "0,/${marker_escaped}/ { /${marker_escaped}/ s/${tag_pattern}/${replacement}/ }" "${VERSION_FILE}" > "${tmp_file}"
```

If the file contains a prefix-overlapping marker first:

```hcl
production_risk_evaluation_postprocess_version = "riREDACTED_SECRET_PATTERN.1.0" #x-release-production-version-riREDACTED_SECRET_PATTERN
production_risk_evaluation_version = "risk-evaluation-v0.5.0" #x-release-production-version-risk-evaluation
```

then exact `grep` finds the intended line, but `0,/${marker_escaped}/` stops at the postprocess marker. The `risk-evaluation-v...` substitution matches nothing, leaving the file unchanged. A later `git diff --quiet` path can produce no marker-bump commit/PR even though the deploy workflow appeared to resolve the correct component.

## Review checklist

- Search for **all** uses of the marker regex: lookup, validation, replacement, line range, extraction, and tests. Exact matching must be consistent across the read and write paths.
- Prefer a shared variable such as `marker_pattern="${marker_escaped}[[:space:]]*$"` and use it for every marker address/match. Avoid recomputing similar-but-different regexes inline.
- Be suspicious of `sed` ranges like `0,/${marker_escaped}/` or `/marker/,/.../` when marker names can overlap by prefix.
- Confirm the update command changes the already-validated exact line, not merely “some line containing the marker substring.” A Python/AWK one-pass exact-line update can be safer than complex `sed` range addressing.
- Regression tests should exercise the **mutation**, not just lookup. Use a fixture where the longer/prefixed component appears before the shorter target component and assert:
  - the shorter target row is changed,
  - the longer/prefixed row is untouched,
  - the command exits non-zero when only the prefixed marker exists.
- Do not rely solely on substring tests that assert exact `grep` commands exist in the workflow; those can pass while the mutating command remains wrong.

## Useful local probe

For shell snippets embedded in YAML, extract or model the exact update block against a temporary fixture. On macOS, remember BSD `sed` may reject GNU-specific `0,/pattern/` ranges even if GitHub Actions runs on GNU sed; record that as a host limitation and use Linux CI/tests or a small Python model to prove the prefix-overlap behavior.
