# Inventário de usos independentes de Redis

Análise estática do checkout em 2026-10-29; não houve conexão ao Redis nem inspeção de dados. Além de broker e backend Celery (`app/worker/celery_app.py`), os seguintes usos em `apps/server/app/` não dependem de Celery:

| Uso | Evidência | Consequência ou limite observado |
| --- | --- | --- |
| Ciclo de vida e dependência HTTP | `main.py` cria e conecta `RedisClient`; `api/deps.py` o fornece às rotas; `clients/redis.py` encapsula operações. | Configuração usa `REDIS_URL` construída em `core/config.py`; não presumir que remover Celery permita remover Redis. |
| Prontidão | `api/routes/v1/health.py` executa ping e incorpora o resultado à prontidão. | Indisponibilidade pode marcar a aplicação como não pronta. |
| Verificação de email | `services/email_verification.py` usa chaves com TTL, contadores e bloqueios; `api/routes/v1/auth.py` injeta o cliente. | Limites e controle de tentativas dependem de operações Redis; não há fallback geral demonstrado. |
| Redefinição de senha | `services/password_reset.py` usa TTL, incremento e expiração para cooldown e limites por email/IP; `auth.py` fornece Redis. | A indisponibilidade afeta o fluxo de limitação; não há fallback geral demonstrado. |
| Deduplicação de webhook | `api/routes/v1/webhook.py` usa `SET NX` com expiração de 60 segundos por mensagem. | Se o cliente não estiver disponível na inicialização, a função considera a mensagem não duplicada; falhas posteriores de operação não foram avaliadas aqui. |
| Tokens de integração | `services/integration_service.py` usa `SET NX` com TTL e `GETDEL`, com alternativa de banco documentada em `db/models/integration_link_token.py`. | Fallback não implica equivalência operacional em todos os cenários; examinar antes de qualquer mudança. |

Os Compose configuram Redis compartilhado com Celery e aplicação; a configuração local não prova topologia, tráfego ou isolamento dos ambientes implantados. Não foram inspecionados dados, credenciais, clientes externos ou logs. Manter Redis e confirmar dependências e operação com responsáveis antes de qualquer alteração.
