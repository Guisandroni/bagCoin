"""Text-to-SQL agent for BagCoin.

Converts natural language queries to safe SQL using the sync engine.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from calendar import monthrange
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from sqlalchemy import text

from app.agents.tenant_context import tenant_phone_error
from app.db.session import sync_engine
from app.services.llm_service import get_llm

logger = logging.getLogger(__name__)


MONTHS_PT = {
    "jan": 1,
    "janeiro": 1,
    "fev": 2,
    "fevereiro": 2,
    "mar": 3,
    "marco": 3,
    "março": 3,
    "abr": 4,
    "abril": 4,
    "mai": 5,
    "maio": 5,
    "jun": 6,
    "junho": 6,
    "jul": 7,
    "julho": 7,
    "ago": 8,
    "agosto": 8,
    "set": 9,
    "setembro": 9,
    "out": 10,
    "outubro": 10,
    "nov": 11,
    "novembro": 11,
    "dez": 12,
    "dezembro": 12,
}

MONTH_LABELS_PT = {
    1: "janeiro",
    2: "fevereiro",
    3: "março",
    4: "abril",
    5: "maio",
    6: "junho",
    7: "julho",
    8: "agosto",
    9: "setembro",
    10: "outubro",
    11: "novembro",
    12: "dezembro",
}


@dataclass(frozen=True)
class FinancialQueryPeriod:
    """Resolved period used by SQL queries and report generation."""

    start: date | None
    end: date | None
    label: str

    @property
    def sql_clause(self) -> str | None:
        if self.start and self.end:
            return f"DATE(transaction_date) BETWEEN '{self.start.isoformat()}' AND '{self.end.isoformat()}'"
        if self.start:
            return f"DATE(transaction_date) >= '{self.start.isoformat()}'"
        if self.end:
            return f"DATE(transaction_date) <= '{self.end.isoformat()}'"
        return None


def normalize_query_text(text: str) -> str:
    return unicodedata.normalize("NFKD", text.lower()).encode("ASCII", "ignore").decode("ASCII")

DB_SCHEMA = """
Tabelas:
- users(id, phone_number, full_name, status, preferences, financial_profile, created_at, updated_at)
- transactions(id, user_id, type, amount, currency, category_id, description, source_format, transaction_date, created_at, updated_at, confidence_score, raw_input)
- categories(id, user_id, name, parent_category_id, is_default, created_at, updated_at)

Relacionamentos:
- transactions.user_id -> users.id
- categories.user_id -> users.id
- transactions.category_id -> categories.id

Tipos de transação (USE SEMPRE MAIÚSCULO no SQL): EXPENSE, INCOME, TRANSFER, ADJUSTMENT
"""

ALLOWED_SQL_PATTERNS = [
    r"^\s*SELECT\s+",
    r"^\s*WITH\s+",
]

FORBIDDEN_KEYWORDS = [
    "DROP",
    "DELETE",
    "UPDATE",
    "INSERT",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "GRANT",
    "REVOKE",
    "EXEC",
    "EXECUTE",
    "UNION",
]


def validate_sql(query: str) -> bool:
    """Validate that the SQL query is safe (SELECT/WITH only)."""
    query_upper = query.upper().strip()

    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in query_upper:
            return False

    # Block SQL comments
    if "--" in query or "/*" in query:
        return False

    has_allowed = any(re.match(pattern, query, re.IGNORECASE) for pattern in ALLOWED_SQL_PATTERNS)
    return has_allowed


def validate_user_filter(sql: str, phone_number: str) -> bool:
    """Validate that the query filters by the correct user's phone_number."""
    sql_normalized = re.sub(r"\s+", " ", sql.upper().strip())
    pattern = (
        r"(?:[a-z_]+\.)?\s*USER_ID\s*"
        r"(?:=|IN)\s*"
        r"\(?\s*SELECT\s+(?:ID\s+FROM\s+USERS\s+"
        r"|DISTINCT\s+ID\s+FROM\s+USERS\s+)"
        r"WHERE\s+(?:PHONE_NUMBER|PHONE)\s*(?:=|LIKE|ILIKE|IN)"
    )
    return bool(re.search(pattern, sql_normalized, re.IGNORECASE))


def sanitize_sql_enums(sql: str) -> str:
    """Fix lowercase enums to UPPERCASE in SQL."""
    replacements = {
        r"'expense'": "'EXPENSE'",
        r"'income'": "'INCOME'",
        r"'transfer'": "'TRANSFER'",
        r"'adjustment'": "'ADJUSTMENT'",
    }
    for pattern, replacement in replacements.items():
        sql = re.sub(pattern, replacement, sql, flags=re.IGNORECASE)
    return sql


def execute_sql_query(query: str, params: dict | None = None) -> list[dict[str, Any]]:
    """Execute a SQL query safely using the sync engine."""
    if not validate_sql(query):
        raise ValueError("Query SQL não permitida. Apenas SELECT e WITH são autorizados.")

    query = sanitize_sql_enums(query)

    with sync_engine.connect() as connection:
        result = connection.execute(text(query), params or {})
        rows = [dict(row._mapping) for row in result]
        return rows


def _current_report_date() -> date:
    try:
        from app.services.report_time import report_now

        return report_now().date()
    except Exception:
        return datetime.now(UTC).date()


def _month_period(month: int, year: int) -> FinancialQueryPeriod:
    last_day = monthrange(year, month)[1]
    label = f"{MONTH_LABELS_PT[month]} de {year}"
    return FinancialQueryPeriod(
        start=date(year, month, 1),
        end=date(year, month, last_day),
        label=label,
    )


def resolve_financial_query_period(
    message: str,
    *,
    today: date | None = None,
) -> FinancialQueryPeriod:
    """Resolve a natural-language financial query period for SQL and reports."""
    today = today or _current_report_date()
    msg_norm = normalize_query_text(message)

    if any(
        marker in msg_norm
        for marker in (
            "todo tempo",
            "todos os tempos",
            "todas minhas financas",
            "todas as minhas financas",
            "historico completo",
            "desde o inicio",
            "desde que comecei",
        )
    ):
        return FinancialQueryPeriod(start=None, end=None, label="todo histórico")

    month_names = "|".join(sorted(MONTHS_PT, key=len, reverse=True))
    month_match = re.search(
        rf"\b({month_names})\b(?:\s*(?:de|/|-)?\s*(20\d{{2}}))?",
        msg_norm,
    )
    if month_match:
        month = MONTHS_PT[month_match.group(1)]
        year = int(month_match.group(2) or today.year)
        return _month_period(month, year)

    explicit_year_match = re.search(r"\b(20\d{2})\b", msg_norm)
    requested_year = int(explicit_year_match.group(1)) if explicit_year_match else today.year
    if any(
        marker in msg_norm
        for marker in (
            "todo ano",
            "ano todo",
            "ano inteiro",
            "ano completo",
            "este ano",
            "esse ano",
            "ano atual",
            "ano de",
        )
    ):
        end = today if requested_year == today.year else date(requested_year, 12, 31)
        return FinancialQueryPeriod(
            start=date(requested_year, 1, 1),
            end=end,
            label=f"ano de {requested_year}",
        )

    if "hoje" in msg_norm:
        return FinancialQueryPeriod(start=today, end=today, label="hoje")

    if "ontem" in msg_norm:
        yesterday = today - timedelta(days=1)
        return FinancialQueryPeriod(start=yesterday, end=yesterday, label="ontem")

    if any(marker in msg_norm for marker in ("esta semana", "essa semana", "ultimos 7 dias", "semana")):
        return FinancialQueryPeriod(
            start=today - timedelta(days=7),
            end=today,
            label="últimos 7 dias",
        )

    if any(marker in msg_norm for marker in ("ultimos 30 dias", "ultimos trinta dias")):
        return FinancialQueryPeriod(
            start=today - timedelta(days=30),
            end=today,
            label="últimos 30 dias",
        )

    if any(marker in msg_norm for marker in ("mes passado", "ultimo mes")):
        first_this_month = today.replace(day=1)
        end = first_this_month - timedelta(days=1)
        start = end.replace(day=1)
        return FinancialQueryPeriod(start=start, end=end, label="mês passado")

    if any(marker in msg_norm for marker in ("esse mes", "este mes", "mes atual", "mes corrente", "mes")):
        return FinancialQueryPeriod(
            start=today.replace(day=1),
            end=today,
            label="este mês",
        )

    if any(
        marker in msg_norm
        for marker in ("ja gastei", "ate agora", "total", "quanto gastei")
    ) and not any(marker in msg_norm for marker in ("hoje", "ontem", "semana", "mes", "ano")):
        return FinancialQueryPeriod(
            start=today.replace(day=1),
            end=today,
            label="este mês",
        )

    return FinancialQueryPeriod(
        start=today.replace(day=1),
        end=today,
        label="este mês",
    )


def get_date_filter(msg_lower: str) -> str | None:
    """Return WHERE date clause based on the user's message."""
    return resolve_financial_query_period(msg_lower).sql_clause


def _period_label(date_clause: str) -> str:
    """Generate user-friendly period label for summary."""
    if not date_clause:
        return ""
    if "CURRENT_DATE" in date_clause and "date_trunc" not in date_clause:
        if "- INTERVAL '1 day'" in date_clause:
            return " de ontem"
        if "- INTERVAL '7 days'" in date_clause or "- INTERVAL '30 days'" in date_clause:
            return " no período"
        return " de hoje"
    if "date_trunc('month'" in date_clause:
        return " deste mês"
    if "date_trunc('year'" in date_clause:
        return " deste ano"
    return ""


def build_financial_transactions_query(message: str) -> tuple[str, str, FinancialQueryPeriod]:
    """Build the canonical SQL used by reports to fetch financial transactions."""
    period = resolve_financial_query_period(message)
    date_sql = f" AND {period.sql_clause}" if period.sql_clause else ""
    sql = (
        "SELECT "
        "t.id, t.transaction_date, t.type, t.amount, t.description, "
        "t.category_id, COALESCE(c.name, 'Outros') AS category, t.source_format "
        "FROM transactions t "
        "LEFT JOIN categories c ON t.category_id = c.id "
        "WHERE t.user_id = (SELECT id FROM users WHERE phone_number = :phone_number)"
        f"{date_sql} "
        "ORDER BY t.transaction_date DESC NULLS LAST, t.id DESC"
    )
    return sql, f"Transações financeiras - {period.label}", period


def fetch_financial_transactions_for_query(message: str, phone_number: str) -> dict[str, Any]:
    """Execute the canonical text-to-SQL transaction query for reports."""
    sql, description, period = build_financial_transactions_query(message)
    if not validate_user_filter(sql, phone_number):
        raise ValueError("Missing user_id filter")
    rows = execute_sql_query(sql, {"phone_number": phone_number})
    return {
        "sql": sql,
        "description": description,
        "period": period,
        "rows": rows,
    }


def get_fallback_query(message: str, phone_number: str) -> tuple[str | None, str | None]:
    """Try to map common queries to SQL without LLM."""
    msg_lower = message.lower()
    msg_norm = normalize_query_text(msg_lower)
    user_filter = "user_id = (SELECT id FROM users WHERE phone_number = :phone_number)"
    period = resolve_financial_query_period(message)
    date_clause = period.sql_clause
    date_sql = f" AND {date_clause}" if date_clause else ""
    description_period = f" ({period.label})" if period.label else ""

    def _in(keywords):
        return any(kw in msg_lower for kw in keywords) or any(kw in msg_norm for kw in keywords)

    # Total expenses
    expense_phrases = [
        "quanto gastei",
        "quanto ja gastei",
        "quanto gastei ate agora",
        "total de gastos",
        "soma das despesas",
        "total pago",
        "gastos totais",
        "despesas totais",
        "quanto ja paguei",
    ]
    if _in(expense_phrases):
        sql = f"SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE {user_filter} AND type = 'EXPENSE'{date_sql}"
        return sql, f"Total de gastos{description_period}"

    # Total income
    income_phrases = [
        "quanto recebi",
        "total de receitas",
        "soma das receitas",
        "total de entradas",
        "receitas totais",
        "quanto caiu",
        "quanto ganhei",
        "quanto entrou",
    ]
    if _in(income_phrases):
        sql = f"SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE {user_filter} AND type = 'INCOME'{date_sql}"
        return sql, f"Total de receitas{description_period}"

    # Balance
    if _in(["saldo", "quanto sobrou", "diferenca", "balanco"]):
        if date_clause:
            sql = (
                f"SELECT (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE {user_filter} AND type = 'INCOME' AND {date_clause}) "
                f"- (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE {user_filter} AND type = 'EXPENSE' AND {date_clause}) as saldo"
            )
        else:
            sql = (
                f"SELECT (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE {user_filter} AND type = 'INCOME') "
                f"- (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE {user_filter} AND type = 'EXPENSE') as saldo"
            )
        return sql, "Saldo (receitas - despesas)"

    # Expenses by category
    category_phrases = [
        "gastos por categoria",
        "despesas por categoria",
        "categorias",
        "gastos em cada categoria",
        "quanto gastei em cada",
        "resumo por categoria",
        "resumo de categoria",
    ]
    if _in(category_phrases):
        sql = (
            f"SELECT c.name as categoria, COALESCE(SUM(t.amount), 0) as total "
            f"FROM transactions t LEFT JOIN categories c ON t.category_id = c.id "
            f"WHERE t.{user_filter} AND t.type = 'EXPENSE'{date_sql} "
            f"GROUP BY c.name ORDER BY total DESC"
        )
        return sql, "Gastos por categoria"

    # Last transactions
    if _in(["ultimas transacoes", "ultimos gastos", "historico recente", "lista de transacoes"]):
        sql = (
            f"SELECT t.transaction_date as data, t.type as tipo, t.amount as valor, "
            f"t.description as descricao, c.name as categoria "
            f"FROM transactions t LEFT JOIN categories c ON t.category_id = c.id "
            f"WHERE t.{user_filter}{date_sql} "
            f"ORDER BY t.transaction_date DESC LIMIT 10"
        )
        return sql, "Últimas 10 transações"

    # Biggest expense
    if _in(["maior gasto", "maior despesa", "gasto mais alto"]):
        sql = (
            f"SELECT t.amount as valor, t.description as descricao, c.name as categoria "
            f"FROM transactions t LEFT JOIN categories c ON t.category_id = c.id "
            f"WHERE t.{user_filter} AND t.type = 'EXPENSE'{date_sql} "
            f"ORDER BY t.amount DESC LIMIT 1"
        )
        return sql, "Maior gasto registrado"

    # Income list
    if _in(["lista de receitas", "minhas receitas", "receitas recentes", "entradas"]):
        sql = (
            f"SELECT t.transaction_date as data, t.amount as valor, t.description as descricao "
            f"FROM transactions t WHERE t.{user_filter} AND t.type = 'INCOME'{date_sql} "
            f"ORDER BY t.transaction_date DESC LIMIT 10"
        )
        return sql, "Receitas recentes"

    # Expense list
    if _in(["lista de gastos", "minhas despesas", "gastos recentes", "despesas"]):
        sql = (
            f"SELECT t.transaction_date as data, t.amount as valor, t.description as descricao "
            f"FROM transactions t WHERE t.{user_filter} AND t.type = 'EXPENSE'{date_sql} "
            f"ORDER BY t.transaction_date DESC LIMIT 10"
        )
        return sql, "Gastos recentes"

    return None, None


def process_query(state: dict[str, Any]) -> dict[str, Any]:
    """Process natural language query and convert to SQL."""
    message = state.get("message", "")
    phone_number = state.get("phone_number", "")
    terr = tenant_phone_error(phone_number)
    if terr:
        state["error"] = terr
        return state

    llm = get_llm(temperature=0.1)

    fallback_sql, fallback_desc = get_fallback_query(message, phone_number)

    if not llm and not fallback_sql:
        state["error"] = (
            "Não reconheci o padrão da consulta. Tente algo como:\n"
            "• 'Quanto gastei hoje?'\n"
            "• 'Gastos por categoria'\n"
            "• 'Qual meu saldo?'"
        )
        return state

    try:
        if fallback_sql:
            sql = fallback_sql
            description = fallback_desc
        else:
            history = ""
            try:
                from app.agents.persistence import get_conversation_history

                history = get_conversation_history(phone_number, limit=4)
            except Exception:
                pass
            from app.agents.prompts.other import build_sql_prompt

            history_context = f"\n\nÚltimas mensagens da conversa:\n{history}" if history else ""

            system_prompt = build_sql_prompt(db_schema=DB_SCHEMA, history=history_context)

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Telefone: {phone_number}\nPergunta: {message}"),
            ]

            response = llm.invoke(messages)
            result = JsonOutputParser().parse(response.content)

            sql = result.get("sql", "")
            description = result.get("description", "")

        # Sanitize enums
        sql = sanitize_sql_enums(sql)

        # Security validation (SELECT only)
        if not validate_sql(sql):
            state["error"] = "A consulta gerada não é segura. Tente reformular."
            state["query_result"] = {"sql": sql, "error": "Query blocked by safety filter"}
            return state

        # Runtime user isolation validation
        if not validate_user_filter(sql, phone_number):
            logger.warning(f"Query rejected for missing user_id filter: {sql[:200]}")
            state["error"] = (
                "Não consegui buscar seus dados com segurança. Tente reformular a pergunta."
            )
            state["query_result"] = {"sql": sql, "error": "Missing user_id filter"}
            return state

        # Execute query
        params = {"phone_number": phone_number}
        rows = execute_sql_query(sql, params)

        # Generate summary
        summary = generate_summary(message, rows, description)

        state["query_result"] = {
            "sql": sql,
            "results": rows,
            "summary": summary,
            "error": None,
        }

        logger.info(f"Query executed successfully: {sql[:100]}...")

    except Exception as e:
        logger.error(f"Error in text-to-SQL: {e}")
        state["error"] = (
            "Não consegui buscar seus dados. Tente reformular a pergunta de outra forma."
        )
        state["query_result"] = {"error": str(e)}

    return state


def generate_summary(question: str, rows: list[dict[str, Any]], description: str) -> str:
    """Generate natural language summary of query results."""
    from app.agents.responses import category_list, transaction_list

    if not rows:
        return "Não encontrei registros para o período."

    # Single row with single metric
    if len(rows) == 1 and len(rows[0]) == 1:
        key = list(rows[0].keys())[0]
        value = rows[0][key]
        if isinstance(value, (int, float)):
            return f"R$ {value:,.2f}"
        return f"Resultado: {value}"

    # Detect transaction list
    first_keys = {k.lower() for k in rows[0].keys()}
    is_transaction_list = bool(
        first_keys & {"data", "date", "transaction_date"}
        and first_keys & {"valor", "amount", "total"}
        and first_keys & {"descricao", "description", "desc"}
    )
    if is_transaction_list:
        title = "Transações"
        q = question.lower()
        if "receita" in q or "entrada" in q:
            title = "Receitas"
        elif "gasto" in q or "despesa" in q:
            title = "Gastos"
        return transaction_list(rows, title)

    # Detect category list
    is_category_list = bool(
        first_keys & {"categoria", "category", "name"} and first_keys & {"total", "amount", "sum"}
    )
    if is_category_list:
        return category_list(rows)

    # Fallback: generic formatting
    lines = []
    for row in rows[:5]:
        parts = []
        for k, v in row.items():
            k_lower = k.lower()
            if isinstance(v, float):
                parts.append(f"R$ {v:,.2f}")
            elif k_lower in {"data", "date", "transaction_date"}:
                from app.agents.responses import _fmt_date

                parts.append(str(_fmt_date(v)))
            elif k_lower in {"tipo", "type"}:
                parts.append("Receita" if str(v).upper() == "INCOME" else "Gasto")
            else:
                parts.append(str(v))
        lines.append("- " + " | ".join(parts))

    return "\n".join(lines)
