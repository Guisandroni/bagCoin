#!/usr/bin/env bash
set -Eeuo pipefail

DEPLOY_PATH="${DEPLOY_PATH:-/root/projects/bagCoin}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-feat/periodo-llm-classificacao-persistencia}"
ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
TRAEFIK_USERSFILE="${TRAEFIK_USERSFILE:-deploy/traefik/usersfile}"

log() {
	printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

fail() {
	printf '\n[deploy:error] %s\n' "$*" >&2
	exit 1
}

compose() {
	if docker compose version >/dev/null 2>&1; then
		docker compose "$@"
		return
	fi

	if command -v docker-compose >/dev/null 2>&1; then
		docker-compose "$@"
		return
	fi

	fail "Docker Compose não encontrado. Instale 'docker compose' ou 'docker-compose'."
}

read_env_value() {
	local key="$1"
	local file="$2"
	local line value

	line="$(grep -E "^[[:space:]]*${key}=" "$file" | tail -n 1 || true)"
	value="${line#*=}"
	value="${value%$'\r'}"

	if [[ "$value" == \"*\" && "$value" == *\" ]]; then
		value="${value:1:${#value}-2}"
	elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
		value="${value:1:${#value}-2}"
	fi

	printf '%s' "$value"
}

ensure_traefik_usersfile() {
	local auth_value

	if [[ -s "$TRAEFIK_USERSFILE" ]]; then
		chmod 600 "$TRAEFIK_USERSFILE"
		return
	fi

	auth_value="$(read_env_value "TRAEFIK_DASHBOARD_AUTH" "$ENV_FILE")"
	[[ -n "$auth_value" ]] || fail "Crie $TRAEFIK_USERSFILE ou defina TRAEFIK_DASHBOARD_AUTH em $ENV_FILE."

	mkdir -p "$(dirname "$TRAEFIK_USERSFILE")"
	printf '%s\n' "${auth_value//\$\$/\$}" >"$TRAEFIK_USERSFILE"
	chmod 600 "$TRAEFIK_USERSFILE"
}

cd "$DEPLOY_PATH" || fail "Não foi possível acessar DEPLOY_PATH=$DEPLOY_PATH."

[[ -f "$ENV_FILE" ]] || fail "Arquivo de variáveis não encontrado: $ENV_FILE."
[[ -f "$COMPOSE_FILE" ]] || fail "Arquivo compose de produção não encontrado: $COMPOSE_FILE."

if [[ "${DEPLOY_SKIP_GIT:-0}" != "1" ]]; then
	log "Atualizando branch $DEPLOY_BRANCH"
	git fetch origin "$DEPLOY_BRANCH"
	git checkout "$DEPLOY_BRANCH"
	git pull --ff-only origin "$DEPLOY_BRANCH"
else
	log "DEPLOY_SKIP_GIT=1 ativo; pulando atualização Git"
fi

log "Preparando autenticação do dashboard Traefik"
ensure_traefik_usersfile

log "Validando configuração Docker Compose"
compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" config --quiet

log "Subindo containers de produção"
compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build --remove-orphans

log "Status dos containers"
compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

log "Limpando imagens antigas"
docker image prune -f

log "Deploy concluído"
