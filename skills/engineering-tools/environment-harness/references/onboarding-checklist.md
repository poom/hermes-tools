# Onboarding Checklist

Use this checklist when making a repo agent-ready.

## Prerequisites

- repo has a locally runnable test suite
- 1Password service account exists with the right vault access

## Repo Changes

- create `.mise.toml` or `.tool-versions`
- list required private registries and test credentials
- create or verify the needed 1Password items
- add `.agents.env` refs as `KEY=<secret-store-reference>`
- add `.agents.npmrc` or other `.agents.<tool-config>` templates when the tool needs a config file

## Validation

- resolve each ref safely with `op read "...ref..." | wc -c`
- run the `before_run` flow or equivalent setup locally
- verify install commands succeed
- verify tests pass

## Registration

- add the repo to Symphony's watched repo list
- configure repo-specific hook overrides if needed
- run a test ticket end to end

## PR

- commit `.agents.env`, `.agents.npmrc` or other templates, and `.mise.toml`
- link the rollout ticket
- document any non-obvious setup in repo instructions
