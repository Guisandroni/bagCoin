# Implementation Plan: Estabilização operacional

**Branch atual**: `develop` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

**Input**: `specs/001-estabilizacao-operacional/spec.md`. O identificador retornado pelo setup é `001-estabilizacao-operacional`; nenhuma branch de feature foi criada.

## Summary

Entregar em PRs separados: corrigir Compose, proteger `develop` com CI, investigar a infraestrutura assíncrona e atualizar a documentação. Manter serviços e dados; nenhuma alteração pública de API ou implantação de produção está prevista.

## Technical Context

**Language/Version**: Python 3.11 e TypeScript/Node do projeto.

**Primary Dependencies**: FastAPI, Docker Compose, GitHub Actions, Celery, Redis, Next.js.

**Storage**: PostgreSQL, Redis e volumes existentes; sem migração de dados planejada.

**Testing**: pytest, Ruff, ty, Vitest, Playwright e validação/smoke Compose.

**Target Platform**: desenvolvimento local e configuração de produção em contêineres.

**Project Type**: aplicação web e API multicanal.

**Performance Goals**: sem novas metas de desempenho; preservar comportamento atual.

**Constraints**: não remover serviços, volumes ou dados; não publicar produção; não reduzir limites de qualidade existentes; proteção de branch depende de permissões.

**Scale/Scope**: três variantes Compose afetadas, workflows existentes, investigação operacional e documentação.

## Constitution Check

- Domínio, identidade e contratos: preservados; não há mudanças de modelo/API.
- Segurança e integridade: validação com dados e volumes descartáveis, sem expor segredos; entrypoint executa migrações.
- Simplicidade: corrigir configurações existentes, sem novas dependências ou remoção antecipada de serviços.
- Verificação: validar sintaxe, imagens, smoke e checks existentes; registrar falhas e permissões insuficientes.
- Operação: documentar comportamento observado e separar Redis de Celery.

**Resultado antes e depois do desenho**: sem violações identificadas. A ratificação da constituição permanece pendente de confirmação, conforme seu próprio registro.

## Project Structure

### Documentation (this feature)

`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/operacao.md` e `quickstart.md`; `tasks.md` será gerado na próxima fase.

### Source Code (repository root)

`docker-compose*.yml`, `.github/workflows/`, `apps/server/`, `apps/web/`, `README.md` e documentação operacional existente.

**Structure Decision**: manter a estrutura atual e separar as entregas por responsabilidade.

## Implementation sequence

1. Compose: restaurar o backend Python nos três arquivos afetados; preservar recarga em desenvolvimento e quatro workers em produção, usar healthcheck HTTP que falhe em status não saudável e alinhar imagens dos processos Celery. Validar configurações, builds e smoke local isolado.
2. CI: adicionar `develop` aos gatilhos existentes, tornar lint frontend bloqueante, preservar verificações e o limite de cobertura; validar nomes reais dos checks em PR antes de configurar regras de proteção, preservando regras existentes. Não ampliar o gatilho de deploy. Avaliar E2E separadamente, sem torná-lo obrigatório agora.
3. Investigar tarefas, produtores, consumidores, agendamentos e usos independentes do Redis; coletar evidências operacionais autorizadas e registrar limites e alternativas. Não remover serviços sem decisão posterior.
4. Atualizar README e documentação operacional conforme os resultados finais; verificar portas, comandos e responsabilidades. Cada PR registra verificações, falhas e bloqueios.

## Complexity Tracking

Nenhuma exceção ou abstração adicional prevista.
