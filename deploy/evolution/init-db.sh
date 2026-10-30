#!/bin/sh
set -eu

: "${EVOLUTION_DB_USER:?EVOLUTION_DB_USER is required}"
: "${EVOLUTION_DB_PASSWORD:?EVOLUTION_DB_PASSWORD is required}"
: "${EVOLUTION_DB_NAME:?EVOLUTION_DB_NAME is required}"
: "${PGUSER:?PGUSER is required}"
: "${BAGCOIN_DB_NAME:?BAGCOIN_DB_NAME is required}"
: "${EVOLUTION_API_KEY:?EVOLUTION_API_KEY is required}"
: "${EVOLUTION_WEBHOOK_SECRET:?EVOLUTION_WEBHOOK_SECRET is required}"
: "${EVOLUTION_INSTANCE_NAME:?EVOLUTION_INSTANCE_NAME is required}"

for value in "$EVOLUTION_DB_USER" "$EVOLUTION_DB_PASSWORD" "$EVOLUTION_DB_NAME"; do
  case "$value" in
    *[!A-Za-z0-9_-]*) echo 'Evolution database credentials must be URL-safe.' >&2; exit 1 ;;
  esac
done

if [ "$EVOLUTION_API_KEY" = "$EVOLUTION_WEBHOOK_SECRET" ]; then
  echo 'Evolution API and webhook secrets must differ.' >&2
  exit 1
fi

if [ "$EVOLUTION_DB_USER" = "$PGUSER" ] || [ "$EVOLUTION_DB_NAME" = "$BAGCOIN_DB_NAME" ]; then
  echo 'Evolution database and role must be separate from BagCoin.' >&2
  exit 1
fi

psql -X -q -v ON_ERROR_STOP=1 <<'SQL'
\getenv evolution_user EVOLUTION_DB_USER
\getenv evolution_password EVOLUTION_DB_PASSWORD
\getenv evolution_database EVOLUTION_DB_NAME
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'evolution_user', :'evolution_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'evolution_user')
\gexec
SELECT format('CREATE DATABASE %I OWNER %I', :'evolution_database', :'evolution_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'evolution_database')
\gexec
SELECT (pg_get_userbyid(datdba) = :'evolution_user') AS owner_matches
FROM pg_database WHERE datname = :'evolution_database'
\gset
\if :owner_matches
\else
\echo 'Existing Evolution database has a different owner.'
\quit 3
\endif
SQL

PGPASSWORD="$EVOLUTION_DB_PASSWORD" psql -X -q -v ON_ERROR_STOP=1 \
  -U "$EVOLUTION_DB_USER" -d "$EVOLUTION_DB_NAME" -c 'SELECT 1' >/dev/null
