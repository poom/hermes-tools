# Runtime config defaults rollout safety

Use when a PR reroutes telemetry, API providers, exporters, queues, or other runtime integrations by changing application fallback values and example env files.

## Case pattern

A PR can correctly change production/deployment configuration while still creating a local/non-cluster regression if it makes an environment-specific endpoint the unconditional application fallback or the generated `.env.example` default.

Concrete example from a PHP/Laravel OpenTelemetry migration:

- PR changed `.env.example` and `config/opentelemetry.php` to default `OTEL_EXPORTER_OTLP_ENDPOINT` to `http://otel-collector.finn.svc.cluster.local:4318`.
- `Makefile prepare-env` copied `.env.example` into `.env` / `.env.ci` for fresh setups.
- `docker-compose.yaml` did not define an `otel-collector` service.
- The endpoint was a Kubernetes-internal DNS name, not resolvable from local/non-cluster runtimes.
- Author argued the endpoint could be overridden. This did not resolve the finding: the out-of-box generated local env remained unsafe.

## Review checklist

1. Check both the application fallback code and generated/example env files (`.env.example`, `.env.ci`, Helm values, Terraform variables, docker-compose env).
2. Find how fresh local/CI/dev envs are generated (`make prepare-env`, Composer/Laravel post-create scripts, devcontainer setup, Docker Compose env_file, CI bootstrap). If example env is copied into runtime env, treat example values as active defaults.
3. Check whether the advertised default endpoint/service exists in the local runtime (`docker-compose.yaml`, devcontainer services, kind/minikube setup). Kubernetes DNS such as `*.svc.cluster.local` is not local-safe unless the local harness actually runs in that cluster context.
4. For telemetry/exporter SDKs, inspect whether unreachable endpoints are async/drop-only or can block request/shutdown/worker paths. Batch processors can still synchronously flush on shutdown; default timeouts and retries matter.
5. Treat "users can override via env" as insufficient when the PR itself generates an unsafe default. The default should be safe or the local harness should supply the dependency.
6. Check tests: a new test that asserts the environment-specific endpoint as the unconditional default may lock in the unsafe behavior. Prefer tests covering local/default vs deployed env behavior separately.

## Decision guidance

Request changes when:

- A cluster-only/internal endpoint becomes an unconditional application fallback or copied local `.env` default.
- Local/dev/CI setup does not provide that service and the SDK can add latency/noise or fail runtime work.
- The fix is only documented manual override instead of safe generated defaults.

Approve or downgrade when:

- The endpoint is only set in deployment/runtime configuration, not local/generated defaults.
- Local defaults disable the exporter or point to a resolvable local collector.
- The local harness includes the collector and tests verify it.
- The SDK is demonstrably non-blocking/drop-only and failure noise is acceptable, though this is usually still worth a non-blocking note.

## Fix patterns

- Keep production/staging collector endpoints in deployment env only.
- Make `.env.example` local-safe: disabled/null exporters, blank/commented endpoint, or `localhost` with documented collector setup.
- Add a local collector service to Docker Compose/devcontainer and use its resolvable service name.
- Gate defaults by environment (`APP_ENV=local` safe; staging/prod collector) and add regression tests for both paths.
