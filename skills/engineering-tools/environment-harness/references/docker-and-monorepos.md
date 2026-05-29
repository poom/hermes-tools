# Docker and Monorepos

## Docker Test Services

Use `docker-compose.agents.yml` when tests need local services such as databases, queues, or emulators.

Example:

```yaml
services:
  test-db:
    image: postgres:16
    environment:
      POSTGRES_DB: test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test"]
      interval: 2s
```

Continuation:

```yaml
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

Start services in `before_run`:

```bash
docker compose -f docker-compose.agents.yml up -d --wait
```

Stop them in `after_run`:

```bash
docker compose -f docker-compose.agents.yml down -v
```

## Monorepo Pattern

- keep `.agents.env` and `.mise.toml` at the repo root
- keep shared and package-specific credentials in the same root `.agents.env`
- document package-scoped test commands in workflow instructions

Example package test:

```bash
cd packages/auth && npm test
```
