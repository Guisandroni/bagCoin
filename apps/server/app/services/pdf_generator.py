"""PDF Generator service — generates financial report PDFs using ReportLab.

Creates professional PDF reports with summary, category breakdown, and transactions.
"""

import logging
import os
from datetime import datetime
from typing import Any

from app.services.report_time import report_now
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

logger = logging.getLogger(__name__)

REPORTS_DIR = os.path.join(os.getcwd(), "reports")


def _format_money_ptbr(value: Any) -> str:
    amount = float(value or 0)
    formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def _format_percent_ptbr(value: Any) -> str:
    amount = float(value or 0)
    return f"{amount:.1f}".replace(".", ",") + "%"


def _format_transaction_type_ptbr(value: Any) -> str:
    normalized = str(value or "").upper()
    if normalized == "INCOME":
        return "Receita"
    if normalized == "EXPENSE":
        return "Despesa"
    return "Transação"


def _format_date_ptbr(value: Any) -> str:
    if not value:
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return "-"
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                parsed = datetime.strptime(cleaned.replace("Z", "+0000"), fmt)
                return parsed.strftime("%d/%m/%Y")
            except ValueError:
                continue
        return cleaned
    return str(value)


def generate_financial_report(
    user_name: str,
    period_start: str,
    period_end: str,
    transactions: list[dict[str, Any]],
    categories_summary: list[dict[str, Any]],
    total_income: float,
    total_expense: float,
    budget_info: dict[str, Any] | None = None,
    budgets_info: list[dict[str, Any]] | None = None,
    goals_info: list[dict[str, Any]] | None = None,
    generated_at: datetime | None = None,
) -> str:
    """Gera relatório PDF financeiro.

    Returns:
        Caminho absoluto do arquivo PDF gerado.
    """
    generated_at_local = report_now(generated_at)
    if budgets_info is None:
        budgets_info = [budget_info] if budget_info else []
    goals_info = goals_info or []

    filename = f"report_{user_name.replace(' ', '_')}_{generated_at_local.strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=30,
        alignment=TA_CENTER,
    )
    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#16213e"),
        spaceAfter=12,
        spaceBefore=12,
    )

    story = []

    # Título
    story.append(Paragraph("💰 BagCoin - Relatório Financeiro", title_style))
    story.append(Spacer(1, 0.5 * cm))

    # Período
    story.append(Paragraph(f"<b>Período:</b> {period_start} a {period_end}", styles["Normal"]))
    story.append(
        Paragraph(
            f"<b>Gerado em:</b> {generated_at_local.strftime('%d/%m/%Y %H:%M')}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 1 * cm))

    # Resumo
    story.append(Paragraph("📊 Resumo Financeiro", heading_style))

    summary_data = [
        ["Métrica", "Valor"],
        ["Total de Receitas", _format_money_ptbr(total_income)],
        ["Total de Despesas", _format_money_ptbr(total_expense)],
        ["Saldo", _format_money_ptbr(total_income - total_expense)],
    ]

    if budgets_info:
        total_budget_limit = sum(float(b.get("limit", 0) or 0) for b in budgets_info)
        total_budget_spent = sum(float(b.get("spent", 0) or 0) for b in budgets_info)
        summary_data.append(["Orçamentos Definidos", _format_money_ptbr(total_budget_limit)])
        summary_data.append(["Consumo dos Orçamentos", _format_money_ptbr(total_budget_spent)])

    summary_table = Table(summary_data, colWidths=[8 * cm, 8 * cm])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16213e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f0f0f0")),
                ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (-1, -1), 10),
                ("TOPPADDING", (0, 1), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 1 * cm))

    # Despesas por categoria
    if categories_summary:
        story.append(Paragraph("📈 Despesas por Categoria", heading_style))
        cat_data = [["Categoria", "Total", "% do Total"]]
        for cat in categories_summary:
            pct = (cat["total"] / total_expense * 100) if total_expense > 0 else 0
            cat_data.append([cat["name"], _format_money_ptbr(cat["total"]), _format_percent_ptbr(pct)])

        cat_table = Table(cat_data, colWidths=[8 * cm, 4 * cm, 4 * cm])
        cat_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8f8f8")),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                    ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                    ("TOPPADDING", (0, 1), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                ]
            )
        )
        story.append(cat_table)
        story.append(Spacer(1, 1 * cm))

    # Transações detalhadas
    if transactions:
        story.append(PageBreak())
        story.append(Paragraph("📝 Transações Detalhadas", heading_style))

        tx_data = [["Data", "Tipo", "Categoria", "Descrição", "Valor"]]
        for tx in transactions:
            tx_data.append(
                [
                    tx.get("date", "N/A"),
                    _format_transaction_type_ptbr(tx.get("type")),
                    tx.get("category", "N/A"),
                    tx.get("description", "-")[:30],
                    _format_money_ptbr(tx.get("amount", 0)),
                ]
            )

        tx_table = Table(tx_data, colWidths=[3 * cm, 2.5 * cm, 3 * cm, 5.5 * cm, 3 * cm])
        tx_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("TOPPADDING", (0, 1), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(tx_table)

    # Orçamentos
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph("📌 Orçamentos", heading_style))
    if budgets_info:
        budget_data = [["Nome", "Limite", "Despesa", "Restante", "%"]]
        for budget in budgets_info:
            limit = float(budget.get("limit", 0) or 0)
            spent = float(budget.get("spent", 0) or 0)
            remaining = budget.get("remaining")
            if remaining is None:
                remaining = limit - spent
            percentage = budget.get("percentage")
            if percentage is None:
                percentage = round((spent / limit) * 100, 1) if limit > 0 else 0
            budget_data.append(
                [
                    str(budget.get("name") or "Orçamento"),
                    _format_money_ptbr(limit),
                    _format_money_ptbr(spent),
                    _format_money_ptbr(remaining),
                    _format_percent_ptbr(percentage),
                ]
            )
        budget_table = Table(budget_data, colWidths=[5 * cm, 3 * cm, 3 * cm, 3 * cm, 2 * cm])
        budget_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(budget_table)
    else:
        story.append(Paragraph("Nenhum orçamento criado.", styles["Normal"]))

    # Metas
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph("🎯 Metas Financeiras", heading_style))
    if goals_info:
        goal_data = [["Meta", "Atual", "Alvo", "Progresso", "Prazo"]]
        for goal in goals_info:
            progress = (
                (goal.get("current", 0) / goal.get("target", 1) * 100)
                if goal.get("target", 0) > 0
                else 0
            )
            goal_data.append(
                [
                    str(goal.get("title") or "Meta"),
                    _format_money_ptbr(goal.get("current", 0)),
                    _format_money_ptbr(goal.get("target", 0)),
                    _format_percent_ptbr(progress),
                    _format_date_ptbr(goal.get("deadline")),
                ]
            )
        goal_table = Table(goal_data, colWidths=[5 * cm, 3 * cm, 3 * cm, 2.5 * cm, 2.5 * cm])
        goal_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(goal_table)
    else:
        story.append(Paragraph("Nenhuma meta criada.", styles["Normal"]))

    # Rodapé
    story.append(Spacer(1, 2 * cm))
    story.append(
        Paragraph(
            "<i>Este relatório foi gerado automaticamente pelo BagCoin. "
            "As informações são baseadas nos dados registrados no sistema.</i>",
            ParagraphStyle(
                "Footer",
                parent=styles["Normal"],
                fontSize=8,
                textColor=colors.grey,
                alignment=TA_CENTER,
            ),
        )
    )

    doc.build(story)
    logger.info(f"Relatório PDF gerado: {filepath}")

    return filepath
