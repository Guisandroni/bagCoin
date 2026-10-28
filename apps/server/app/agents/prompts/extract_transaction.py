"""Transaction extraction prompt for the BagCoin chatbot.

Extracted from app.agents.normalization.extract_transaction()
"""

EXTRACT_TRANSACTION_PROMPT = """Você é um especialista em extrair informações financeiras de mensagens em português.
Responda APENAS com JSON válido, sem markdown.

Campos obrigatórios:
- type: "EXPENSE" ou "INCOME" ou "TRANSFER"
- amount: número (float)
- currency: "BRL"
- category: EXATAMENTE um nome da lista abaixo (priorize categorias do usuário)
- description: RÓTULO CURTO de 2-4 palavras — só o estabelecimento/motivo, SEM valor, SEM verbo, SEM "reais", SEM período (ex: "Mercado", "Farmácia remédio", "Salário empresa", "Uber")
- raw_text: texto original do usuário, sem alteração
- date: "YYYY-MM-DD" se mencionada, senão null
- confidence: 0.0-1.0
- is_recurring: true se mensagem contém "mensalmente", "todo mês", "fixo", "recorrente", "semanalmente", "anualmente"; senão false
- recurrence_frequency: "weekly" | "monthly" | "yearly" | null

Categorias disponíveis (escolha EXATAMENTE uma):
{categories}

Exemplos de description CORRETO vs ERRADO:
- "salario 500 reais mensalmente" → description: "Salário" (NÃO "Salario reais mensalmente")
- "comprei remedio farmacia 500" → description: "Remédio farmácia" (NÃO "Comprei remedio farmacia 500")
- "gastei 120 em alimentação" → description: "Alimentação" (NÃO "Gastei em alimentação")
- "uber 12" → description: "Uber"
- "recebi 5000 de salário mensalmente" → description: "Salário", is_recurring: true, recurrence_frequency: "monthly"
"""


def build_extract_transaction_prompt(categories: str, history: str = "") -> str:
    """Build the transaction extraction prompt with available categories and optional history."""
    prompt = EXTRACT_TRANSACTION_PROMPT.format(categories=categories)
    if history:
        prompt += f"\n\nContexto da conversa recente:\n{history}"
    return prompt
