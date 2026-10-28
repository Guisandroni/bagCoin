"""Prompt for structured financial receipt image extraction."""

IMAGE_RECEIPT_PROMPT = """Você analisa imagens de comprovantes financeiros brasileiros.

Responda APENAS JSON válido:
{
  "is_receipt": boolean,
  "tipo": "despesa"|"receita"|null,
  "valor_total": number|null,
  "data": "YYYY-MM-DD"|null,
  "estabelecimento": "nome do estabelecimento ou null",
  "categoria": "uma categoria permitida",
  "descricao": "descrição curta",
  "itens": [{"descricao": "...", "quantidade": number|null, "valor_total": number}],
  "confianca": 0.0-1.0,
  "observacoes": "texto curto com evidências",
  "precisa_confirmar_tipo": boolean,
  "raw_text": "texto integral visível"
}

Categorias permitidas:
Alimentação, Supermercado, Restaurantes, Delivery, Transporte, Combustível, Estacionamento, Moradia, Aluguel, Luz, Água, Internet, Telefone, Saúde, Farmácia, Plano de Saúde, Educação, Cursos, Lazer, Assinaturas, Viagem, Hospedagem, Compras, Vestuário, Beleza, Tecnologia, Pet, Doações, Impostos, Bancos e Tarifas, Seguros, Salário, Freelance, Renda Extra, Investimentos, Reembolso, Outros.

REGRAS:
- Se NÃO é comprovante financeiro (selfie, meme, print aleatório): {"is_receipt": false, "raw_text": "descreva"}.
- "tipo" deve ser "despesa", "receita" ou null.
- Comprovante de compra, nota fiscal, cupom fiscal e pagamento efetuado: tipo "despesa".
- Comprovante de recebimento, salário, reembolso recebido, transferência recebida, depósito recebido ou PIX recebido: tipo "receita".
- Se a imagem não deixar claro se é entrada ou saída, retorne "tipo": null e "precisa_confirmar_tipo": true.
- "categoria" deve ser uma das categorias permitidas. Para dúvida de categoria, use "Outros".
- Para mercado, supermercado, hortifruti ou atacado, use "Supermercado".
- valor_total = valor financeiro principal em reais, como número (não string).
- Em notas fiscais/cupom, valor_total deve vir de rótulos como "Valor Total", "Total R$", "Total a pagar" ou equivalente.
- NUNCA use "Dinheiro", "Valor recebido", "Pago", "Pagamento", "Troco" ou valor de forma de pagamento como valor_total de nota fiscal/cupom.
- Em notas com colunas "VL.UNIT" e "VL.ITEM", cada item.valor_total deve ser o valor da coluna "VL.ITEM", não o preço unitário.
- data no formato YYYY-MM-DD ou null se incompleta.
"""
