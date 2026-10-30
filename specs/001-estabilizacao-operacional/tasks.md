# Tasks: Estabilização operacional do bagCoin

**Input**: `specs/001-estabilizacao-operacional/` — especificação, plano, pesquisa, contratos e guia de validação.

**Formato**: `[P]` indica tarefas independentes em arquivos distintos; `[USn]` identifica a história. A ordem de entrega acordada é Compose → CI → investigação assíncrona → documentação, em PRs separados.

## Phase 1: Setup

- [ ] T001 Conferir o estado do repositório e preservar alterações existentes antes de trabalhar em `specs/001-estabilizacao-operacional/spec.md`.
- [ ] T002 Conferir Docker, dependências e permissões necessárias conforme `specs/001-estabilizacao-operacional/quickstart.md`, registrando bloqueios sem expor segredos.

## Phase 2: Foundational

- [ ] T003 Identificar portas, nomes fixos de contêiner e banco/volumes descartáveis para validação de `docker-compose.dev.yml` e `docker-compose.frontend.yml`; não reutilizar dados existentes nem executar `down -v` em ambiente real.
- [ ] T004 Revisar o entrypoint e o Dockerfile em `apps/server/Dockerfile` para confirmar execução de migrações e comandos antes de qualquer smoke test.

## Phase 3: User Story 1 — Ambiente reproduzível (P1, MVP)

**Objetivo**: restaurar o backend e preservar os serviços e dados nas três configurações.

**Teste independente**: validar as três configurações, construir as imagens relevantes e verificar API e dependências em ambiente local descartável.

- [ ] T005 [P] [US1] Corrigir contexto e comando da API em `docker-compose.dev.yml` para `apps/server` e Uvicorn com recarga, preservando volumes e redes.
- [ ] T006 [P] [US1] Corrigir contexto, comando e healthcheck HTTP em `docker-compose.frontend.yml`; alinhar imagens de worker, Beat e Flower e garantir sua construção antes do uso.
- [ ] T007 [P] [US1] Corrigir contexto, comando Uvicorn com quatro workers e healthcheck HTTP em `docker-compose.prod.yml`, preservando redes, volumes e configuração de produção.
- [ ] T008 [US1] Validar `config --quiet` e construir imagens relevantes de `docker-compose.dev.yml`, `docker-compose.frontend.yml` e `docker-compose.prod.yml`, usando valores fictícios não sensíveis para produção e sem deploy.
- [ ] T009 [US1] Executar smoke test isolado da API e dependências de `docker-compose.dev.yml` e verificar saúde HTTP e preservação dos volumes existentes; registrar resultados e bloqueios no PR.
- [ ] T010 [US1] Revisar as alterações dos três arquivos `docker-compose*.yml` e preparar entrega Compose independente para `develop`.

## Phase 4: User Story 2 — Proteção de develop (P2)

**Objetivo**: executar verificações obrigatórias de backend e frontend e proteger a integração.

**Teste independente**: observar os checks reais em PR para `develop` e confirmar bloqueio por falha, quando houver permissão.

- [ ] T011 [P] [US2] Acrescentar `develop` aos gatilhos de `.github/workflows/ci.yml`, preservando os checks, limite de cobertura e gatilhos existentes.
- [ ] T012 [P] [US2] Acrescentar `develop` aos gatilhos de `.github/workflows/test.yml` e remover `continue-on-error` do lint frontend; manter E2E informativo inicialmente.
- [ ] T013 [US2] Executar os comandos de backend dos workflows em `apps/server/` com PostgreSQL e Redis de teste e registrar falhas sem reduzir cobertura.
- [ ] T014 [US2] Executar lint, build e testes em `apps/web/package.json`, corrigindo falhas relacionadas ou registrando bloqueios.
- [ ] T015 [US2] Avaliar `npm run test:e2e` em `apps/web/package.json` com seus pré-requisitos e registrar estabilidade sem torná-lo obrigatório nesta entrega.
- [ ] T016 [US2] Observar os nomes reais dos checks em PR para `develop`, revisar regras existentes e configurar a proteção preservando-as; se faltar permissão, registrar os nomes e a configuração pendente no PR relativo a `.github/workflows/`.
- [ ] T017 [US2] Confirmar que um check obrigatório falho impede merge para `develop` e que `.github/workflows/deploy.yml` mantém seus gatilhos; registrar evidências ou impedimento.

## Phase 5: User Story 3 — Avaliação da infraestrutura assíncrona (P3)

**Objetivo**: elaborar recomendação baseada em evidências sem alterar serviços.

**Teste independente**: conferir inventário, fontes, incertezas e consequências para todos os serviços avaliados.

- [ ] T018 [P] [US3] Inventariar tarefas, produtores, consumidores e agenda a partir de `apps/server/app/worker/` e registrar evidências em `specs/001-estabilizacao-operacional/research.md`.
- [ ] T019 [P] [US3] Inventariar usos independentes de Redis em `apps/server/app/` e registrar evidências em `specs/001-estabilizacao-operacional/research-redis.md`.
- [ ] T020 [US3] Consultar responsáveis e evidências operacionais autorizadas sobre produtores externos sem consumir filas; registrar janela, fontes, limitações e lacunas em `specs/001-estabilizacao-operacional/research.md`.
- [ ] T021 [US3] Consolidar recomendação e impactos para worker, Beat, Flower e Redis em `specs/001-estabilizacao-operacional/research.md`, mantendo serviços até decisão aprovada.

## Phase 6: User Story 4 — Documentação operacional (P4)

**Objetivo**: tornar instruções coerentes com as entregas validadas.

**Teste independente**: conferir cada porta, comando e responsabilidade documentada contra a configuração final.

- [ ] T022 [US4] Atualizar portas, comandos, healthchecks e responsabilidades em `README.md` conforme os Compose e workflows finais.
- [ ] T023 [US4] Documentar em `README.md` as conclusões assíncronas e distinguir tarefas de exemplo de tarefas de negócio, com referência à investigação.
- [ ] T024 [US4] Conferir os exemplos de `README.md` contra `docker-compose*.yml` e `.github/workflows/`, corrigindo divergências e registrando verificações no PR.

## Phase 7: Polish & Cross-Cutting

- [ ] T025 Conferir os critérios de `specs/001-estabilizacao-operacional/spec.md` e os resultados de `specs/001-estabilizacao-operacional/quickstart.md`, registrando falhas e pendências.
- [ ] T026 Executar `graphify update .` após alterações de código, conforme `AGENTS.md`, e registrar eventual falha sem ocultá-la.

## Dependencies & Execution Order

T001–T004 precedem as histórias. A entrega segue US1 → US2 → US3 → US4; US4 depende das configurações e conclusões finais. T008 depende de T005–T007; T009 depende de T008 e do isolamento T003–T004. T016 depende dos checks disponíveis em PR; T017 depende da proteção configurada. T020–T021 dependem do inventário. T025–T026 encerram o trabalho.

## Parallel Examples

- US1: T005, T006 e T007 podem ser executadas em paralelo, cada uma em arquivo Compose distinto.
- US2: T011 e T012 podem ser executadas em paralelo em workflows distintos.
- US3: T018 e T019 podem ser executadas em paralelo; a consolidação ocorre depois.
- US4: a revisão independente de `docker-compose*.yml` e `.github/workflows/` pode ocorrer em paralelo; a edição de `README.md` deve ser coordenada.

## Implementation Strategy

Concluir setup e fundamentos, entregar e validar US1 como MVP, depois entregar US2, US3 e US4 em PRs separados. Não realizar deploy de produção nem remover infraestrutura assíncrona. A falta de acesso remoto ou de ambiente isolado deve ser reportada com evidências, sem declarar a verificação concluída.
