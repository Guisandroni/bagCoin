# Pesquisa e decisões

## Compose

**Decisão**: usar a imagem Python de `apps/server` para a API, comandos adequados a desenvolvimento e produção e verificações de saúde que validem status HTTP. Alinhar imagens usadas por worker, Beat e Flower no frontend.

**Justificativa**: `apps/backend` não existe, `node dist/main` não corresponde ao backend e as imagens de processos no frontend são inconsistentes.

**Alternativas**: manter configuração atual falha no build; criar outro backend amplia o escopo sem necessidade.

**Risco**: o entrypoint executa migrações mesmo em processos auxiliares. Smoke tests exigem banco/volumes descartáveis e confirmação de ausência de colisões de portas e `container_name`; um nome de projeto diferente não basta.

## CI

**Decisão**: manter ambos os workflows e seus controles, acrescentar `develop`, tornar o lint do frontend obrigatório e escolher checks efetivamente executados para proteção após observar um PR. Preservar cobertura de 100% e gatilho de deploy existente.

**Justificativa**: mudanças menores preservam cobertura e evitam proteção baseada em nomes presumidos. E2E será avaliado antes de ser obrigatório.

**Alternativas**: consolidar workflows ou reduzir cobertura aumenta o escopo ou enfraquece controles; configurações remotas requerem permissão e inspeção das regras existentes.

## Infraestrutura assíncrona

**Decisão**: manter todos os serviços e produzir inventário e recomendação antes de qualquer remoção.

**Justificativa**: o código examinado contém tarefas Celery de exemplo sem produtores internos identificados, mas Redis também atende limites de autenticação, deduplicação, integrações e prontidão. A análise estática não demonstra ausência de produtores externos.

**Alternativas**: remover Celery ou Redis agora pode interromper usos não observados. Consultar responsáveis e evidências operacionais autorizadas sem consumir filas; uma janela sem atividade não prova ausência de uso futuro.

### Inventário estático (T018–T021)

Investigação em 2026-10-29, limitada ao checkout local: busca por definições de tarefas, chamadas `.delay`, `apply_async`, `send_task`, configuração Celery e comandos de execução. Não foi consultado ambiente em execução nem houve consumo de filas. Os caminhos abaixo são relativos à raiz do repositório.

- `apps/server/app/worker/tasks/examples.py` define três tarefas de exemplo: `example_task` simula processamento e retries, `long_running_task` simula progresso e `send_email_task` apenas simula envio; não é entrega real de email. `tasks/__init__.py` importa as duas primeiras do mesmo módulo. Os testes em `apps/server/tests/test_worker.py` chamam as tarefas diretamente e não demonstram publicação no broker.
- `apps/server/app/worker/celery_app.py` configura broker e backend, autodiscovery de `app.worker.tasks` e agenda `example-every-minute` para `app.worker.tasks.examples.example_task` a cada 60 segundos com argumento `periodic`; a agenda de limpeza está comentada. Beat é o produtor periódico configurado; worker é o consumidor previsto. A descoberta e o registro efetivos no processo em execução não foram verificados, portanto a configuração não comprova execução bem-sucedida.
- A busca no repositório não identificou chamadas internas de publicação de tarefas de negócio. `apps/server/cli/commands.py` e os quatro `docker-compose*.yml` contêm comandos para worker, Beat e Flower; isso demonstra configuração, não utilização real. Broker e backend usam Redis, inclusive o banco 0 nos Compose; Flower é componente de observação do Celery, não produtor de negócio identificado.

### Produtores externos e decisão pendente

Não houve consulta a responsáveis nem acesso a logs, métricas ou configuração operacional: nenhuma fonte operacional autorizada ou responsável foi disponibilizado, e a instrução desta investigação proíbe enviar mensagens. **Janela operacional observada: nenhuma**; a data acima é apenas a da análise estática. Assim, produtores externos, implantação efetiva, filas pendentes, frequência de uso e dependências de consumidores permanecem desconhecidos. Ausência de referências no checkout ou de atividade em uma janela futura não prova ausência de uso futuro.

Antes de qualquer decisão, obter dos responsáveis inventário de produtores e contratos, ambientes e horários relevantes, incluindo rotinas raras; consultar, com autorização, configurações implantadas e métricas/logs agregados de publicação e execução durante janela representativa, sem ler ou consumir mensagens nem expor segredos. Registrar fonte, intervalo e lacunas, e confirmar o registro das tarefas em ambiente isolado. A consulta aos responsáveis e a evidência operacional de T020 continuam pendentes.

**Recomendação:** manter worker, Beat, Flower e Redis até decisão aprovada baseada nessa evidência. Desativar worker pode deixar mensagens sem processamento; desativar Beat interrompe a agenda configurada e quaisquer agendas operacionais não identificadas; desativar Flower reduz observabilidade; remover Redis afeta também funcionalidades independentes do Celery descritas em [research-redis.md](research-redis.md). Qualquer mudança posterior exige avaliação dos responsáveis, plano de reversão e tratamento de mensagens pendentes; esta pesquisa não autoriza alteração de serviços.
