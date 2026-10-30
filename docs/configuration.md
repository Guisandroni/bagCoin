# Configuration Reference

All configuration is managed via environment variables, loaded from
`apps/server/.env` using [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/).

Settings are defined in `app/core/config.py` and accessed via the global
`settings` object:

```python
from app.core.config import settings

print(settings.AI_MODEL)
print(settings.DEBUG)
```

## Getting Started

```bash
cd apps/server

# Copy the example file (may already exist if generated with --generate-env)
cp .env.example .env

# Generate a secure secret key
openssl rand -hex 32
# Paste the output as SECRET_KEY in .env
```

## Project Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `PROJECT_NAME` | `bagcoin_api` | Display name for the project |
| `API_V1_STR` | `/api/v1` | API version prefix |
| `DEBUG` | `false` | Enable debug mode (verbose errors, auto-reload) |
| `ENVIRONMENT` | `local` | One of: `development`, `local`, `staging`, `production` |
| `TIMEZONE` | `UTC` | IANA timezone (e.g. `UTC`, `Europe/Warsaw`, `America/New_York`) |
| `MODELS_CACHE_DIR` | `./models_cache` | Directory for cached ML models |
| `MEDIA_DIR` | `./media` | Directory for uploaded files |
| `MAX_UPLOAD_SIZE_MB` | `50` | Maximum file upload size in megabytes |

## Authentication

### JWT

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | (insecure default) | JWT signing key. **Must** be changed in production. Generate with: `openssl rand -hex 32` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | `10080` | Refresh token lifetime (7 days) |
| `ALGORITHM` | `HS256` | JWT signing algorithm |

Production validation: `SECRET_KEY` must be at least 32 characters and cannot
use the default value in `ENVIRONMENT=production`.

### API Key

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | `change-me-in-production` | Shared API key for programmatic access |
| `API_KEY_HEADER` | `X-API-Key` | HTTP header name for API key |

Production validation: `API_KEY` cannot use the default value in
`ENVIRONMENT=production`.

## Database (PostgreSQL)

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_USER` | `postgres` | PostgreSQL user |
| `POSTGRES_PASSWORD` | (empty) | PostgreSQL password |
| `POSTGRES_DB` | `bagcoin_api` | Database name |
| `DB_POOL_SIZE` | `5` | Connection pool size |
| `DB_MAX_OVERFLOW` | `10` | Max overflow connections |
| `DB_POOL_TIMEOUT` | `30` | Pool timeout in seconds |

Computed properties:
- `DATABASE_URL` -- async connection string (`postgresql+asyncpg://...`)
- `DATABASE_URL_SYNC` -- sync connection string for Alembic

## Redis

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_PASSWORD` | (none) | Redis password (optional) |
| `REDIS_DB` | `0` | Redis database number |

## AI Agent

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | (empty) | OpenAI API key |
| `AI_MODEL` | `gpt-4.1-mini` | Default LLM model for chat |
| `AI_TEMPERATURE` | `0.7` | LLM temperature (0.0 = deterministic, 1.0 = creative) |
| `AI_AVAILABLE_MODELS` | (auto-configured) | JSON list of models shown in the UI model selector |
| `AI_FRAMEWORK` | `langgraph` | AI framework (informational) |
| `LLM_PROVIDER` | `openai` | LLM provider (informational) |

### Customizing Available Models

Override `AI_AVAILABLE_MODELS` in `.env` to customize the model selector:

```bash
AI_AVAILABLE_MODELS=["gpt-4.1-mini","gpt-4.1","claude-sonnet-4-6"]
```

## Observability (Logfire)

| Variable | Default | Description |
|----------|---------|-------------|
| `LOGFIRE_TOKEN` | (none) | Pydantic Logfire token. Get one at https://logfire.pydantic.dev |
| `LOGFIRE_SERVICE_NAME` | `bagcoin_api` | Service name in Logfire dashboard |
| `LOGFIRE_ENVIRONMENT` | `development` | Environment tag |

## Observability (LangSmith)

| Variable | Default | Description |
|----------|---------|-------------|
| `LANGCHAIN_TRACING_V2` | `true` | Enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | (none) | LangSmith API key. Get one at https://smith.langchain.com |
| `LANGCHAIN_PROJECT` | `bagcoin_api` | Project name in LangSmith |
| `LANGCHAIN_ENDPOINT` | `https://api.smith.langchain.com` | LangSmith API endpoint |

## CORS

| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | `["http://localhost:3000","http://localhost:8080"]` | Allowed origins (JSON array) |
| `CORS_ALLOW_CREDENTIALS` | `true` | Allow credentials (cookies) |
| `CORS_ALLOW_METHODS` | `["*"]` | Allowed HTTP methods |
| `CORS_ALLOW_HEADERS` | `["*"]` | Allowed HTTP headers |

Production validation: `CORS_ORIGINS` cannot contain `"*"` in
`ENVIRONMENT=production`.

## Development Compose

The root `.env` supplies the Compose database and Evolution settings. The API reads `apps/server/.env`; Compose overrides the database, Redis, Evolution URL and email provider for its Docker network. See [the setup guide](../README.md#desenvolvimento-local) and the example files.

The Evolution database uses separate credentials and a separate database. `EVOLUTION_API_KEY` and `EVOLUTION_WEBHOOK_SECRET` must be different. `RESEND_API_KEY` and `RESEND_FROM_EMAIL` configure email delivery.
