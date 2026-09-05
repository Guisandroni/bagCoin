"""Response templates for BagCoin agents.

Principles:
- Clean, humanized text
- Minimal emoji usage
- WhatsApp-friendly formatting
"""

from datetime import date, datetime
from typing import Any


_MONTHS_PT = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)

def _fmt_date(raw) -> str:
    """Format date/time to Brazilian day/month/year format."""
    if isinstance(raw, datetime):
        return raw.strftime("%d/%m/%Y")
    if isinstance(raw, date):
        return raw.strftime("%d/%m/%Y")
    if isinstance(raw, str):
        value = raw.strip()
        if not value:
            return ""
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            pass
        for fmt in ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"]:
            try:
                dt = datetime.strptime(value.split(".")[0], fmt.split(".")[0])
                return dt.strftime("%d/%m/%Y")
            except ValueError:
                continue
    return str(raw) if raw else ""


def _fmt_money(value: Any) -> str:
    """Format money in pt-BR without depending on system locale."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        amount = 0.0
    formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def _success_date(raw: Any) -> str:
    return _fmt_date(raw) or datetime.now().strftime("%d/%m/%Y")


def _transaction_sentence(row: dict[str, Any]) -> str:
    amount = row.get("amount") or row.get("valor") or row.get("total") or 0
    category = row.get("category") or row.get("categoria") or row.get("category_name") or "Outros"
    description = (
        row.get("description")
        or row.get("descricao")
        or row.get("name")
        or row.get("nome")
        or ""
    )
    date_val = row.get("transaction_date") or row.get("date") or row.get("data")
    desc_part = f" ({description})" if description else ""
    return f"Valor: {_fmt_money(amount)} em {category}{desc_part} no dia {_success_date(date_val)}."


def _fmt_deadline(raw) -> str:
    """Format a goal deadline as month/year in Portuguese."""
    if isinstance(raw, datetime):
        return f"{_MONTHS_PT[raw.month - 1]}/{raw.year}"
    if isinstance(raw, date):
        return f"{_MONTHS_PT[raw.month - 1]}/{raw.year}"
    if isinstance(raw, str):
        value = raw.strip()
        if not value:
            return ""
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return f"{_MONTHS_PT[dt.month - 1]}/{dt.year}"
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%Y"):
            try:
                dt = datetime.strptime(value, fmt)
                return f"{_MONTHS_PT[dt.month - 1]}/{dt.year}"
            except ValueError:
                continue
    return str(raw) if raw else ""


def period_label(period: str | None) -> str:
    """Return a Portuguese label for a budget period."""
    return {
        "daily": "Diário",
        "weekly": "Semanal",
        "monthly": "Mensal",
        "yearly": "Anual",
    }.get(period or "", period or "")


def greeting(name: str | None = None, greeting_time: str | None = None) -> str:
    prefix = greeting_time or "Oi"
    if name:
        return (
            f"{prefix}, {name}! Sou o BagCoin, seu assistente financeiro.\n\n"
            "O que vamos registrar hoje?"
        )
    return (
        f"{prefix}! Sou o BagCoin, seu assistente financeiro.\n\n"
        "Posso ajudar você a:\n"
        "- Registrar despesas e receitas\n"
        "- Consultar suas transações realizadas\n"
        "- Gerar relatórios em PDF\n"
        "- Definir orçamentos por categoria e metas\n\n"
        "O que vamos fazer hoje?"
    )


def help_menu() -> str:
    return (
        "Como usar o BagCoin:\n\n"
        " Voce pode registrar uma despesa:\n"
        "• Gastei R$ 35 no almoço\n"
        "• Mercado 240\n"
        "• Uber 30\n\n"
        " Ou registrar uma receita:\n"
        "• Recebi R$ 5000 de salario\n"
        "• Meu pai me mandou 170\n\n"
        " Voce pode consultar suas transações realizadas:\n"
        "• Quanto gastei hoje?\n"
        "• Despesas por categoria\n"
        "• Qual meu saldo?\n\n"
        " Voce pode definir orçamentos por categoria:\n"
        "• Crie um orçamento de R$ 3000 para a categoria alimentação\n"
        "• Crie um orçamento de R$ 1000 para a categoria transporte\n\n"
        " Voce pode definir metas financeiras:\n"
        "• Crie uma meta de R$ 10000 para a viagem de férias\n"
        "• Crie uma meta de R$ 5000 para a compra de um patinete\n\n"
        " Voce pode consultar suas metas:\n"
        "• Minhas metas\n"
        "• Metas por prazo\n"
        "• Progresso das metas\n"
    )


def transaction_confirmation(
    tx_type: str,
    amount: float,
    category: str,
    description: str,
    transaction_date: Any = None,
) -> str:
    """Return the fixed confirmation prompt for a pending transaction."""
    prefix = "💰 Receita" if str(tx_type).upper() == "INCOME" else "🧾 Despesa"
    clean_category = (category or "Outros").strip() or "Outros"
    clean_description = (description or "Sem descrição").strip() or "Sem descrição"
    return (
        f"{prefix}: {_fmt_money(amount)} em {clean_category} ({clean_description}) "
        f"no dia {_success_date(transaction_date)}.\n\n"
        "Confirma esta transação?\n"
        "Se algo estiver errado, me diga o ajuste. Ex: \"valor era 200\"."
    )


def transaction_registered(
    tx_type: str,
    amount: float,
    category: str,
    description: str,
    transaction_date: Any = None,
) -> str:
    """Return the short success message after a transaction is saved."""
    _ = (tx_type, amount, category, description, transaction_date)
    return "✅ Transação registrada com sucesso!"


def document_imported(
    transactions: list[dict[str, Any]],
    skipped: int = 0,
    errors: list[str] | None = None,
    *,
    label: str = "Documento",
) -> str:
    """Return a user-facing import confirmation based on persisted rows."""
    errors = errors or []
    imported = len(transactions)
    prefix = f"{label} importado com sucesso!"

    suffix_parts = []
    if skipped:
        plural = "s" if skipped != 1 else ""
        suffix_parts.append(f"{skipped} duplicata{plural} ignorada{plural}.")
    if errors:
        error_count = len(errors)
        plural = "s" if error_count != 1 else ""
        minor_suffix = "es" if error_count != 1 else ""
        suffix_parts.append(f"{error_count} erro{plural} menor{minor_suffix} ignorado{plural}.")
    suffix = f" {' '.join(suffix_parts)}" if suffix_parts else ""

    if imported == 0:
        if skipped:
            return (
                f"📄 {label} processado.\n\n"
                "🔁 Nenhuma transação nova foi importada.\n"
                "As transações encontradas já estavam duplicadas e foram ignoradas."
            )
        return f"📄 {label} processado.\n\nNenhuma transação nova foi importada."

    if imported == 1:
        return f"{prefix} {_transaction_sentence(transactions[0])} ✅{suffix}"

    lines = [f"{prefix} {imported} transações importadas:"]
    for index, tx in enumerate(transactions, 1):
        lines.append(f"{index}. {_transaction_sentence(tx)}")
    if suffix_parts:
        lines.append(" ".join(suffix_parts))
    lines.append("✅")
    return "\n".join(lines)


def non_financial_media(kind: str = "imagem") -> str:
    label = "imagem" if kind == "image" else "documento" if kind == "document" else kind
    return (
        f"🖼️ Não consegui processar essa {label}.\n\n"
        "Ela não parece conter uma nota fiscal, recibo, comprovante ou documento financeiro aceito.\n"
        "Envie uma imagem financeira ou descreva a transação em texto."
    )


def query_summary(summary: str) -> str:
    """Wrap query summary in clean wrapper."""
    return summary


def report_summary(period_label: str, income: float, expense: float, balance: float) -> str:
    return (
        f"Relatório Financeiro\n"
        f"Período: {period_label}\n\n"
        f"Receitas: R$ {income:,.2f}\n"
        f"Despesas: R$ {expense:,.2f}\n"
        f"Saldo: R$ {balance:,.2f}"
    )


def budget_created(name: str, limit: float, period: str, updated: bool = False) -> str:
    verb = "atualizado" if updated else "criado"
    return (
        f"Orçamento {verb}! 📊\n\n"
        f"Categoria: {name}\n"
        f"Limite: R$ {limit:,.2f}\n"
        f"Período: {period_label(period)}\n\n"
        f"Vou te avisar quando chegar em 80% e 100%."
    )


def budget_confirmation(
    name: str,
    limit: float,
    period: str = "monthly",
    created_at: Any = None,
) -> str:
    """Return the fixed confirmation prompt for a pending budget."""
    clean_name = (name or "Outros").strip() or "Outros"
    cadence = "a cada 30 dias" if period == "monthly" else f"no periodo {period_label(period)}"
    return (
        f"📊 Orçamento de {_fmt_money(limit)} na categoria {clean_name} "
        f"{cadence} no dia {_success_date(created_at)}.\n\n"
        "Confirma?"
    )


def budget_saved_success() -> str:
    return "✅ Orçamento criado com sucesso!"


def budget_list(budgets: list[dict[str, Any]]) -> str:
    if not budgets:
        return (
            "Você ainda não tem orçamentos ativos.\n\n"
            "Orçamentos são limites de despesa por categoria (ex: R$ 500/mês em Alimentação). "
            "Quando você registra uma despesa na categoria, eu descontato do orçamento e aviso "
            "quando chega em 80% e 100% do limite.\n\n"
            "Para criar: 'Orçamento de R$ 500 para alimentação'."
        )
    lines = ["Seus orçamentos:"]
    for b in budgets:
        status = (
            "Ultrapassado"
            if b["percentage"] >= 100
            else "Atenção"
            if b["percentage"] >= 80
            else "OK"
        )
        lines.append(
            f"\n- {b['name']} ({period_label(b.get('period'))})\n"
            f"  R$ {b['total_spent']:,.2f} / R$ {b['total_limit']:,.2f} ({b['percentage']}%)\n"
            f"  Status: {status}"
        )
    return "\n".join(lines)


def goal_list(goals: list[dict[str, Any]]) -> str:
    if not goals:
        return (
            "Você ainda não tem metas ativas.\n\n"
            "Metas são objetivos de poupança (ex: R$ 10.000 para viagem até dez/2026). "
            "Você adiciona valor gradualmente com 'guardei X na meta Y' e eu acompanho o progresso.\n\n"
            "Para criar: 'Meta de R$ 10.000 para viagem até dez/2026'."
        )
    lines = ["Suas metas:"]
    for g in goals:
        pct = g.get("percentage", 0)
        deadline = g.get("deadline")
        dl_str = f" | Prazo: {_fmt_deadline(deadline)}" if deadline else ""
        lines.append(
            f"\n- {g['title']}\n"
            f"  R$ {g['current_amount']:,.2f} / R$ {g['target_amount']:,.2f} ({pct}%){dl_str}"
        )
    return "\n".join(lines)


def goal_created(title: str, target: float, deadline: str | None = None) -> str:
    dl = f"\nPrazo: {_fmt_deadline(deadline)}" if deadline else ""
    return (
        f"Meta criada!\n\nObjetivo: {title}\nValor: R$ {target:,.2f}{dl}\n\nBora começar a guardar!"
    )


def goal_confirmation(title: str, target: float, deadline: Any = None) -> str:
    clean_title = (title or "Reserva").strip() or "Reserva"
    deadline_label = _fmt_deadline(deadline)
    deadline_part = f" até {deadline_label}" if deadline_label else ""
    return f"🎯 Meta de {_fmt_money(target)} para {clean_title}{deadline_part}.\n\nConfirma?"


def goal_saved_success() -> str:
    return "✅ Meta criada com sucesso!"


def goal_contribution_confirmation(goal_identifier: str, amount: float) -> str:
    clean_identifier = (goal_identifier or "sua meta").strip() or "sua meta"
    return f"🎯 Adicionar {_fmt_money(amount)} na meta {clean_identifier}.\n\nConfirma?"


def goal_contribution_success(
    title: str,
    current_amount: float,
    target_amount: float,
    percentage: Any = 0,
) -> str:
    clean_title = (title or "Meta").strip() or "Meta"
    return (
        "✅ Valor adicionado à meta!\n\n"
        f"{clean_title}: {_fmt_money(current_amount)} / {_fmt_money(target_amount)} ({percentage}%)."
    )


def goal_update_confirmation(
    goal_identifier: str,
    title: str | None = None,
    target_amount: float | None = None,
    deadline: Any = None,
) -> str:
    clean_identifier = (goal_identifier or "sua meta").strip() or "sua meta"
    changes = []
    if title:
        changes.append(f"nome para {title}")
    if target_amount is not None:
        changes.append(f"valor para {_fmt_money(target_amount)}")
    deadline_label = _fmt_deadline(deadline)
    if deadline_label:
        changes.append(f"prazo para {deadline_label}")
    change_text = f"\n\nAlterações: {', '.join(changes)}." if changes else ""
    return f"🎯 Atualizar meta {clean_identifier}.{change_text}\n\nConfirma?"


def goal_update_success(title: str, target_amount: float, deadline: Any = None) -> str:
    deadline_label = _fmt_deadline(deadline)
    deadline_part = f" Prazo: {deadline_label}." if deadline_label else ""
    return f"✅ Meta atualizada com sucesso! {title}: {_fmt_money(target_amount)}.{deadline_part}".strip()


def goal_delete_confirmation(goal_identifier: str) -> str:
    clean_identifier = (goal_identifier or "sua meta").strip() or "sua meta"
    return f"🗑️ Remover meta {clean_identifier}.\n\nConfirma?"


def goal_delete_success() -> str:
    return "✅ Meta removida com sucesso!"


def alerts_list(alerts: list[dict[str, Any]]) -> str:
    if not alerts:
        return "Nenhum alerta no momento. Seus orçamentos e metas estão dentro do previsto."
    lines = ["Alertas:"]
    for a in alerts:
        lines.append(f"\n- {a['message']}")
    return "\n".join(lines)


def transaction_list(rows: list[dict[str, Any]], title: str = "Transações") -> str:
    """Format transaction list cleanly."""
    if not rows:
        return "Nenhuma transação encontrada."
    lines = [f"{title}:"]
    for i, row in enumerate(rows, 1):
        amount = row.get("amount") or row.get("valor") or row.get("total") or 0
        desc = row.get("description") or row.get("descricao") or row.get("desc") or "-"
        cat = row.get("category") or row.get("categoria") or ""
        date_val = row.get("transaction_date") or row.get("data") or row.get("date") or ""
        tipo = row.get("type") or row.get("tipo") or "EXPENSE"

        date_str = _fmt_date(date_val)
        prefix = "+" if str(tipo).upper() == "INCOME" else "-"
        cat_part = f" ({cat})" if cat else ""
        date_part = f", {date_str}" if date_str else ""

        lines.append(f"{i}. {prefix}R$ {float(amount):,.2f} — {desc}{cat_part}{date_part}")
    return "\n".join(lines)


def category_list(rows: list[dict[str, Any]]) -> str:
    """Format expense-by-category list."""
    if not rows:
        return "Nenhuma despesa encontrada no período."
    lines = ["Despesas por categoria:"]
    for row in rows:
        cat = row.get("categoria") or row.get("category") or row.get("name") or "Outros"
        total = row.get("total") or row.get("amount") or row.get("sum") or 0
        lines.append(f"- {cat}: R$ {float(total):,.2f}")
    return "\n".join(lines)


def import_result(imported: int, skipped: int, errors: list[str]) -> str:
    if errors:
        return (
            f"Importação concluída.\n"
            f"Importados: {imported}\n"
            f"Ignorados: {skipped}\n"
            f"Erros: {len(errors)}\n\n"
            f"Detalhes: {', '.join(errors[:3])}"
        )
    return f"Importação concluída. {imported} transações importadas, {skipped} ignoradas."


def unknown_intent() -> str:
    return (
        "Não entendi muito bem. Posso ajudar com:\n"
        "- Registrar despesas e receitas\n"
        "- Consultar seus dados\n"
        "- Gerar relatórios\n"
        "- Dar dicas financeiras\n\n"
        "Manda 'ajuda' para ver exemplos."
    )


def error_message(error: str) -> str:
    error_lower = error.lower()
    if "invalid input value for enum" in error_lower or "psycopg" in error_lower:
        return "Ops, tive um problema ao buscar seus dados. Pode tentar reformular? Ex: 'Quanto gastei esse mês?'"
    if "não foi possível identificar o valor" in error_lower:
        return "Não consegui identificar o valor. Pode me dizer quanto foi? Ex: 'Gastei R$ 50 no mercado'"
    if "connection" in error_lower or "timeout" in error_lower:
        return (
            "Parece que estou com dificuldades de conexão. Pode tentar de novo em alguns segundos?"
        )
    return "Ops, tive um problema ao processar sua solicitação. Pode tentar de outra forma?"
