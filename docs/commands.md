# Commands Reference

This project provides commands via two interfaces: **Make** targets for common
workflows and a **project CLI** for fine-grained control.

## Make Commands

Run these from the project root directory.

### Quick Start

| Command | Description |
|---------|-------------|
| `make quickstart` | Build and start the development stack; the API applies migrations |
| `make install` | Install backend dependencies with uv + pre-commit hooks |

### Development

| Command | Description |
|---------|-------------|
| `make run` | Start development server with hot reload |
| `make run-prod` | Start production server (0.0.0.0:8000) |
| `make routes` | Show all registered API routes |
| `make test` | Run tests with verbose output |
| `make test-cov` | Run tests with coverage report (HTML + terminal) |
| `make format` | Auto-format code with ruff |
| `make lint` | Lint and type-check code (ruff + ty) |
| `make clean` | Remove cache files (__pycache__, .pytest_cache, etc.) |

### Database

| Command | Description |
|---------|-------------|
| `make db-init` | Start the development stack; the API applies migrations |
| `make db-migrate` | Create new migration (prompts for message) |
| `make db-upgrade` | Apply pending migrations |
| `make db-downgrade` | Rollback last migration |
| `make db-current` | Show current migration revision |
| `make db-history` | Show full migration history |

### Users

| Command | Description |
|---------|-------------|
| `make create-admin` | Create admin user (interactive) |
| `make user-create` | Create new user (interactive) |
| `make user-list` | List all users |

### Docker (Development)

| Command | Description |
|---------|-------------|
| `make docker-up` | Build and start the development stack |
| `make docker-down` | Stop all services |
| `make docker-logs` | Follow service logs |
| `make docker-build` | Build development images |
| `make docker-shell` | Open shell in app container |
| `make docker-db` | Start only PostgreSQL |
| `make docker-db-stop` | Stop PostgreSQL |
| `make docker-redis` | Start only Redis |
| `make docker-redis-stop` | Stop Redis |

---

## Project CLI

All project CLI commands are invoked via:

```bash
cd apps/server
uv run bagcoin_api <group> <command> [options]
```

### Server Commands

```bash
uv run bagcoin_api server run              # Start dev server
uv run bagcoin_api server run --reload     # With hot reload
uv run bagcoin_api server run --port 9000  # Custom port
uv run bagcoin_api server routes           # Show all registered routes
```

### Database Commands

```bash
uv run bagcoin_api db init                  # Run all migrations
uv run bagcoin_api db migrate -m "message"  # Create new migration
uv run bagcoin_api db upgrade               # Apply pending migrations
uv run bagcoin_api db upgrade --revision e3f  # Upgrade to specific revision
uv run bagcoin_api db downgrade             # Rollback last migration
uv run bagcoin_api db downgrade --revision base  # Rollback to start
uv run bagcoin_api db current               # Show current revision
uv run bagcoin_api db history               # Show migration history
```

### User Commands

```bash
# Create user (interactive prompts for email/password)
uv run bagcoin_api user create

# Create user non-interactively
uv run bagcoin_api user create --email user@example.com --password secret

# Create user with specific role
uv run bagcoin_api user create --email admin@example.com --password secret --role admin

# Create user with superuser flag
uv run bagcoin_api user create --email admin@example.com --password secret --superuser

# Create admin (shortcut)
uv run bagcoin_api user create-admin --email admin@example.com --password secret

# Change user role
uv run bagcoin_api user set-role user@example.com --role admin

# List all users
uv run bagcoin_api user list
```

### Custom Commands

Custom commands are auto-discovered from `app/commands/`. Run them via:

```bash
uv run bagcoin_api cmd <command-name> [options]
```

## Adding Custom Commands

Commands are auto-discovered from `app/commands/`. Create a new file:

```python
# app/commands/my_command.py
import click
from app.commands import command, success, error

@command("my-command", help="Description of what this does")
@click.option("--name", "-n", required=True, help="Name parameter")
def my_command(name: str):
    """Your command logic here."""
    success(f"Done: {name}")
```

Run it:

```bash
uv run bagcoin_api cmd my-command --name test
```

For more details, see `docs/adding_features.md`.
