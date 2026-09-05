"""Budget and goal extraction prompts for the BagCoin chatbot.

Extracted from app.agents.budget_goal._extract_with_llm()
"""

# Prompt templates for each extraction type
EXTRACT_PROMPTS: dict[str, str] = {
    "budget": """Extraia dados de orçamento da mensagem.
Retorne APENAS JSON: {"name": "categoria", "total_limit": 3000.0, "period": "monthly"}
- name: a categoria/nome do orçamento (ex: alimentação, transporte)
- total_limit: valor numérico (número, sem R$)
- period: sempre "monthly". O BagCoin cria orçamentos por categoria a cada 30 dias.
- não extraia nem peça descrição para orçamento.
Exemplos:
"orçamento 4000 alimentação" -> {"name": "alimentação", "total_limit": 4000.0, "period": "monthly"}
"alimentação 4000" -> {"name": "alimentação", "total_limit": 4000.0, "period": "monthly"}
Se um campo não estiver na mensagem, omita do JSON.""",

    "goal": """Extraia dados de meta financeira da mensagem.
Retorne APENAS JSON: {"title": "viagem", "target_amount": 10000.0, "deadline": "12/2026"}
- title: o objetivo da meta
- target_amount: valor numérico
- deadline: prazo opcional no formato "MM/YYYY". Hoje é {today_iso}.
  Se o usuário disser só o mês (ex: "outubro"), use o ANO ATUAL se esse mês ainda não passou,
  senão use ANO ATUAL + 1. NUNCA retorne uma data no passado.
Se um campo não estiver na mensagem, omita do JSON.""",

    "contribute": """Extraia dados de contribuição para meta.
Retorne APENAS JSON: {"goal_identifier": "viagem", "amount": 500.0}
- goal_identifier: nome da meta ou número (ex: "viagem", "meta 1", "bike")
- amount: valor a adicionar
Se um campo não estiver na mensagem, omita do JSON.""",

    "delete_budget": """Extraia qual orçamento excluir.
Retorne APENAS JSON: {"name": "alimentação"} ou {"all": true} para excluir todos.
Se a mensagem disser "todos", "todas" ou "tudo", retorne {"all": true}.""",

    "update_budget": """Extraia dados para atualizar orçamento.
Retorne APENAS JSON: {"name": "alimentação", "total_limit": 4000.0}
- name: nome do orçamento a atualizar
- total_limit: novo valor do limite
Se um campo não estiver na mensagem, omita do JSON.""",

    "update_goal": """Extraia dados para atualizar meta.
Retorne APENAS JSON: {"goal_identifier": "viagem", "new_target": 12000.0, "new_title": null, "deadline": "06/2027"}
- goal_identifier: nome da meta
- new_target: novo valor total (opcional)
- new_title: novo nome (opcional)
- deadline: novo prazo (opcional, formato "MM/YYYY"). Hoje é {today_iso}.
  Se o usuário disser só o mês, use o ANO ATUAL se esse mês ainda não passou,
  senão use ANO ATUAL + 1. NUNCA retorne uma data no passado.
Se um campo não estiver na mensagem ou não houver alteração, omita do JSON.""",
}
