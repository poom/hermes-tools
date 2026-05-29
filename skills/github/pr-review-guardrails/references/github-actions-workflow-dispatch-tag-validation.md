# GitHub Actions workflow_dispatch tag-validation reviews

Use this reference when a PR hardens a manual production deploy workflow so `workflow_dispatch` can only deploy an existing Git tag, especially when the workflow previously passed raw `github.event.inputs.tag || github.ref` into `actions/checkout`.

## Review checklist

1. Verify the acceptance contract explicitly:
   - Dispatch from a branch with `tag=<existing-tag>` succeeds and deploys that tag.
   - Dispatch from a branch with `tag=<branch-name>` or a raw SHA fails before checkout/deploy.
   - Dispatch from a tag ref without explicit input succeeds when that is part of the intended UX.
   - If the ticket requires it, confirm a real manual `workflow_dispatch` run was performed against a valid tag.
2. Ensure checkout never receives untrusted/raw input:
   - The workflow should compute a validated output such as `steps.validate-tag.outputs.deploy_ref` and use that for `actions/checkout.ref`.
   - Avoid `ref: ${{ github.event.inputs.tag || github.ref }}` after the validation step; this can bypass the gate.
3. Prefer authenticated GitHub API validation for private repos:
   - Pre-checkout `git ls-remote https://github.com/OWNER/REPO.git ...` can fail with 401 because no checkout credential helper exists yet.
   - A safe pattern is `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}` plus `gh api graphql` querying `repository.ref(qualifiedName: "refs/tags/<tag>")`.
4. Check ref-name normalization and traversal cases:
   - Build `expected_ref="refs/tags/${tag_name}"`.
   - Run `git check-ref-format --normalize "$expected_ref"` and require exact equality with `expected_ref`.
   - Spot-check inputs like `main`, `refs/heads/main`, `../heads/main`, percent/path traversal variants, and a 40-char SHA.
   - A SHA-like string is only acceptable if an actual tag with that exact name exists; call this out if the ticket says “SHA-looking input” must be rejected regardless of tag existence.
5. Validate shell safety:
   - Quote all user-controlled variables.
   - Ensure anything written to `$GITHUB_OUTPUT` passed ref-format validation so it cannot inject extra outputs/newlines.
6. Re-check prior inline blockers on current head:
   - Older findings often involve crafted ref paths, percent-encoded traversal, or line-length/lint failures. Confirm current code and current checks before repeating them.

## Lightweight local probes

From a PR checkout, emulate the gate without running the workflow:

```bash
validate() {
  local tag_name="$1"
  local expected_ref="refs/tags/${tag_name}"
  local normalized_ref
  normalized_ref="$(git check-ref-format --normalize "$expected_ref" 2>/dev/null || true)"
  printf '\ninput=%q expected=%q normalized=%q\n' "$tag_name" "$expected_ref" "$normalized_ref"
  if [[ -z "$tag_name" || "$normalized_ref" != "$expected_ref" ]]; then
    echo 'format reject'
    return 0
  fi
  gh api graphql \
    -f query='query($owner:String!, $repo:String!, $qualifiedName:String!) { repository(owner:$owner, name:$repo) { ref(qualifiedName:$qualifiedName) { name } } }' \
```

Continuation:

```bash
    -F owner='OWNER' -F repo='REPO' -F qualifiedName="$expected_ref" \
    --jq '.data.repository.ref.name // empty'
}
validate 'known-valid-tag'
validate 'main'
validate '../heads/main'
validate 'refs/heads/main'
validate '0123456789abcdef0123456789abcdef01234567'
```

## Reporting wording

Use wording like:

> The deploy workflow no longer passes raw workflow input or `github.ref` to checkout. It constructs `refs/tags/<tag>`, validates the ref format, verifies the tag via the authenticated GitHub API, and checks out only the validated deploy ref. Branch/SHA/traversal-style inputs do not resolve as tags on current head.
