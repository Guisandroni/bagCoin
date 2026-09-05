"""Shared financial category taxonomy used by web and agents."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class FinancialCategory:
    name: str
    color: str
    type: str
    emoji: str
    aliases: tuple[str, ...] = ()


DEFAULT_FINANCIAL_CATEGORIES: tuple[FinancialCategory, ...] = (
    FinancialCategory("Alimentação", "#FF6D00", "despesa", "🍽️", ("comida", "lanche", "padaria", "feira")),
    FinancialCategory("Supermercado", "#FFC107", "despesa", "🛒", ("mercado", "hortifruti")),
    FinancialCategory("Restaurantes", "#FF3B30", "despesa", "🍴", ("restaurante", "bar", "cafeteria", "jantar", "almoco", "pizza")),
    FinancialCategory("Delivery", "#FF7043", "despesa", "🍔", ("ifood", "rappi", "uber eats")),
    FinancialCategory("Transporte", "#0057FF", "despesa", "🚗", ("uber", "99", "taxi", "onibus", "metro", "passagem")),
    FinancialCategory("Combustível", "#001F54", "despesa", "⛽", ("gasolina", "alcool", "etanol", "diesel")),
    FinancialCategory("Estacionamento", "#4FC3F7", "despesa", "🅿️", ("pedagio", "zona azul")),
    FinancialCategory("Moradia", "#7B1FA2", "despesa", "🏠", ("casa", "reforma", "manutencao")),
    FinancialCategory("Aluguel", "#8E24AA", "despesa", "🏘️", ("condominio", "financiamento")),
    FinancialCategory("Luz", "#FFD600", "despesa", "💡", ("energia", "eletricidade")),
    FinancialCategory("Água", "#00B8D4", "despesa", "💧", ("agua", "esgoto")),
    FinancialCategory("Internet", "#00ACC1", "despesa", "🌐", ("wifi", "fibra", "banda larga")),
    FinancialCategory("Telefone", "#006064", "despesa", "📱", ("celular", "recarga", "tim", "vivo", "claro", "oi")),
    FinancialCategory("Saúde", "#00C853", "despesa", "🏥", ("medico", "consulta", "exame", "hospital")),
    FinancialCategory("Farmácia", "#FF1493", "despesa", "💊", ("farmacia", "remedio", "medicamento")),
    FinancialCategory("Plano de Saúde", "#1DE9B6", "despesa", "🩺", ("plano de saude", "convenio")),
    FinancialCategory("Educação", "#AEEA00", "despesa", "🎓", ("faculdade", "escola", "livro", "material escolar")),
    FinancialCategory("Cursos", "#556B2F", "despesa", "📚", ("curso", "idioma", "aula")),
    FinancialCategory("Lazer", "#D500F9", "despesa", "🎮", ("cinema", "show", "teatro", "festa", "hobby", "jogo")),
    FinancialCategory("Assinaturas", "#3F51B5", "despesa", "🎬", ("netflix", "spotify", "youtube", "streaming", "saas")),
    FinancialCategory("Viagem", "#00ACC1", "despesa", "✈️", ("turismo", "passeio", "passagem aerea")),
    FinancialCategory("Hospedagem", "#006064", "despesa", "🏨", ("hotel", "airbnb", "pousada")),
    FinancialCategory("Compras", "#FF1493", "despesa", "🛍️", ("shopping", "loja")),
    FinancialCategory("Vestuário", "#B388FF", "despesa", "👕", ("roupa", "calcado", "sapato", "camiseta")),
    FinancialCategory("Beleza", "#FA8072", "despesa", "💅", ("salao", "barbearia", "manicure", "cosmetico")),
    FinancialCategory("Tecnologia", "#424242", "despesa", "💻", ("eletronico", "computador", "software", "app", "console")),
    FinancialCategory("Pet", "#E76F51", "despesa", "🐾", ("racao", "veterinario", "petshop")),
    FinancialCategory("Doações", "#AEEA00", "despesa", "🤝", ("doacao", "caridade", "igreja", "ong")),
    FinancialCategory("Impostos", "#800020", "despesa", "🧾", ("irpf", "iptu", "ipva", "darf", "taxa")),
    FinancialCategory("Bancos e Tarifas", "#111111", "despesa", "🏦", ("tarifa", "banco", "juros", "anuidade")),
    FinancialCategory("Seguros", "#00897B", "despesa", "🛡️", ("seguro", "apolice")),
    FinancialCategory("Salário", "#00C853", "receita", "💰", ("salario", "ordenado", "pagamento")),
    FinancialCategory("Freelance", "#1DE9B6", "receita", "💼", ("freela", "consultoria")),
    FinancialCategory("Renda Extra", "#00B8D4", "receita", "💵", ("bonus", "comissao", "mesada", "presente")),
    FinancialCategory("Investimentos", "#3F51B5", "investimento", "📈", ("investimento", "dividendo", "rendimento")),
    FinancialCategory("Reembolso", "#00897B", "receita", "↩️", ("estorno", "devolucao")),
    FinancialCategory("Outros", "#424242", "despesa", "💳", ("outro", "geral")),
)


def normalize_category_key(value: str) -> str:
    return (
        unicodedata.normalize("NFKD", value.strip().lower())
        .encode("ASCII", "ignore")
        .decode("ASCII")
    )


def resolve_default_category_name(value: str | None) -> str:
    if not value or not value.strip():
        return "Outros"
    normalized = normalize_category_key(value)
    for category in DEFAULT_FINANCIAL_CATEGORIES:
        if normalize_category_key(category.name) == normalized:
            return category.name
        if any(normalize_category_key(alias) == normalized for alias in category.aliases):
            return category.name
    for category in DEFAULT_FINANCIAL_CATEGORIES:
        if normalized in {normalize_category_key(alias) for alias in category.aliases}:
            return category.name
        if normalized in normalize_category_key(category.name):
            return category.name
    return value.strip().capitalize()


def category_color(name: str) -> str:
    resolved = resolve_default_category_name(name)
    for category in DEFAULT_FINANCIAL_CATEGORIES:
        if category.name == resolved:
            return category.color
    return "#0057FF"


def category_type(name: str) -> str:
    resolved = resolve_default_category_name(name)
    for category in DEFAULT_FINANCIAL_CATEGORIES:
        if category.name == resolved:
            return category.type
    return "despesa"


def category_emoji(name: str) -> str:
    resolved = resolve_default_category_name(name)
    for category in DEFAULT_FINANCIAL_CATEGORIES:
        if category.name == resolved:
            return category.emoji
    return "💳"


def default_category_names() -> list[str]:
    return [category.name for category in DEFAULT_FINANCIAL_CATEGORIES]
