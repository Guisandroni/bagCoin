"""Wizard extraction and correction prompts for the BagCoin chatbot.

Extracted from app.agents.wizard._extract_fields_with_llm() and _extract_correction_with_llm()
"""

# Default JSON format examples per wizard type
FIELD_EXAMPLES: dict[str, str] = {
    "create_budget": '{"name": "alimentação", "total_limit": 3000, "period": "monthly"}',
    "create_goal": '{"title": "viagem", "target_amount": 10000, "deadline": "12/2026"}',
    "update_goal": '{"goal_identifier": "bike", "amount": 500}',
    "contribute_goal": '{"goal_identifier": "bike", "amount": 500}',
}


def build_wizard_extract_prompt(wizard_type: str, field_example: str) -> str:
    """Build wizard field extraction prompt."""
    return f"""Você é um assistente que extrai dados de mensagens curtas em português.
O usuário está preenchendo um formulário de {wizard_type.replace("_", " ")}.

Extraia APENAS os campos presentes na mensagem do usuário.
Responda SEMPRE em JSON no formato: {field_example}

Regras:
- Se um campo não estiver na mensagem, omita do JSON (não use null)
- total_limit, target_amount, amount: números apenas (ex: 3000, 10000.50)
- deadline: string no formato "MM/YYYY" ou "DD/MM/YYYY"
- name/title: string, sem incluir o valor monetário
- Para create_budget, period deve ser sempre "monthly"; orçamento não tem descrição.
- goal_identifier: nome da meta ou número dela

Exemplos de extração:
Mensagem: "Orçamento de R$ 3000 para alimentação mensal"
→ {{"name": "alimentação", "total_limit": 3000, "period": "monthly"}}

Mensagem: "alimentação 4000"
→ {{"name": "alimentação", "total_limit": 4000, "period": "monthly"}}

Mensagem: "Meta de R$ 10000 para viagem até 12/2026"
→ {{"title": "viagem", "target_amount": 10000, "deadline": "12/2026"}}

Mensagem: "guardar 500 na meta bike"
→ {{"goal_identifier": "bike", "amount": 500}}"""


WIZARD_CORRECTION_PROMPT = """O usuário quer corrigir um campo. Identifique qual campo e novo valor.
Responda em JSON: {"field_name": "novo_valor"}
Exemplo: "muda para 4000" → {"total_limit": 4000}
"não é viagem, é bike" → {"title": "bike"}
"""
