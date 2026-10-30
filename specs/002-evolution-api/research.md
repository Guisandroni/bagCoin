# Pesquisa e gates

## Arquitetura

**Decisão**: backend comunica diretamente com Evolution; uma instância compartilhada; painel controla QR; PostgreSQL e Redis compartilhados com banco e prefixo isolados. **Justificativa**: projeto sem usuários em produção e camada intermediária sem necessidade. **Alternativa**: manter bridge aumenta serviços e acoplamento operacional.

## Versão e segurança

**Decisão**: a candidata v2.3.7 do plano base não é autorização para conexão real. Antes de conectar conta, verificar no artefato efetivo uma versão do Baileys corrigida conforme [GHSA-qvv5-jq5g-4cgg](https://github.com/WhiskeySockets/Baileys/security/advisories/GHSA-qvv5-jq5g-4cgg) e o estado da [issue Evolution #2686](https://github.com/evolution-foundation/evolution-api/issues/2686). Não assumir que tag ou release corrigiu a vulnerabilidade. Se nenhuma imagem segura e compatível estiver disponível, reportar bloqueio em vez de contorná-lo.

**Alternativa**: usar v2.3.7 sem verificação expõe sessão; RC sem validação não comprova correção. Fixar versão/digest somente após comprovação.

## Webhook e reentrega

**Decisão**: confirmar contrato exato de autenticação, tipos, dados e reentrega da versão segura antes de usar. O endpoint deve verificar instância, autenticação e limites; eventos concorrentes e falhas entre persistência e envio precisam de idempotência validada.

**Alternativa**: deduplicação em memória ou TTL isolado não garante preservação financeira após falhas e múltiplas réplicas.

Fontes primárias da versão 2.3.7 mostram `baileys` 7.0.0-rc.9 ([package.json](https://github.com/evolution-foundation/evolution-api/blob/2.3.7/package.json)), afetado pelo advisory; a 2.4.0-rc2 também usa rc.9 ([package.json](https://github.com/evolution-foundation/evolution-api/blob/5624bda/package.json)). Uma branch mutável com rc.13 não é imagem estável comprovadamente segura. Confirmar build, dependências e licença antes de fixar imagem e conectar número real.

O código 2.3.7 aceita headers configuráveis no webhook por instância, não no global ([fonte](https://raw.githubusercontent.com/evolution-foundation/evolution-api/2.3.7/src/api/integrations/event/webhook/webhook.controller.ts)). Usar segredo dedicado, não registrar payload completo que pode conter `apikey`, e revalidar esses contratos na versão efetivamente escolhida.

## Banco Evolution

**Decisão**: provisionar banco separado explicitamente e de forma idempotente, inclusive para volumes PostgreSQL já existentes; usar credenciais específicas e cache isolado. **Alternativa**: depender exclusivamente de scripts de inicialização não cobre volumes existentes. Não recriar volumes existentes nem automatizar operações destrutivas.

## Investigação de releases e imagens (2026-10-29)

- O [advisory do Baileys](https://github.com/WhiskeySockets/Baileys/security/advisories/GHSA-qvv5-jq5g-4cgg) classifica a vulnerabilidade de falsificação de mensagens como crítica e identifica a correção a partir de 7.0.0-rc12 na série 7. O [código oficial da tag 2.3.7](https://raw.githubusercontent.com/evolution-foundation/evolution-api/2.3.7/package.json) fixa 7.0.0-rc.9; o [código oficial da candidata 2.4.0-rc2](https://raw.githubusercontent.com/evolution-foundation/evolution-api/2.4.0-rc2/package.json) também fixa rc.9. Não usar essas versões com conta real com base apenas na tag.
- No momento da consulta, a [lista oficial de releases](https://github.com/evolution-foundation/evolution-api/releases) apresenta 2.4.0-rc2 como pré-release e v2.3.7 como versão estável mais recente. O [package.json da branch develop](https://raw.githubusercontent.com/evolution-foundation/evolution-api/develop/package.json) informa rc13, fora da faixa afetada pelo advisory específico, mas é uma branch mutável e não comprova um release ou digest auditado. O pré-release 2.4.0 também declara requisito de ativação de licença; suas condições e compatibilidade precisam de validação independente.
- O Docker Hub apresenta para [v2.3.7](https://hub.docker.com/layers/evoapicloud/evolution-api/v2.3.7/images/sha256-456b4104b0ddffbb092d6b3c0560a4ae86fc3e014e885b882aca4b1b371dfc81) o digest de índice `sha256:1bd8afc4a6cf48822e6cf02469aeae7bd35a12a6b616eacd1291926307f4d339` e para [2.4.0-rc2](https://hub.docker.com/layers/evoapicloud/evolution-api/2.4.0-rc2/images/sha256-0589281d448736759b98d11071066a3b9be3a1f19724802dd5867d9608a9584b) `sha256:b4a18ed5213d34a0845f841ba9afae1b67940457d021b42af863eae67dc2cfbd`. São referências de inventário, não evidência de imagem corrigida; não foram baixadas nem inspecionadas.
- **Alternativas a avaliar**: esperar release oficial corrigida; ou produzir imagem a partir de commit upstream imutável com dependência corrigida e revisar a proveniência, licença, demais vulnerabilidades, migrações, contratos e testes antes de aprová-la. Um fork de terceiros ou tag `homolog` demanda a mesma auditoria e não deve ser assumido seguro por alegação de versão.
- **Gate**: manter testes simulados e não conectar número real até identificar um artefato imutável, inspecionar a dependência efetivamente instalada e validar segurança, compatibilidade e licença. Filtrar eventos no webhook do bagCoin não corrige processamento vulnerável dentro da Evolution. A pesquisa não provou a segurança de nenhuma imagem candidata.

## Autorização para teste local (2026-10-30)

O usuário aceitou explicitamente executar a Evolution v2.3.7 vulnerável exclusivamente em ambiente local de teste; isso não torna a versão segura nem autoriza produção. A validação de imagem corrigida continua obrigatória antes de produção. A execução dos testes está suspensa por instrução do usuário.
