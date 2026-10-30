<!--
Sync Impact Report
Version: scaffold → 1.0.0
Modified principles: placeholders → five initial principles
Added sections: Core Principles, Technical Constraints, Development Workflow, Governance
Removed sections: none
Follow-up: confirm the original ratification date.
-->
# Constituição do bagCoin

## Core Principles

### I. Domínio e identidade compartilhados

Mudanças financeiras DEVEM usar os conceitos de `CONTEXT.md` e preservar o vínculo dos dados ao usuário correto em todos os canais. Alterações de terminologia ou decisões arquiteturais DEVEM atualizar a documentação de domínio aplicável.

### II. Segurança e integridade financeira

Operações DEVEM validar entradas nas fronteiras, verificar autenticação e escopo do usuário e preservar os dados existentes. Ações que exigem confirmação explícita DEVEM respeitar esse fluxo antes da persistência. Credenciais e dados sensíveis NÃO DEVEM ser expostos em código, respostas ou logs.

### III. Limites explícitos e simplicidade

Mudanças DEVEM aproveitar componentes e padrões existentes e manter responsabilidades claras entre canais, API, serviços, agentes e persistência. Novas abstrações e dependências DEVEM resolver uma necessidade atual demonstrável.

### IV. Verificação proporcional ao risco

Cada mudança DEVE ser verificada com testes ou verificações apropriados ao comportamento alterado. Regras financeiras, autorização, persistência e integração entre componentes DEVEM ter cobertura dos cenários relevantes, incluindo falhas e limites. Falhas ou testes não executados DEVEM ser informados na entrega.

### V. Operação reproduzível e observável

Configurações, comandos operacionais e documentação DEVEM refletir o comportamento real. Mudanças operacionais DEVEM preservar tratamento de erros e permitir diagnóstico sem expor segredos ou dados financeiros. O uso de infraestrutura assíncrona DEVE corresponder às necessidades efetivas do sistema.

## Technical Constraints

- O backend em `apps/server` e os contratos da API versionada DEVEM permanecer compatíveis, salvo quando uma mudança incompatível for explicitamente definida e comunicada.
- Migrações de dados DEVEM preservar informações existentes e descrever pré-requisitos e riscos.
- `CONTEXT.md` e `docs/adr/` são as referências de domínio e decisões arquiteturais.

## Development Workflow

- Mudanças DEVEM ter escopo delimitado e incluir os consumidores, configurações e documentação afetados. A revisão DEVE considerar segurança, integridade dos dados e compatibilidade.
- PRs para `develop` DEVEM executar as verificações aplicáveis de backend e frontend; alterações de infraestrutura DEVEM incluir validação das configurações e, quando possível, smoke tests.
- Problemas conhecidos e verificações pendentes DEVEM ser comunicados explicitamente.

## Governance

Esta constituição orienta o desenvolvimento em conjunto com as instruções vigentes do repositório e as instruções explícitas do usuário. Emendas DEVEM registrar a motivação, o impacto e a versão, e ser aprovadas pelos responsáveis pelo projeto. A revisão DEVE verificar a conformidade com os princípios aplicáveis e justificar exceções.

O versionamento é semântico: MAJOR para remoção ou redefinição incompatível de princípios; MINOR para novos princípios ou expansão material; PATCH para esclarecimentos sem mudança de significado. A data de alteração DEVE ser atualizada em cada emenda.

**Version**: 1.0.0 | **Ratified**: TODO(RATIFICATION_DATE): confirmar data de aprovação | **Last Amended**: 2026-10-29
