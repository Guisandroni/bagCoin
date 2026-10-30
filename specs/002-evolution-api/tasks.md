# Tasks: Migração WhatsApp para Evolution API

**Input**: `specs/002-evolution-api/{spec,plan,research,data-model,quickstart}.md`, `contracts/whatsapp.md` e `patches/plano-evolution-api.md`.

**Formato**: `[P]` tarefas paralelas em arquivos distintos; `[USn]` identifica história. Testes são exigidos pela especificação. O usuário aceitou o risco da v2.3.7 apenas para teste local; produção requer imagem corrigida. Testes estão suspensos por enquanto.

## Phase 1: Setup

- [X] T001 Inspecionar branch, alterações e opções Spec Kit em `specs/002-evolution-api/plan.md`, preservando arquivos anteriores e segredos.
- [ ] T002 [P] Confirmar contratos e disponibilidade da imagem Evolution segura em `specs/002-evolution-api/research.md`, incluindo dependência corrigida conforme GHSA-qvv5-jq5g-4cgg; 2.3.7 e 2.4.0-rc2 usam rc.9 vulnerável.
- [X] T003 [P] Confirmar contratos oficiais de webhook, autenticação, mídia, envio e reentrega na versão escolhida e atualizar `specs/002-evolution-api/contracts/whatsapp.md`; payloads não devem ser registrados integralmente.

## Phase 2: Foundational

- [X] T004 Definir algoritmo durável de idempotência com prevenção de concorrência e falhas entre persistência e envio em `specs/002-evolution-api/data-model.md`; demonstrar como reentregas evitam transações financeiras duplicadas.
- [X] T005 Planejar/provisionar banco dedicado idempotentemente e cache separado em `docker-compose.yml`, sem depender de scripts executados apenas em bancos recém-criados e sem destruir volumes.
- [X] T006 Configurar URL, instância, segredo de webhook e chave de API em `apps/server/app/core/config.py` e `apps/server/.env.example`, sem valores secretos reais.

## Phase 3: US1 — Mensagens individuais (P1)

**Teste independente**: evento autenticado de texto gera uma resposta ordenada ao remetente, sem processar duplicatas.

- [ ] T007 [P] [US1] Criar verificações de eventos autorizados, instância errada, tipos ignorados e duplicatas concorrentes em `apps/server/tests/test_evolution_webhook.py`.
- [ ] T008 [P] [US1] Criar verificações de envio de texto, fragmentação, falhas e timeout em `apps/server/tests/test_evolution_client.py`.
- [X] T009 [US1] Implementar cliente Evolution com chave, timeout e envio de texto em `apps/server/app/services/whatsapp_service.py`, após confirmar contratos de T003.
- [X] T010 [US1] Implementar endpoint autenticado por segredo dedicado de webhook por instância em `apps/server/app/api/routes/v1/webhook.py`, com filtros, limites e logs sem payload sensível.
- [X] T011 [US1] Integrar deduplicação durável de T004 ao processamento e às respostas em `apps/server/app/api/routes/v1/webhook.py`, sem reconhecer ação financeira falha como concluída.

## Phase 4: US2 — Mídia e relatórios (P2)

**Teste independente**: eventos simulados de áudio, imagem, documento e saída PDF exercitam fluxo do agente; mídias inválidas não geram transações.

- [ ] T012 [P] [US2] Acrescentar testes de extração de mídia, limites, arquivo ausente e tipos inválidos em `apps/server/tests/test_evolution_media.py`.
- [X] T013 [US2] Adaptar recebimento e recuperação de mídia ao contrato do agente em `apps/server/app/api/routes/v1/webhook.py`, preservando autenticação e limites.
- [X] T014 [US2] Acrescentar envio de PDF e testes de falha em `apps/server/app/services/whatsapp_service.py` e `apps/server/tests/test_evolution_client.py`.

## Phase 5: US3 — Vínculo seguro (P3)

**Teste independente**: número conhecido mantém usuário; LID ambíguo é rejeitado sem ação financeira.

- [ ] T015 [P] [US3] Testar vínculos existentes, JID e LID ambíguo em `apps/server/tests/test_evolution_identity.py`.
- [X] T016 [US3] Aplicar normalização e resolução confiável na entrada em `apps/server/app/api/routes/v1/webhook.py`, reutilizando o vínculo existente em `apps/server/app/services/integration_service.py`.

## Phase 6: US4 — Operação da instância (P4)

**Teste independente**: configuração local isolada inicia serviços, painel mostra estado e sessão persiste após reinício; conexão real depende de T002.

- [X] T017 [P] [US4] Configurar Evolution e isolamento de sessão/cache/banco em `docker-compose.dev.yml` e `docker-compose.frontend.yml` conforme T002–T005, preservando volumes existentes.
- [ ] T018 [P] [US4] Configurar Evolution nas redes e variáveis seguras de `docker-compose.prod.yml`, sem deploy nem exposição pública do painel/chave.
- [ ] T019 [US4] Configurar imagem segura fixada, persistência e rede em `docker-compose.yml` e `.env.prod.example`; verificar suporte ao painel e webhook por instância.
- [ ] T020 [US4] Validar configs e subir ambiente isolado segundo `specs/002-evolution-api/quickstart.md`, sem usar bancos/volumes reais; testar status e reinício.

## Phase 7: Encerramento e compatibilidade

- [ ] T021 Validar equivalência das funções e remover bridge `apps/whatsapp-bridge/` e referências em Compose apenas após testes simulados e reais comprovarem equivalência (T025); preservar volumes de sessão antigos.
- [ ] T022 Ajustar status/consumidores em `apps/server/app/api/routes/v1/integrations.py` e documentação `README.md` ao serviço direto, mantendo contratos públicos e Telegram.
- [ ] T023 Atualizar instruções de credenciais, banco dedicado, painel QR, webhooks, backup e reconexão em `README.md`.
- [ ] T024 Executar testes automatizados e smoke web/Telegram segundo `specs/002-evolution-api/quickstart.md`, registrando falhas sem enfraquecer validação.
- [ ] T025 Quando o usuário retomar testes, conectar número de teste pelo painel em ambiente local, reconhecendo o risco da v2.3.7 e validar texto, áudio, imagem, documento, PDF e reconexão em `specs/002-evolution-api/quickstart.md`; se não for possível, registrar como pendente e não alegar validação real.
- [ ] T026 Executar `graphify update .` após mudanças de código e validar ausência de referências obsoletas à bridge em `README.md` e `docker-compose*.yml`.

## Dependencies & Execution Order

T001 precede tudo. T002–T003 podem ocorrer em paralelo. T004–T006 exigem decisão de contrato; T007–T008 podem ser preparados em paralelo antes de T009–T011. US2 e US3 dependem do webhook; seus testes podem ser preparados em paralelo. T017–T018 são paralelos após fundamentos, T019 integra configuração comum, T020 valida. T021 depende de T025 e de equivalência comprovada; T025 requer retomada dos testes e ação humana de QR; produção exige T002. Produção não será implantada.

## Parallel Examples

- US1: T007 e T008 em arquivos de teste diferentes; implementação do webhook depende de T004 e do cliente.
- US2: T012 pode ser preparado enquanto contrato de saída PDF é verificado; T013 e T014 compartilham o fluxo e exigem coordenação.
- US3: T015 pode ser preparado enquanto US2 avança, sem edição simultânea de `webhook.py`.
- US4: T017 e T018 editam arquivos de infraestrutura distintos, depois T019–T020 integram e validam.

## Implementation Strategy

Entregar primeiro texto autenticado e identidade segura; acrescentar mídia/PDF, infraestrutura e operação; remover bridge apenas depois da equivalência demonstrada. O gate de segurança é condição para conectar conta real; a não disponibilidade de versão segura é bloqueio explícito, não autorização para usar uma imagem vulnerável.

**Decisão do usuário (2026-10-30)**: usar v2.3.7 com risco conhecido apenas no ambiente de teste e suspender a criação e execução de testes por enquanto. A aprovação de imagem segura para produção continua pendente.
