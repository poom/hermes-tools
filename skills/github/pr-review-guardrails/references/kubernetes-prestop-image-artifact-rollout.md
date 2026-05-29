# Kubernetes preStop hook + image artifact rollout review

Use this reference when a PR wires Kubernetes lifecycle hooks, scripts, or binaries supplied by application images, especially `preStop` hooks for Kafka/worker graceful shutdown.

## Case pattern

In `EWA-Services/Infrastructure#4342`, the production infra PR added `preStop` hooks for MCS and ACS Kafka consumers. The important review question was not only whether the manifest rendered, but whether the referenced production image tags actually contained `shell/kafka-graceful-shutdown.sh` and whether the fallback shell preserved failure signal.

## Checklist

1. Identify the exact deployment image tags in the PR-owned manifests/values.
2. Verify the app-side PRs that add the hook/script are merged.
3. Verify the deployed tag actually contains the file, not just `main`:
   ```bash
   gh api repos/OWNER/APP_REPO/contents/shell/kafka-graceful-shutdown.sh?ref=vX.Y.Z \
     --jq '{path,sha,size,download_url}'
   ```
4. Compare staging/prod rollout sequence. If prod PR says staging must be validated first, check both the original staging PR and any follow-up that patches the exact hook behavior.
5. Inspect the shell control flow:
   - Acceptable when missing-script compatibility is intentional:
     ```sh
     if test -x shell/kafka-graceful-shutdown.sh; then
       shell/kafka-graceful-shutdown.sh
     else
       sleep 15
     fi
     ```
   - Risky/blocking when it masks script failures:
     ```sh
     test -x shell/kafka-graceful-shutdown.sh && shell/kafka-graceful-shutdown.sh || sleep 15
     ```
6. Treat a bot comment asking to sleep after a non-zero script exit as non-blocking when the explicit review requirement is to keep real graceful-shutdown failures visible. The compatibility fallback is for missing/non-executable script only; script failure should surface.
7. Check local syntax when full Helm tooling is unavailable:
   ```bash
   git diff --check origin/main...HEAD
   ruby -e 'require "yaml"; ARGV.each { |f| YAML.load_file(f); puts "ok #{f}" }' path/to/file.yaml
   ```
   Record that this is a syntax fallback, not a replacement for `helm template`/CI.

## Approval wording

For approve-level outcomes, include:

- The current head SHA and that the live `base...HEAD` diff is the reviewed diff.
- The app PRs/tags checked and evidence that the script exists at those tags.
- Why the `if test -x ...; then script; else sleep 15; fi` form is safe: it preserves missing-script compatibility without hiding actual script failures.
- Non-blocking follow-up: verify logs/observability on at least one rolling restart and monitor whether `terminationGracePeriodSeconds` is sufficient.
