# Go CLI PR review quirks

Use this when reviewing small Go command-line utilities, especially repos that do not have a `go.mod`.

## Single-file / no-module tools

Some Tools-style repos keep standalone Go programs under a subdirectory without a module file. In that layout:

- `go build ./path/tool.go` can compile the command.
- `go vet ./path/tool.go` can vet the file.
- `go test ./path` may fail with `go: cannot find main module` even when PR-added tests are valid for explicit file compilation.
- Prefer explicit file tests for the changed command:
  ```bash
  go test ./path/tool.go ./path/tool_test.go -v
  ```
- If the host cannot execute Go-built binaries, use compile-only test validation:
  ```bash
  go test -c -o /tmp/tool.test ./path/tool.go ./path/tool_test.go
  ```

## macOS dyld `missing LC_UUID load command`

On some local macOS toolchains, Go-built binaries/tests may compile but abort at execution with:

```text
dyld: missing LC_UUID load command
signal: abort trap
```

Treat this as a local host/toolchain execution problem, not automatically as a PR failure, when:

1. `go build`, `go vet`, and/or `go test -c` succeed;
2. remote CI for equivalent checks is passing; and
3. the failure occurs for even a freshly compiled trivial/known command on the host.

If an alternate managed Go toolchain is available (for example `mise exec go@1.26.1 -- go test github/pr_velocity_*.go`), try it before settling for compile-only validation. Record which Go toolchain passed, and still mention the default-host dyld limitation in the review body.

Record the limitation in the review body and rely on remote CI plus compile-only or alternate-toolchain local checks. Do not claim `go run` or runtime tests passed locally unless they actually executed successfully.

## Review implications

- For PRs that add metrics/reporting CLIs, inspect scan boundaries, pagination stop conditions, time-zone/date-window semantics, and whether documentation matches defaults.
- If a metric applies an onboarding/new-user adjustment, verify the data source proves the user's true onboarding/first-activity date. A first event observed only inside the scan range is a heuristic and can distort averages for tenured users.
