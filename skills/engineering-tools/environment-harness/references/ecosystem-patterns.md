# Ecosystem Patterns

## Node.js / TypeScript

```text
.agents.env    -> NPM_TOKEN, GH_PACKAGES_TOKEN, FONTAWESOME_TOKEN
.agents.npmrc  -> registry config with ${VAR} interpolation
.mise.toml     -> node = "20"
```

## Python

```text
.agents.env      -> PYPI_TOKEN or index credentials
.agents.pip.conf -> template rendered to $HOME/.config/pip/pip.conf
.mise.toml       -> python = "3.12"
```

For Poetry, skip the template file and export `POETRY_HTTP_BASIC_*` directly.

## Go

```text
.agents.env    -> GOPRIVATE_TOKEN
.agents.netrc  -> template rendered to $HOME/.netrc
.mise.toml     -> go = "1.22"
```

Set `GOPRIVATE=github.com/EWA-Services/*` and `GONOSUMCHECK=github.com/EWA-Services/*`, then render the `.netrc` template before `go mod download`.

## PHP / Composer

```text
.agents.env       -> COMPOSER_AUTH_TOKEN
.agents.auth.json -> template rendered to $HOME/.composer/auth.json
.mise.toml        -> php = "8.3"
```

## Terraform / HCL

```text
.agents.env    -> TF_TOKEN_app_terraform_io
.mise.toml     -> terraform = "1.7"
```

Terraform reads `TF_TOKEN_*` directly, so no extra render step is needed.

## Test Runner Additions

Some repos need non-secret runtime variables in the hook:

```env
CHROME_BIN=chromium-browser
PUBSUB_EMULATOR_HOST=localhost:8085
DATASTORE_EMULATOR_HOST=localhost:8081
```

Secrets for test databases or staging APIs still belong in `.agents.env`.
