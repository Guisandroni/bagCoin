"""Tests for financial PDF generation."""

from datetime import UTC, datetime

from PyPDF2 import PdfReader

from app.services import pdf_generator
from app.services.report_time import report_now


def _pdf_text(path: str) -> str:
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def test_report_now_uses_sao_paulo_timezone():
    utc_now = datetime(2026, 5, 25, 0, 34, 38, tzinfo=UTC)

    local = report_now(utc_now)

    assert local.strftime("%Y-%m-%d %H:%M:%S") == "2026-05-24 21:34:38"


def test_pdf_filename_and_empty_budget_goal_sections_use_local_time(tmp_path, monkeypatch):
    monkeypatch.setattr(pdf_generator, "REPORTS_DIR", str(tmp_path))
    utc_now = datetime(2026, 5, 25, 0, 34, 38, tzinfo=UTC)

    path = pdf_generator.generate_financial_report(
        user_name="Gui Sandroni",
        period_start="01/05/2026",
        period_end="24/05/2026",
        transactions=[],
        categories_summary=[],
        total_income=0,
        total_expense=0,
        budgets_info=[],
        goals_info=[],
        generated_at=utc_now,
    )

    assert path.endswith("report_Gui_Sandroni_20260524_213438.pdf")
    text = _pdf_text(path)
    assert "Gerado em:" in text
    assert "24/05/2026 21:34" in text
    assert "Nenhum orçamento criado." in text
    assert "Nenhuma meta criada." in text


def test_pdf_renders_budget_and_goal_sections(tmp_path, monkeypatch):
    monkeypatch.setattr(pdf_generator, "REPORTS_DIR", str(tmp_path))

    path = pdf_generator.generate_financial_report(
        user_name="Gui Sandroni",
        period_start="01/05/2026",
        period_end="24/05/2026",
        transactions=[
            {
                "date": "24/05/2026",
                "type": "INCOME",
                "category": "Salário",
                "description": "Salário Maio",
                "amount": 8500,
            },
            {
                "date": "24/05/2026",
                "type": "EXPENSE",
                "category": "Alimentação",
                "description": "Mercado",
                "amount": 100,
            },
        ],
        categories_summary=[{"name": "Alimentação", "total": 100}],
        total_income=8500,
        total_expense=100,
        budgets_info=[
            {
                "name": "Alimentação",
                "limit": 4000,
                "spent": 100,
                "remaining": 3900,
                "percentage": 2.5,
            }
        ],
        goals_info=[
            {
                "title": "Notebook",
                "target": 5000,
                "current": 1200,
                "deadline": datetime(2026, 10, 31, tzinfo=UTC),
            },
            {"title": "Reserva", "target": 3000, "current": 300},
        ],
        generated_at=datetime(2026, 5, 24, 18, 0, tzinfo=UTC),
    )

    text = _pdf_text(path)
    assert "Alimentação" in text
    assert "Notebook" in text
    assert "Reserva" in text
    assert "Receita" in text
    assert "Despesa" in text
    assert "INCOME" not in text
    assert "EXPENSE" not in text
    assert "R$ 8.500,00" in text
    assert "R$ 8,500.00" not in text
    assert "Meta" in text
    assert "Atual" in text
    assert "Alvo" in text
    assert "Progresso" in text
    assert "Prazo" in text
    assert "31/10/2026" in text
    assert "Nenhum orçamento criado." not in text
    assert "Nenhuma meta criada." not in text
