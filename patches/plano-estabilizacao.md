# Plano de estabilização do bagCoin

## Resumo

Entregar as prioridades em PRs separados e pequenos, nesta ordem: Compose, CI, investigação da infraestrutura assíncrona e documentação operacional. Cada PR deve registrar suas verificações e manter compatibilidade com os dados existentes.

## Mudanças

1. **Compose:** alinhar os serviços de API de desenvolvimento, frontend e produção ao backend FastAPI em `apps/server`. Revisar comandos, healthchecks e imagens compartilhadas com worker, Beat e Flower; corrigir a inconsistência de imagens no Compose de frontend. Preservar volumes, redes e variáveis necessárias.
2. **CI e proteção de `develop`:** habilitar os workflows relevantes para pushes e PRs destinados a `develop`, mantendo os gatilhos existentes. Tornar o lint do frontend obrigatório e exigir verificações de backend e frontend — lint, testes e build aplicáveis — na proteção da branch. Validar a estabilidade do E2E antes de torná-lo obrigatório. Se faltarem permissões para configurar a proteção, entregar os workflows e registrar a configuração pendente.
3. **Infraestrutura assíncrona:** mapear produtores e consumidores Celery, tarefas agendadas, dependências operacionais e possíveis produtores externos. Registrar uma recomendação fundamentada para worker, Beat e Flower, com os efeitos de cada mudança. Manter os serviços até a decisão ser aprovada. Avaliar Redis separadamente: ele também é usado por autenticação, deduplicação e prontidão.
4. **Documentação:** atualizar o README conforme os Compose e workflows finais, incluindo portas, comandos de execução, healthchecks e responsabilidades dos serviços. Documentar a conclusão da investigação assíncrona sem apresentar tarefas de exemplo como funcionalidades de negócio.

Não há mudanças previstas nos contratos públicos da API ou no modelo de dados.

## Verificação

- Validar a configuração dos Compose e construir as imagens relevantes; subir localmente os serviços essenciais e verificar a API e suas dependências. Validar produção sem realizar deploy.
- Executar lint, testes e build correspondentes às verificações que serão obrigatórias; corrigir falhas que impeçam sua adoção ou registrar bloqueios com evidências.
- Verificar, em um PR para `develop`, que os checks são acionados e que a proteção exige os nomes corretos. Executar E2E para avaliar sua estabilidade, sem bloqueá-lo inicialmente.
- Conferir os comandos e portas documentados contra a configuração final. Após alterações de código, executar `graphify update .`.

## Premissas

A branch de destino é `develop`. A revisão do Celery é investigativa; nenhuma remoção de serviço está autorizada por este plano. A validação de produção não inclui deploy.

A investigação inicial foi estática: não confirmou produtores externos de tarefas nem executou os serviços.
