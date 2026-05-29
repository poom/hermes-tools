# Kubernetes read-only diagnostics RBAC PR reviews

Use this for Infrastructure/Kubernetes PRs that add read-only access for incident/debugging, especially `pods/log`, events, endpoint metadata, ingress/network policy metadata, ExternalSecret metadata, or node metadata.

## Review focus

- **Environment scope:** verify the paths and manifests are limited to the intended environment (for example `cd/k8s/staging/**`) and do not touch production RBAC unless explicitly requested and reviewed.
- **Least privilege:** require explicit `apiGroups`, `resources`, and `verbs`; avoid `*` resource/verb/apiGroup wildcards for diagnostics roles.
- **Read-only boundary:** acceptable diagnostics verbs are normally `get/list/watch`, with `get` for `pods/log`. Block or escalate `create`, `update`, `patch`, `delete`, `exec`, `attach`, and `portforward` unless the ticket explicitly calls for them and a human/security owner accepts the risk.
- **Role separation:** prefer a separate diagnostics ClusterRole (for example `diagnostics-read-only`) bound to the existing group over turning a baseline `read-only` role into a forever-growing diagnostics bucket.
- **Secret exposure:** distinguish existing baseline `secrets` access from new diagnostics grants. ExternalSecret/SecretStore metadata may be acceptable, but actual Kubernetes Secret payload expansion or application log exposure via `pods/log` should be called out as a caveat and reviewed carefully.
- **Ticket fit:** tie the granted surfaces to the incident need (CrashLoopBackOff usually needs pod logs + events first). Do not approve broad metadata surfaces that are unrelated to the stated diagnosis path without rationale.

## Quick validation

```bash
# Diff hygiene
git diff --check "$BASE...HEAD"

# Parse changed manifests when Python PyYAML is unavailable on macOS
ruby -e 'require "yaml"; ARGV.each { |f| d=YAML.load_file(f); puts "#{f} #{d["kind"]} #{d.dig("metadata","name")}" }' \
  path/to/changed-rbac.yaml

# Inspect verbs/resources in ClusterRoles
ruby -e 'require "yaml"; ARGV.each { |f| d=YAML.load_file(f); next unless d["kind"]=="ClusterRole"; puts f; d["rules"].each { |r| puts "  #{r["apiGroups"].inspect} #{r["resources"].inspect} #{r["verbs"].inspect}" } }' \
  path/to/clusterrole.yaml
```

If `kubectl` is unavailable or unauthenticated, do not claim dry-run validation passed. Rely on YAML parsing plus passing CI/pre-commit/Digger evidence and state the host limitation.

## Concrete approve-level pattern

In EWA-Services/Infrastructure #4634, the approve-level final shape was:

- staging-only RBAC paths;
- a separate `diagnostics-read-only` ClusterRole for `events`, `nodes`, `pods/log`, `endpointslices`, `events.k8s.io/events`, ExternalSecret metadata, `ingresses`, and `networkpolicies`;
- binding the existing `read-only` group to the diagnostics role;
- keeping baseline `read-only` focused on normal workload/config/RBAC/metrics reads;
- no wildcards and no mutating/interactive verbs;
- explicit caveats that `pods/log` may expose sensitive application logs and that future Secret payload expansion needs separate review.
