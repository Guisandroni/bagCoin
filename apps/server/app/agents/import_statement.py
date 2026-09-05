"""Import statement agent — imports bank statement transactions into the database.

Uses sync_session_maker for database operations.
"""

import logging
from datetime import datetime
from typing import Any

from app.agents import responses as resp
from app.agents.persistence import get_or_create_user
from app.agents.statement_parser import parse_statement
from app.core.financial_categories import resolve_default_category_name
from app.db.models.category import Category
from app.db.models.phone_conversation import PhoneConversation
from app.db.models.transaction import Transaction
from app.db.session import sync_session_maker
from app.services.agent_memory_service import add_memory_event

logger = logging.getLogger(__name__)


def _map_category_to_db(category_name: str) -> str:
    """Mapeia nome de categoria heurística para as categorias padronizadas no banco.

    O statement_parser usa nomes como 'Renda', 'Entretenimento', 'Transferência'
    mas o banco usa categorias padronizadas como 'Receita', 'Lazer', 'Outros'.
    """
    mapping = {
        # Alimentação
        "Alimentação": "Alimentação",
        # Transporte
        "Transporte": "Transporte",
        # Moradia
        "Moradia": "Moradia",
        # Saúde
        "Saúde": "Saúde",
        "Saude": "Saúde",
        # Educação
        "Educação": "Educação",
        "Educacao": "Educação",
        # Entretenimento → Lazer (padronizado)
        "Entretenimento": "Lazer",
        "Lazer": "Lazer",
        # Vestuário
        "Vestuário": "Vestuário",
        "Vestuario": "Vestuário",
        # Renda → Receita (padronizado)
        "Renda": "Receita",
        "Receita": "Receita",
        # Investimentos → Outros (não é receita nem despesa direta)
        "Investimentos": "Outros",
        # Transferência → Outros
        "Transferência": "Outros",
        "Transferencia": "Outros",
        # Seguros
        "Seguros": "Outros",
        # Impostos
        "Impostos": "Impostos",
        # Viagem
        "Viagem": "Viagem",
        # Saque → Outros
        "Saque": "Outros",
        # Doações → Doação
        "Doações": "Doação",
        "Doacao": "Doação",
        "Doação": "Doação",
    }
    return resolve_default_category_name(mapping.get(category_name, category_name or "Outros"))


def import_parsed_transactions(
    phone_number: str,
    transactions: list[dict[str, Any]],
    *,
    source_format: str = "statement_import",
) -> dict[str, Any]:
    """Persist normalized imported transactions for a linked chat user."""
    db = sync_session_maker()
    try:
        user = get_or_create_user(phone_number, db)
        user_id = user.id
        conversation = (
            db.query(PhoneConversation)
            .filter(PhoneConversation.user_id == user_id)
            .order_by(PhoneConversation.updated_at.desc())
            .first()
        )

        imported = 0
        skipped = 0
        errors = []
        imported_transactions: list[dict[str, Any]] = []

        for tx in transactions:
            try:
                tx_date = datetime.strptime(tx["date"], "%Y-%m-%d")

                existing = (
                    db.query(Transaction)
                    .filter(
                        Transaction.user_id == user_id,
                        Transaction.transaction_date == tx_date,
                        Transaction.amount == tx["amount"],
                        Transaction.description == tx["description"],
                    )
                    .first()
                )
                if existing:
                    skipped += 1
                    continue

                cat_name = _map_category_to_db(tx.get("category", "Outros"))
                category = (
                    db.query(Category)
                    .filter(Category.user_id == user_id, Category.name == cat_name)
                    .first()
                )
                if not category:
                    category = Category(
                        user_id=user_id,
                        name=cat_name,
                        is_default=(
                            cat_name
                            in [
                                "Alimentação",
                                "Transporte",
                                "Moradia",
                                "Lazer",
                                "Saúde",
                                "Educação",
                                "Outros",
                            ]
                        ),
                    )
                    db.add(category)
                    db.commit()
                    db.refresh(category)

                db_tx = Transaction(
                    user_id=user_id,
                    type=tx["type"].upper(),
                    amount=tx["amount"],
                    currency="BRL",
                    category_id=category.id,
                    description=tx["description"],
                    transaction_date=tx_date,
                    source_format=source_format,
                    raw_input=tx.get("raw", ""),
                )
                db.add(db_tx)
                db.flush()
                imported += 1
                imported_transactions.append({
                    "type": tx["type"].upper(),
                    "amount": float(tx["amount"]),
                    "category": cat_name,
                    "description": tx["description"],
                    "transaction_date": tx_date,
                })
                add_memory_event(
                    db,
                    user_id=user_id,
                    conversation_id=conversation.id if conversation else None,
                    event_type="transaction_created",
                    entity_type="transaction",
                    entity_id=db_tx.id,
                    source=source_format,
                    summary=(
                        f"{tx['type'].upper()} R$ {float(tx['amount']):.2f} "
                        f"em {cat_name}: {tx['description']}"
                    ),
                    payload={
                        "transaction_id": db_tx.id,
                        "type": tx["type"].upper(),
                        "amount": float(tx["amount"]),
                        "category": cat_name,
                        "description": tx["description"],
                        "source_format": source_format,
                        "transaction_date": tx_date.isoformat(),
                    },
                )
            except Exception as e:
                logger.warning(f"Erro ao importar transação {tx}: {e}")
                errors.append(str(e))
                continue

        if imported or skipped:
            add_memory_event(
                db,
                user_id=user_id,
                conversation_id=conversation.id if conversation else None,
                event_type="document_import_processed",
                entity_type="document",
                source=source_format,
                summary=f"{imported} transação(ões) importada(s), {skipped} duplicata(s) ignorada(s).",
                payload={
                    "source_format": source_format,
                    "imported_count": imported,
                    "skipped_count": skipped,
                    "error_count": len(errors),
                },
            )

        db.commit()

        return {
            "imported_count": imported,
            "skipped_count": skipped,
            "import_errors": errors,
            "imported_transactions": imported_transactions,
            "import_summary": resp.document_imported(
                imported_transactions,
                skipped,
                errors,
                label="Extrato",
            ),
        }
    finally:
        db.close()


def import_transactions(state: dict[str, Any]) -> dict[str, Any]:
    """Importa transações de extrato bancário para o banco de dados.

    Espera que o estado contenha:
    - phone_number (para buscar/criar usuário)
    - context.media (com o extrato)

    Retorna:
    - state atualizado com response, import_summary, imported_count, error
    """
    phone_number = state.get("phone_number")
    media = state.get("context", {}).get("media")
    error = state.get("error")

    if error:
        return state

    if not media:
        state["error"] = "Nenhuma mídia encontrada para importação"
        return state

    # Parse do extrato
    transactions = parse_statement(media)
    if not transactions:
        state["error"] = (
            "Não consegui extrair transações do documento. Verifique se é um extrato bancário válido (CSV, OFX ou PDF)."
        )
        return state

    logger.info(f"Importando {len(transactions)} transações de extrato para {phone_number}")

    try:
        import_result = import_parsed_transactions(
            phone_number,
            transactions,
            source_format="statement_import",
        )
        state["imported_count"] = import_result["imported_count"]
        state["skipped_count"] = import_result["skipped_count"]
        state["import_errors"] = import_result["import_errors"]
        state["intent"] = "import_statement"
        state["import_summary"] = import_result["import_summary"]

        logger.info(
            "Importação concluída: %s importadas, %s ignoradas",
            import_result["imported_count"],
            import_result["skipped_count"],
        )

    except Exception as e:
        logger.error(f"Erro na importação de extrato: {e}", exc_info=True)
        state["error"] = f"Erro ao importar extrato: {e!s}"

    return state
