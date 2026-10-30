# bagCoin

Assistente financeiro pessoal com acesso pela aplicação web e pelo WhatsApp. O backend FastAPI usa PostgreSQL e Redis; o frontend usa Next.js e a integração WhatsApp usa Evolution API.

## Desenvolvimento local

Requisitos: Docker e Docker Compose. Esta configuração é exclusiva para desenvolvimento local.

1. Copie `.env.example` para `.env` na raiz e `apps/server/.env.example` para `apps/server/.env`. Configure os segredos e as demais credenciais necessárias no arquivo do backend. Não compartilhe esses arquivos.
2. No `.env` da raiz, configure uma senha para o banco da Evolution e dois segredos diferentes para `EVOLUTION_API_KEY` e `EVOLUTION_WEBHOOK_SECRET`. Por exemplo, gere cada valor com `openssl rand -hex 32`.
3. Para envio de e-mails de confirmação e recuperação de senha, configure `RESEND_API_KEY` e `RESEND_FROM_EMAIL` em `apps/server/.env`. O provedor padrão é Resend.
4. Inicie os serviços:

```sh
docker compose up -d --build
docker compose logs -f
```

O frontend está em http://localhost:3000, a API e sua documentação em http://localhost:8000/docs e a Evolution em http://localhost:8080. PostgreSQL e Redis ficam acessíveis apenas pela rede Docker. Alterações no frontend e no código Python são recarregadas automaticamente; alterações nas dependências exigem reconstruir as imagens.

A inicialização da API aplica as migrações Alembic. Um serviço de inicialização cria o banco e usuário separados da Evolution antes de ela iniciar. Os dados persistem em volumes Docker. `docker compose down` encerra os serviços sem apagar os volumes; `docker compose down -v` também apaga os dados.

## WhatsApp

Configure a instância no painel da Evolution com o nome de `EVOLUTION_INSTANCE_NAME`, conecte o número pelo QR code e configure o webhook para `http://app:8000/api/v1/webhook/evolution`, com o cabeçalho `X-Evolution-Webhook-Secret` usando o valor de `EVOLUTION_WEBHOOK_SECRET`. O número do bot para os links de associação é configurado por `BOT_WHATSAPP_NUMBER` no backend.

A imagem Evolution v2.3.7 foi mantida por decisão de desenvolvimento e possui vulnerabilidade conhecida (CVE-2026-48063). Use-a somente localmente para experimentação; atualize e reavalie a segurança antes de disponibilizar o projeto na internet.

## Comandos úteis

```sh
make docker-up       # Compila e inicia os serviços
make docker-logs     # Acompanha os logs
make docker-down     # Encerra os serviços
make db-current      # Mostra a migração atual
```

Consulte [CONTEXT.md](CONTEXT.md) para a linguagem do domínio e [plano da Evolution](patches/plano-evolution-api.md) para o histórico da integração.
