# Feature Specification: Estabilização operacional do bagCoin

**Feature Branch**: nenhuma criada; destino `develop`

**Created**: 2026-10-29

**Status**: Draft

**Input**: `patches/plano-estabilizacao.md`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Executar o ambiente com confiança (Priority: P1)

Como pessoa desenvolvedora, quero iniciar e verificar os serviços essenciais usando os ambientes disponibilizados, para trabalhar com uma configuração reproduzível e preservar os dados existentes.

**Why this priority**: Um ambiente que não pode ser construído impede o desenvolvimento e a validação.

**Independent Test**: Construir as imagens relevantes, iniciar os serviços essenciais localmente e verificar a disponibilidade da aplicação e de suas dependências.

**Acceptance Scenarios**:

1. **Given** os pré-requisitos e configurações locais disponíveis, **When** o ambiente de desenvolvimento é iniciado, **Then** os serviços essenciais ficam disponíveis e respondem às verificações de saúde.
2. **Given** configurações de frontend e produção, **When** elas são validadas e suas imagens relevantes são construídas, **Then** não dependem de caminhos inexistentes ou de um processo incompatível com a aplicação.
3. **Given** dados persistidos anteriormente, **When** o ambiente corrigido é utilizado, **Then** seus volumes e dados permanecem disponíveis.

### User Story 2 - Proteger alterações na branch de desenvolvimento (Priority: P2)

Como pessoa responsável por revisão, quero que alterações propostas para `develop` passem por verificações obrigatórias, para identificar problemas antes da integração.

**Why this priority**: Verificações automáticas reduzem a chance de integrar regressões.

**Independent Test**: Abrir uma proposta para `develop` e confirmar a execução e o bloqueio das verificações obrigatórias.

**Acceptance Scenarios**:

1. **Given** uma proposta para `develop`, **When** as verificações são iniciadas, **Then** os controles aplicáveis do backend e frontend são executados e reportados.
2. **Given** uma verificação obrigatória com falha, **When** a proteção está configurada, **Then** a integração é bloqueada até a resolução.
3. **Given** falta de permissão para configurar a proteção, **When** os controles forem entregues, **Then** a configuração pendente e seus nomes são registrados.

### User Story 3 - Decidir sobre infraestrutura assíncrona (Priority: P3)

Como responsável pela operação, quero conhecer os usos e dependências da infraestrutura assíncrona para decidir quais serviços são necessários com base em evidências.

**Why this priority**: A decisão afeta operação e disponibilidade e não deve presumir que serviços estão ociosos.

**Independent Test**: Revisar o inventário de produtores, consumidores, agendamentos e dependências, junto com a recomendação e suas limitações.

**Acceptance Scenarios**:

1. **Given** os serviços assíncronos existentes, **When** a investigação é concluída, **Then** seus usos, possíveis produtores externos e impactos das alternativas são registrados.
2. **Given** um serviço compartilhado por outros recursos, **When** a recomendação é formulada, **Then** seus usos independentes são considerados e nenhum serviço é removido sem decisão aprovada.

### User Story 4 - Consultar instruções operacionais confiáveis (Priority: P4)

Como pessoa desenvolvedora ou operadora, quero instruções coerentes com os ambientes finais para iniciar, verificar e entender o sistema.

**Why this priority**: Documentação consistente permite reproduzir as melhorias e reduz dúvidas operacionais.

**Independent Test**: Comparar as instruções atualizadas com os ambientes e verificações entregues.

**Acceptance Scenarios**:

1. **Given** as configurações finais, **When** a documentação é revisada, **Then** portas, comandos, verificações e responsabilidades correspondem ao comportamento entregue.
2. **Given** a investigação assíncrona concluída, **When** a documentação descreve os serviços, **Then** distingue funções reais de tarefas de exemplo.

### Edge Cases

- A falta de credenciais ou permissões impede apenas as verificações dependentes; o bloqueio e a evidência são registrados.
- Uma verificação existente falha: a falha é corrigida ou registrada antes de declarar a etapa concluída.
- Produtores externos não podem ser confirmados: a recomendação explicita a incerteza e mantém os serviços.
- A validação de produção não deve publicar ou implantar a aplicação nem remover dados.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Os ambientes de desenvolvimento, frontend e produção DEVEM referenciar a aplicação existente e permitir a construção das imagens relevantes.
- **FR-002**: Os serviços essenciais locais DEVEM iniciar e permitir verificar a disponibilidade da aplicação e de suas dependências.
- **FR-003**: As alterações DEVEM preservar volumes, redes, configurações necessárias e dados existentes.
- **FR-004**: Alterações em `develop` e propostas destinadas a ela DEVEM acionar os controles relevantes, mantendo os gatilhos existentes.
- **FR-005**: A proteção de `develop` DEVE exigir as verificações aplicáveis de backend e frontend, incluindo análise estática, testes e construção; falhas DEVEM impedir a integração quando a proteção estiver disponível.
- **FR-006**: A estabilidade dos testes de ponta a ponta DEVE ser avaliada antes de torná-los obrigatórios; eles não serão bloqueio inicial.
- **FR-007**: A investigação DEVE documentar tarefas, produtores, consumidores, agendamentos, dependências e possíveis produtores externos, além de recomendar alternativas e seus impactos.
- **FR-008**: Serviços assíncronos DEVEM permanecer ativos até que uma decisão posterior aprove sua alteração; usos de armazenamento compartilhado DEVEM ser avaliados separadamente.
- **FR-009**: A documentação operacional DEVE refletir portas, comandos, verificações e responsabilidades dos serviços após as alterações.
- **FR-010**: Cada entrega DEVE registrar suas verificações e quaisquer falhas, permissões insuficientes ou itens pendentes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Os três ambientes identificados passam na validação de configuração e na construção das imagens relevantes.
- **SC-002**: Uma execução local inicia os serviços essenciais e confirma a disponibilidade da aplicação e de suas dependências.
- **SC-003**: Uma proposta para `develop` apresenta todos os controles obrigatórios definidos e uma falha nesses controles bloqueia a integração quando a proteção está disponível.
- **SC-004**: O relatório assíncrono cobre todos os serviços avaliados, indica incertezas sobre produtores externos e apresenta uma recomendação com impactos.
- **SC-005**: Todas as portas, comandos e responsabilidades atualizados na documentação conferem com a configuração final.

## Assumptions

- As entregas serão organizadas em PRs separados na ordem Compose, CI, investigação assíncrona e documentação.
- A branch de destino é `develop`; a aplicação e os dados existentes permanecem compatíveis.
- Não há mudança prevista de contratos públicos ou modelo de dados, nem deploy de produção.
- A proteção de branch depende das permissões disponíveis; a falta delas será registrada.
- A investigação inicial foi estática e não confirmou produtores externos.
