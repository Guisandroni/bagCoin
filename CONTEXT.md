# bagCoin — domínio financeiro pessoal

Assistente financeiro pessoal com IA integrada via WhatsApp e Telegram. Gerencia transações, orçamentos, metas e relatórios.

## Language

### Core

**Transação**:
Registro financeiro individual — toda entrada ou saída de dinheiro que o usuário quer rastrear. Sempre tem um tipo (`EXPENSE` ou `INCOME`), um valor, e uma categoria.
_Avoid_: lançamento, movimento, registro financeiro

**Categoria**:
Classificação atribuída a cada transação (ex: Alimentação, Transporte, Moradia). As categorias são hierárquicas e podem ser padrão (default) ou criadas pelo usuário.
_Avoid_: tag, label, grupo

**Orçamento**:
Limite mensal de gasto definido para uma categoria específica. O sistema compara o total gasto na categoria com o limite para gerar alertas.
_Avoid_: budget, teto, cota

**Meta**:
Objetivo financeiro com valor-alvo, prazo e progresso acumulado. O usuário contribui valores ao longo do tempo até atingir o target.
_Avoid_: goal, objetivo, reserva

**Relatório**:
Documento PDF ou CSV gerado sob demanda com resumo de transações, orçamentos e metas em um período.
_Avoid_: report, extrato, demonstrativo

**Conta**:
Conta bancária ou carteira que o usuário registra para controle de saldo.
_Avoid_: account, carteira, banco

**Cartão de Crédito**:
Cartão registrado pelo usuário com bandeira, limite e dia de fechamento.
_Avoid_: credit card, crédito

### Identidade

**Usuário**:
A identidade unificada que representa uma pessoa real no sistema. Um mesmo Usuário pode acessar via web (email/senha) e via bot (WhatsApp/Telegram). É a entidade raiz de ownership de todos os dados financeiros.
_Avoid_: User, conta, perfil, cliente

**Canal**:
A superfície pela qual o usuário interage com o sistema: `web` (frontend Next.js), `whatsapp` ou `telegram`.
_Avoid_: plataforma, interface, origem

### Conversação

**Conversa**:
Histórico de mensagens trocadas entre o usuário e o assistente em um canal. Conversas do chat web e conversas do bot são modelos separados, mas ambas pertencem ao mesmo Usuário.
_Avoid_: chat, thread, sessão

**Mensagem**:
Uma entrada individual em uma Conversa — pode ser texto, áudio, imagem ou documento.
_Avoid_: message, fala, interação

**Confirmação Pendente**:
Ação financeira que o agente detectou mas precisa de aprovação explícita do usuário antes de persistir (ex: importação de extrato com múltiplas transações).
_Avoid_: pending action, ação pendente, aprovação

### Agentes

**Intenção**:
A classificação que o agente atribui a cada mensagem recebida, determinando qual nó do grafo vai processá-la (ex: `REGISTER_EXPENSE`, `QUERY_DATA`, `CREATE_BUDGET`).
_Avoid_: intent, propósito, objetivo da mensagem

**Agente**:
Um nó no grafo LangGraph que executa uma etapa do pipeline: classificar, extrair, consultar, gerar relatório, responder. O grafo inteiro é o "orquestrador".
_Avoid_: node, handler, módulo de IA

**Extração**:
O processo de transformar uma mensagem em linguagem natural (texto, áudio, imagem) em dados financeiros estruturados (valor, tipo, categoria, descrição, data).
_Avoid_: parsing, interpretação, NLP

**Multimodal**:
A capacidade do agente de processar entradas que não são texto: áudio (transcrição), imagem (OCR de comprovante), documento (PDF/CSV de extrato bancário).
_Avoid_: media processing, upload

### Recorrência

**Transação Recorrente**:
Uma transação que se repete automaticamente em intervalo fixo (semanal, mensal, anual). Detectada pelo agente quando o usuário usa termos como "mensalmente", "fixo", "todo mês".
_Avoid_: recurring, fixa, assinatura

## Avoid

- Use **Transação** — não lançamento, movimento ou registro.
- Use **Categoria** — não tag, label ou grupo.
- Use **Usuário** — não conta, cliente, ou user account.
- Use **Intenção** — não intent ou propósito.
- Use **Canal** — não plataforma ou origem.
