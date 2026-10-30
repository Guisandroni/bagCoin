# Implementation Plan: Migração WhatsApp para Evolution API

**Branch**: `feat/evolution-api` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

**Input**: `specs/002-evolution-api/spec.md` e `patches/plano-evolution-api.md`.

## Summary

Substituir a bridge `whatsapp-web.js` por integração direta do FastAPI com Evolution API, preservando mensagens, mídia, relatórios, vínculo de usuário e deduplicação. Uma instância compartilhada roda em Docker, com dados isolados nos serviços existentes. O usuário aceitou o risco da v2.3.7 apenas para teste local; produção continua condicionada a uma versão corrigida.

## Technical Context

**Language/Version**: Python 3.11 backend; TypeScript existente na bridge será removido após equivalência.

**Primary Dependencies**: FastAPI, httpx, Evolution API e Docker Compose; sem dependências adicionais desnecessárias.

**Storage**: PostgreSQL com banco próprio da Evolution; Redis com prefixo isolado; volumes de sessão próprios.

**Testing**: pytest para fluxos críticos e verificações locais isoladas, mocks HTTP e teste real com número do usuário; suítes antigas foram removidas.

**Target Platform**: serviços Docker no mesmo servidor; desenvolvimento local antes de produção.

**Project Type**: API e integração de mensagens.

**Performance Goals**: preservar operação atual; sem novos objetivos de vazão.

**Constraints**: não destruir volumes/sessões; não expor credenciais; não associar LID ambíguo; evitar transações financeiras duplicadas; Telegram e contratos públicos preservados; sem deploy.

**Scale/Scope**: uma instância compartilhada; mensagens individuais, mídia, relatórios, vínculo e observabilidade.

## Constitution Check

- Identidade e dados: manter vínculo por telefone e impedir atribuição ambígua.
- Segurança: verificar webhook e instância, limitar mídia e não aceitar comunicação não autenticada; revisar dependência vulnerável antes de conectar número real.
- Simplicidade: cliente e webhook no backend existente; Redis/PostgreSQL existentes com isolamento; remover bridge somente após validação.
- Verificação proporcional: testes de autenticação, concorrência, falhas, mídia e limites; smoke isolado e teste real quando disponível.
- Operação: persistência, QR no painel, observabilidade segura e documentação; ausência de deploy.

**Gate antes da implementação**: compatibilidade de contrato e correção da dependência vulnerável devem ser demonstradas; não utilizar em produção até comprovar imagem segura; o usuário autorizou teste local com a v2.3.7 vulnerável. A constituição tem data de ratificação ainda não confirmada, sem mudança neste fluxo.

**Gate pós-design**: não há alteração deliberada do modelo financeiro ou quebra intencional de API; as verificações acima permanecem obrigatórias.

## Project Structure

### Documentation (this feature)

`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `tasks.md` e `checklists/` neste diretório.

### Source Code (repository root)

`apps/server/app/api/routes/v1/webhook.py`, `apps/server/app/services/whatsapp_service.py`, `apps/server/app/core/config.py`, `apps/whatsapp-bridge/`, `docker-compose*.yml` e `README.md`.

**Structure Decision**: serviços e rotas existentes recebem adaptadores específicos; nada de nova bridge; infraestrutura segue os arquivos Compose atuais.

## Complexity Tracking

Nenhuma abstração adicional prevista. Idempotência precisa preservar correção financeira e reentrega; não presumir que trava de curto prazo é garantia durável.

**Atualização 2026-10-30**: o usuário suspendeu a execução dos testes por ora. Não interpretar ausência de testes como validação ou liberação de produção.
