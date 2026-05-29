# Resolution Flow

## Scope

This reference contains the full examples that were extracted from `SKILL.md` to keep the skill itself focused on the core contract.

## File Examples

### `.agents.env`

```env
# .agents.env
# Format: KEY=op://vault/item/field

NPM_TOKEN=op://Engineering/npm-registry/credential
FONTAWESOME_TOKEN=op://Engineering/fontawesome-pro/npm-token
GH_PACKAGES_TOKEN=op://Engineering/github-packages/token
```

Rules:

- every non-comment line is `KEY=op://vault/item/field`
- blank lines are ignored
- default values and shell interpolation are not allowed
- unresolved refs should fail the run loudly

### `.agents.npmrc`

```ini
@finn:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${GH_PACKAGES_TOKEN}

@fortawesome:registry=https://npm.fontawesome.com/
//npm.fontawesome.com/:_authToken=${FONTAWESOME_TOKEN}
```

npm reads `${VAR}` natively. Most other config formats do not.

## Render Helpers

Use committed `.agents.*` files as templates whenever the target format cannot read environment variables directly.

```bash
render_template() {
  local src="$1"
  local dest="$2"
  mkdir -p "$(dirname "$dest")"
  envsubst < "$src" > "$dest"
}

render_tool_configs() {
  [[ -f "$REPO_ROOT/.agents.netrc" ]] && render_template "$REPO_ROOT/.agents.netrc" "$HOME/.netrc" && chmod 600 "$HOME/.netrc"
  [[ -f "$REPO_ROOT/.agents.pip.conf" ]] && render_template "$REPO_ROOT/.agents.pip.conf" "$HOME/.config/pip/pip.conf"
  [[ -f "$REPO_ROOT/.agents.auth.json" ]] && render_template "$REPO_ROOT/.agents.auth.json" "$HOME/.composer/auth.json"
}
```

## Full `before_run` Pseudocode

```bash
resolve_agents_env() {
  local env_file="$REPO_ROOT/.agents.env"
  [[ -f "$env_file" ]] || return 0

  while IFS= read -r line; do
    [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue

    local key="${line%%=*}"
    local ref="${line#*=}"
    local value
    value=$(op read "$ref" 2>/dev/null) || {
      echo "ERROR: Failed to resolve $key from $ref" >&2
      echo "Check: Does the 1Password item exist? Does the service account have access?" >&2
      return 1
    }

    export "$key=$value"
  done < "$env_file"
}

setup_tools() {
  if [[ -f "$REPO_ROOT/.mise.toml" ]]; then
    mise trust "$REPO_ROOT"
    mise install
  fi
}

resolve_agents_env
render_tool_configs
setup_tools
```

## Error Handling

Common failure modes:

1. missing or renamed 1Password item
2. service account lacks vault access
3. 1Password connectivity issue
4. `envsubst` missing or destination path unwritable

Treat all four as setup failures and stop before install/test work begins.
