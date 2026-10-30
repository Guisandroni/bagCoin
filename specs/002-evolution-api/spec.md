# Feature Specification: Migração WhatsApp para Evolution API

**Feature Branch**: `feat/evolution-api` | **Created**: 2026-10-29 | **Status**: Draft

**Input**: `patches/plano-evolution-api.md`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Conversar por WhatsApp (Priority: P1)

Como usuário, quero enviar mensagens ao assistente financeiro e receber respostas para operar meus dados pelo WhatsApp.

**Why this priority**: O processamento de mensagens é a função central da integração.

**Independent Test**: Enviar mensagem individual usando um número conectado e verificar o processamento e a resposta.

**Acceptance Scenarios**:

1. **Given** a instância conectada e uma mensagem de texto individual, **When** o usuário envia a mensagem, **Then** o assistente processa a intenção e responde ao remetente.
2. **Given** mensagem de grupo ou enviada pelo próprio sistema, **When** o evento chega, **Then** nenhuma ação financeira é executada e nenhuma resposta automática é enviada.
3. **Given** evento repetido, **When** é reentregue, **Then** não cria operação financeira duplicada.
4. **Given** uma mensagem não autenticada ou de instância diferente, **When** recebida, **Then** é recusada sem processamento.

### User Story 2 - Enviar mídia e receber relatório (Priority: P2)

Como usuário, quero enviar áudio, imagem e documentos e receber relatórios, para usar os fluxos financeiros já disponíveis.

**Why this priority**: Mídias e relatórios são capacidades existentes que precisam permanecer disponíveis.

**Independent Test**: Enviar cada tipo de mídia suportado e solicitar relatório PDF a partir do número de teste.

**Acceptance Scenarios**:

1. **Given** áudio, imagem ou documento válido, **When** enviado em conversa individual, **Then** o conteúdo é encaminhado ao processamento existente.
2. **Given** um relatório gerado, **When** a resposta é enviada, **Then** o usuário recebe o documento correspondente.
3. **Given** mídia inválida ou indisponível, **When** ocorre falha na leitura, **Then** nenhuma transação é criada indevidamente e a falha não é informada como sucesso.

### User Story 3 - Vincular identidade com segurança (Priority: P3)

Como usuário, quero continuar vinculando meu número à conta existente, mantendo a separação dos meus dados financeiros.

**Independent Test**: Vincular conta e número conhecidos e confirmar que mensagens usam os dados dessa conta.

**Acceptance Scenarios**:

1. **Given** número já vinculado, **When** chega uma mensagem válida, **Then** somente os dados do usuário vinculado são acessados.
2. **Given** identificador que não permite resolver um telefone com segurança, **When** chega uma mensagem, **Then** nenhum usuário é associado indevidamente e nenhuma operação financeira é executada.

### User Story 4 - Operar uma conexão compartilhada (Priority: P4)

Como operador, quero conectar e acompanhar uma instância compartilhada pelo painel, para disponibilizar o serviço sem gerenciar uma sessão por usuário.

**Independent Test**: Iniciar o ambiente isolado, conectar um número por QR e reiniciar os serviços, verificando o estado da sessão.

**Acceptance Scenarios**:

1. **Given** o ambiente configurado, **When** o operador conecta o número via painel, **Then** uma instância compartilhada atende às mensagens individuais.
2. **Given** uma instância previamente conectada, **When** os serviços reiniciam, **Then** os dados de sessão persistem e o estado de conexão pode ser verificado.

### Edge Cases

- Eventos concorrentes e reentregas não devem executar duas vezes uma ação financeira.
- Falhas de processamento ou envio não devem ser reconhecidas como sucesso nem repetidas cegamente com risco de duplicação.
- Credenciais ausentes ou inválidas devem impedir acesso não autorizado e não aparecer em logs.
- Mídias ausentes, inválidas ou excessivas devem ser rejeitadas sem persistência financeira indevida.
- A operação continua preservando dados existentes, Telegram e acesso web; não há deploy de produção.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE receber eventos autenticados da instância compartilhada e responder mensagens individuais de texto.
- **FR-002**: O sistema DEVE preservar processamento de imagem, áudio e documento e envio de relatórios PDF.
- **FR-003**: O sistema DEVE ignorar mensagens próprias, de grupos e eventos não suportados.
- **FR-004**: O sistema DEVE deduplicar eventos estáveis e evitar operações financeiras duplicadas inclusive em reentregas e concorrência.
- **FR-005**: O sistema DEVE preservar vínculo entre telefone e usuário e rejeitar associação ambígua de identificadores.
- **FR-006**: O sistema DEVE preservar ordenação e fragmentação de respostas longas e relatar falhas sem expor segredos ou conteúdo sensível.
- **FR-007**: O operador DEVE conseguir conectar e inspecionar a instância pelo painel; dados da instância DEVEM persistir após reinício.
- **FR-008**: A infraestrutura DEVE isolar logicamente os dados da integração dos dados existentes e manter Telegram e web funcionais.
- **FR-009**: A integração antiga e suas referências operacionais DEVEM ser removidas somente após validar equivalência; volumes e sessões existentes não serão apagados automaticamente.
- **FR-010**: O projeto DEVE fornecer verificações automatizadas e roteiro local de testes reais sem depender das suítes removidas.

### Key Entities

- **Instância compartilhada**: conexão de WhatsApp e estado persistente administrado pelo operador.
- **Evento de mensagem**: identificador estável, remetente, tipo e conteúdo que determinam o processamento idempotente.
- **Vínculo de usuário**: associação confiável entre telefone e identidade financeira existente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma mensagem real de texto produz uma resposta ao número remetente sem criar registros em conta incorreta.
- **SC-002**: Áudio, imagem e documento são recebidos e um PDF é entregue em testes representativos.
- **SC-003**: Mensagens próprias, grupos, instância incorreta e eventos repetidos não criam ações financeiras; testes cobrem reentrega e concorrência.
- **SC-004**: A instância conectada mantém seus dados após um reinício e pode ser reconectada pelo operador quando necessário.
- **SC-005**: Os fluxos de Telegram e web continuam acessíveis e não são alterados por regressão observada no smoke test.

## Assumptions

- Uma instância compartilhada no mesmo servidor; gestão via painel Evolution.
- Número disponível para teste real, que requer internet; eventos simulados também são validados.
- Banco próprio e cache isolado nos serviços existentes; preservação dos dados atuais.
- Sem usuários online e sem deploy de produção; não é necessária transição sem interrupção.
- A versão candidata está fixada no plano base e sua compatibilidade será confirmada antes de uso.

- O usuário aceitou explicitamente o risco da v2.3.7 exclusivamente para teste local; produção exige versão corrigida. A execução dos testes está temporariamente suspensa por solicitação do usuário.
