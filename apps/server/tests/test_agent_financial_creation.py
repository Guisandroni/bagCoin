"""Direct agent tests for category, transaction, and budget creation."""

from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.models  # noqa: F401
from app.db.base import Base
from app.db.models.agent_log import AgentLog
from app.db.models.agent_memory_event import AgentMemoryEvent
from app.db.models.budget import Budget, BudgetItem
from app.db.models.category import Category
from app.db.models.conversation_message import ConversationMessage
from app.db.models.goal import Goal
from app.db.models.phone_conversation import PhoneConversation
from app.db.models.recurring_transaction import RecurringTransaction
from app.db.models.transaction import Transaction
from app.db.models.user import User


def _session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            Category.__table__,
            RecurringTransaction.__table__,
            Transaction.__table__,
            Budget.__table__,
            BudgetItem.__table__,
            Goal.__table__,
            PhoneConversation.__table__,
            ConversationMessage.__table__,
            AgentMemoryEvent.__table__,
            AgentLog.__table__,
        ],
    )
    return sessionmaker(bind=engine)


def _patch_agent_db(monkeypatch):
    factory = _session_factory()
    import app.agents.import_statement as import_statement
    import app.agents.pending_actions as pending_actions
    import app.agents.persistence as persistence
    import app.services.budget_service as budget_service

    monkeypatch.setattr(persistence, "sync_session_maker", factory)
    monkeypatch.setattr(pending_actions, "sync_session_maker", factory)
    monkeypatch.setattr(import_statement, "sync_session_maker", factory)
    monkeypatch.setattr(budget_service, "sync_session_maker", factory)
    monkeypatch.setattr("app.services.deduplication_service.is_duplicate", lambda *_, **__: False)
    monkeypatch.setattr("app.services.pattern_learning_service.learn_from_transaction", lambda *_, **__: None)
    return factory


def test_agent_creates_custom_category(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.persistence import create_category

    created = create_category("5511999999999", "Colecionáveis")

    assert created is not None
    assert created["name"] == "Colecionáveis"
    with factory() as db:
        category = db.query(Category).filter(Category.name == "Colecionáveis").one()
        assert category.is_default is False


def test_agent_transaction_resolves_default_alias_without_duplicate(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.persistence import save_transaction

    state = {
        "phone_number": "5511999999999",
        "source_format": "text",
        "extracted_data": {
            "type": "EXPENSE",
            "amount": 42.0,
            "category": "mercado",
            "description": "Compra no mercado",
            "confidence": 0.9,
        },
    }

    result = save_transaction(state)

    assert result["category_name"] == "Supermercado"
    with factory() as db:
        assert db.query(Category).filter(Category.name == "Mercado").count() == 0
        assert db.query(Category).filter(Category.name == "Supermercado").count() == 1
        tx = db.query(Transaction).one()
        assert tx.category.name == "Supermercado"


def test_agent_transaction_uses_existing_custom_category(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.persistence import create_category, save_transaction

    create_category("5511999999999", "Colecionáveis")
    state = {
        "phone_number": "5511999999999",
        "source_format": "text",
        "extracted_data": {
            "type": "EXPENSE",
            "amount": 99.0,
            "category": "Colecionáveis",
            "description": "Item raro",
            "confidence": 0.9,
        },
    }

    save_transaction(state)

    with factory() as db:
        assert db.query(Category).filter(Category.name == "Colecionáveis").count() == 1
        tx = db.query(Transaction).one()
        assert tx.category.name == "Colecionáveis"


def test_agent_budget_uses_existing_default_category(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.services.budget_service import create_budget

    budget = create_budget(
        phone_number="5511999999999",
        name="mercado",
        total_limit=500,
        period="monthly",
        budget_type="category",
    )

    assert budget["category_name"] == "Supermercado"
    with factory() as db:
        saved = db.query(Budget).one()
        assert saved.category.name == "Supermercado"
        assert db.query(Category).filter(Category.name == "Mercado").count() == 0


def test_pending_update_budget_matches_default_category_without_accent(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.pending_actions import handle_pending_confirmation, save_pending_action
    from app.services.budget_service import create_budget

    create_budget(
        phone_number="5511999999999",
        name="Combustível",
        total_limit=120,
        period="monthly",
        budget_type="category",
    )

    response = save_pending_action(
        "5511999999999",
        action="update_budget",
        params={"name": "combustivel", "total_limit": 200},
        summary="Vou atualizar o orçamento combustivel para R$ 200.00.",
    )

    assert response.endswith("\n\nConfirma?")
    final_response = handle_pending_confirmation("5511999999999", "sim")

    assert "Orçamento atualizado" in final_response
    with factory() as db:
        budget = db.query(Budget).one()
        assert budget.name == "Combustível"
        assert budget.total_limit == 200


def test_agent_budget_links_unified_user_id(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.services.budget_service import create_budget

    web_user_id = 10
    with factory() as db:
        web_user = User(
            id=web_user_id,
            email="linked-budget@bagcoin.com",
            hashed_password="x",
            full_name="Linked",
        phone_number="5511999999999",
        )
        db.add(web_user)
        db.commit()

    create_budget(
        phone_number="5511999999999",
        name="Supermercado",
        total_limit=500,
        period="monthly",
        budget_type="category",
    )

    with factory() as db:
        saved = db.query(Budget).one()
        assert saved.user_id == web_user_id
        assert saved.category_id is not None


def test_tool_budget_requires_confirmation_before_save(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.pending_actions import handle_pending_confirmation, load_pending_action
    from app.agents.tools.budgets import create_budget_tools

    tools = {tool.name: tool for tool in create_budget_tools("5511999999999")}
    response = tools["prepare_create_budget"].invoke(
        {
            "name": "alimentação",
            "total_limit": 4000,
            "period": "weekly",
        }
    )

    assert response.startswith(
        "📊 Orçamento de R$ 4.000,00 na categoria Alimentação a cada 30 dias no dia "
    )
    assert response.endswith("\n\nConfirma?")
    assert load_pending_action("5511999999999") is not None
    with factory() as db:
        assert db.query(Budget).count() == 0

    final_response = handle_pending_confirmation("5511999999999", "sim")

    assert final_response == "✅ Orçamento criado com sucesso!"
    assert load_pending_action("5511999999999") is None
    with factory() as db:
        budget = db.query(Budget).one()
        assert budget.total_limit == 4000
        assert budget.period == "monthly"
        assert budget.category.name == "Alimentação"


def test_tool_transaction_requires_confirmation_before_save(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.pending_actions import handle_pending_confirmation, load_pending_action
    from app.agents.tools.financial import create_financial_tools

    tools = {tool.name: tool for tool in create_financial_tools("5511999999999")}
    response = tools["prepare_register_transaction"].invoke(
        {
            "amount": 80,
            "description": "Mercado",
            "transaction_type": "EXPENSE",
            "category": "Supermercado",
        }
    )

    assert response.startswith("🧾 Despesa: R$ 80,00 em Supermercado (Mercado) no dia ")
    assert response.endswith(
        "\n\nConfirma esta transação?\n"
        'Se algo estiver errado, me diga o ajuste. Ex: "valor era 200".'
    )
    assert load_pending_action("5511999999999") is not None
    with factory() as db:
        assert db.query(Transaction).count() == 0

    final_response = handle_pending_confirmation("5511999999999", "sim")

    assert final_response == "✅ Transação registrada com sucesso!"
    assert load_pending_action("5511999999999") is None
    with factory() as db:
        tx = db.query(Transaction).one()
        assert tx.amount == 80
        assert tx.description == "Mercado"
        assert tx.transaction_date.date().isoformat() == datetime.now(UTC).date().isoformat()


def test_tool_transaction_cancel_does_not_save(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.pending_actions import handle_pending_confirmation, load_pending_action
    from app.agents.tools.financial import create_financial_tools

    tools = {tool.name: tool for tool in create_financial_tools("5511999999999")}
    tools["prepare_register_transaction"].invoke(
        {
            "amount": 45,
            "description": "Uber",
            "transaction_type": "EXPENSE",
            "category": "Transporte",
        }
    )

    response = handle_pending_confirmation("5511999999999", "cancela")

    assert "nao executei" in response
    assert load_pending_action("5511999999999") is None
    with factory() as db:
        assert db.query(Transaction).count() == 0


def test_tool_income_confirmation_saves_income(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.pending_actions import handle_pending_confirmation
    from app.agents.tools.financial import create_financial_tools

    tools = {tool.name: tool for tool in create_financial_tools("5511999999999")}
    tools["prepare_register_transaction"].invoke(
        {
            "amount": 2500,
            "description": "Salário",
            "transaction_type": "INCOME",
            "category": "Salário",
        }
    )

    handle_pending_confirmation("5511999999999", "sim")
    with factory() as db:
        tx = db.query(Transaction).one()
        assert tx.type == "INCOME"
        assert tx.amount == 2500
        assert tx.category.name == "Salário"


def test_tool_transaction_correction_updates_pending_confirmation(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.pending_actions import handle_pending_confirmation
    from app.agents.tools.financial import create_financial_tools

    tools = {tool.name: tool for tool in create_financial_tools("5511999999999")}
    tools["prepare_register_transaction"].invoke(
        {
            "amount": 120,
            "description": "Supermercado",
            "transaction_type": "EXPENSE",
            "category": "Alimentação",
        }
    )

    correction = handle_pending_confirmation("5511999999999", "valor era 200")

    assert correction.startswith(
        "🧾 Despesa: R$ 200,00 em Alimentação (Supermercado) no dia "
    )
    assert correction.endswith(
        "\n\nConfirma esta transação?\n"
        'Se algo estiver errado, me diga o ajuste. Ex: "valor era 200".'
    )

    final_response = handle_pending_confirmation("5511999999999", "sim")
    assert final_response == "✅ Transação registrada com sucesso!"
    with factory() as db:
        tx = db.query(Transaction).one()
        assert tx.amount == 200


def test_tool_transaction_corrections_update_date_category_and_type(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.pending_actions import handle_pending_confirmation
    from app.agents.tools.financial import create_financial_tools

    tools = {tool.name: tool for tool in create_financial_tools("5511999999999")}
    tools["prepare_register_transaction"].invoke(
        {
            "amount": 90,
            "description": "Mercado",
            "transaction_type": "EXPENSE",
            "category": "Outros",
        }
    )

    date_response = handle_pending_confirmation("5511999999999", "data era 23/05/2026")
    assert "23/05/2026" in date_response

    category_response = handle_pending_confirmation("5511999999999", "categoria alimentação")
    assert "Alimentação" in category_response

    type_response = handle_pending_confirmation("5511999999999", "era receita")
    assert type_response.startswith("💰 Receita:")

    final_response = handle_pending_confirmation("5511999999999", "sim")
    assert final_response == "✅ Transação registrada com sucesso!"
    with factory() as db:
        tx = db.query(Transaction).one()
        assert tx.type == "INCOME"
        assert tx.category.name == "Alimentação"
        assert tx.transaction_date.date().isoformat() == "2026-05-23"


def test_tool_recurring_income_creates_rule_when_linked(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.pending_actions import handle_pending_confirmation
    from app.agents.tools.financial import create_financial_tools

    web_user_id = 10
    with factory() as db:
        db.add(
            User(
                id=web_user_id,
                email="recurring@bagcoin.com",
                hashed_password="x",
                full_name="Recurring",
                phone_number="5511999999999",
            )
        )
        db.commit()

    tools = {tool.name: tool for tool in create_financial_tools("5511999999999")}
    tools["prepare_register_transaction"].invoke(
        {
            "amount": 2500,
            "description": "Salário",
            "transaction_type": "INCOME",
            "category": "Salário",
            "is_recurring": True,
            "recurrence_frequency": "monthly",
            "recurrence_day": 5,
        }
    )

    response = handle_pending_confirmation("5511999999999", "sim")

    assert "Recorrencia automatica criada" in response
    with factory() as db:
        tx = db.query(Transaction).one()
        recurring = db.query(RecurringTransaction).one()
        assert tx.type == "INCOME"
        assert tx.recurring_transaction_id == recurring.id
        assert recurring.user_id == web_user_id
        assert recurring.frequency == "monthly"


def test_tool_budget_spent_updates_after_expense_confirmation(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.pending_actions import handle_pending_confirmation
    from app.agents.tools.financial import create_financial_tools
    from app.services.budget_service import create_budget, get_budgets

    create_budget("5511999999999", "Água", 50, "monthly", "category")
    tools = {tool.name: tool for tool in create_financial_tools("5511999999999")}
    tools["prepare_register_transaction"].invoke(
        {
            "amount": 41.49,
            "description": "Conta de água",
            "transaction_type": "EXPENSE",
            "category": "agua",
        }
    )

    handle_pending_confirmation("5511999999999", "sim")

    budgets = get_budgets("5511999999999")
    assert budgets[0]["category_name"] == "Água"
    assert round(budgets[0]["total_spent"], 2) == 41.49
    with factory() as db:
        assert db.query(Transaction).one().category.name == "Água"


def test_register_tool_agent_failure_does_not_fake_save(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.orchestrator import register_agent_node
    from app.core.config import settings

    class BrokenToolLLM:
        def bind_tools(self, _tools):
            raise RuntimeError("tools unsupported")

    monkeypatch.setattr(settings, "USE_TOOL_AGENTS", True)
    monkeypatch.setattr("app.services.llm_service.get_llm", lambda *_, **__: BrokenToolLLM())

    state = {
        "phone_number": "5511999999999",
        "message": "gastei 80 no mercado",
        "intent": "register_expense",
        "response": None,
        "context": {"channel": "whatsapp"},
        "source_format": "text",
    }

    result = register_agent_node(state)

    assert "Nao consegui preparar" in result["response"]
    with factory() as db:
        assert db.query(Transaction).count() == 0


def test_agent_goal_links_unified_user_id(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.services.budget_service import create_goal

    web_user_id = 10
    with factory() as db:
        web_user = User(
            id=web_user_id,
            email="linked-goal@bagcoin.com",
            hashed_password="x",
            full_name="Linked",
        phone_number="5511999999999",
        )
        db.add(web_user)
        db.commit()

    create_goal("5511999999999", "Viagem", 3000)

    with factory() as db:
        saved = db.query(Goal).one()
        assert saved.user_id == web_user_id


def test_tool_goal_requires_confirmation_before_save(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.pending_actions import handle_pending_confirmation, load_pending_action
    from app.agents.tools.goals import create_goal_tools

    tools = {tool.name: tool for tool in create_goal_tools("5511999999999")}
    response = tools["prepare_create_goal"].invoke(
        {
            "title": "Comprar notebook",
            "target_amount": 5000,
            "deadline": "10/2026",
        }
    )

    assert response == (
        "🎯 Meta de R$ 5.000,00 para Comprar notebook até outubro/2026.\n\nConfirma?"
    )
    assert load_pending_action("5511999999999") is not None
    with factory() as db:
        assert db.query(Goal).count() == 0

    final_response = handle_pending_confirmation("5511999999999", "sim")

    assert final_response == "✅ Meta criada com sucesso!"
    assert load_pending_action("5511999999999") is None
    with factory() as db:
        goal = db.query(Goal).one()
        assert goal.title == "Comprar notebook"
        assert goal.target_amount == 5000
        assert goal.deadline.month == 10
        assert goal.deadline.year == 2026


def test_tool_goal_contribution_requires_confirmation(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.pending_actions import handle_pending_confirmation, load_pending_action
    from app.agents.tools.goals import create_goal_tools
    from app.services.budget_service import create_goal

    create_goal("5511999999999", "Viagem", 5000)
    tools = {tool.name: tool for tool in create_goal_tools("5511999999999")}
    response = tools["prepare_contribute_goal"].invoke(
        {"goal_identifier": "Viagem", "amount": 1200}
    )

    assert response == "🎯 Adicionar R$ 1.200,00 na meta Viagem.\n\nConfirma?"
    with factory() as db:
        assert db.query(Goal).one().current_amount == 0

    final_response = handle_pending_confirmation("5511999999999", "sim")

    assert final_response == (
        "✅ Valor adicionado à meta!\n\nViagem: R$ 1.200,00 / R$ 5.000,00 (24.0%)."
    )
    assert load_pending_action("5511999999999") is None
    with factory() as db:
        assert db.query(Goal).one().current_amount == 1200


def test_tool_goal_update_and_delete_use_fixed_messages(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.pending_actions import handle_pending_confirmation
    from app.agents.tools.goals import create_goal_tools
    from app.services.budget_service import create_goal

    create_goal("5511999999999", "Viagem", 5000)
    tools = {tool.name: tool for tool in create_goal_tools("5511999999999")}

    update_response = tools["prepare_update_goal"].invoke(
        {
            "goal_identifier": "Viagem",
            "title": "Viagem Europa",
            "target_amount": 6000,
            "deadline": "12/2026",
        }
    )
    assert update_response == (
        "🎯 Atualizar meta Viagem.\n\n"
        "Alterações: nome para Viagem Europa, valor para R$ 6.000,00, prazo para dezembro/2026.\n\n"
        "Confirma?"
    )
    assert handle_pending_confirmation("5511999999999", "sim") == (
        "✅ Meta atualizada com sucesso! Viagem Europa: R$ 6.000,00. Prazo: dezembro/2026."
    )
    with factory() as db:
        goal = db.query(Goal).one()
        assert goal.title == "Viagem Europa"
        assert goal.target_amount == 6000

    delete_response = tools["prepare_delete_goal"].invoke({"goal_identifier": "Viagem Europa"})
    assert delete_response == "🗑️ Remover meta Viagem Europa.\n\nConfirma?"
    assert handle_pending_confirmation("5511999999999", "sim") == "✅ Meta removida com sucesso!"
    with factory() as db:
        assert db.query(Goal).count() == 0


def test_agent_manage_blocks_account_creation(monkeypatch):
    from app.agents.orchestrator import smart_manage_node

    monkeypatch.setattr("app.agents.nodes.smart.get_llm", lambda *_, **__: None)

    state = {
        "phone_number": "5511999999999",
        "message": "Criar conta Nubank com saldo 1000",
        "response": None,
    }

    result = smart_manage_node(state)

    assert "não crio contas" in result["response"]
    assert "orçamento por categoria" in result["response"]


def test_agent_manage_prepares_budget_without_llm(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.orchestrator import smart_manage_tool_node
    from app.agents.pending_actions import load_pending_action

    monkeypatch.setattr("app.agents.nodes.smart.get_llm", lambda *_, **__: None)
    monkeypatch.setattr("app.agents.wizard._load_wizard_state", lambda *_: None)

    state = {
        "phone_number": "5511999999999",
        "message": "orçamento 4000 alimentação",
        "response": None,
        "context": {"channel": "whatsapp"},
    }

    result = smart_manage_tool_node(state)

    assert result["response"].startswith(
        "📊 Orçamento de R$ 4.000,00 na categoria Alimentação a cada 30 dias no dia "
    )
    pending = load_pending_action("5511999999999")
    assert pending is not None
    assert pending["action"] == "create_budget"
    with factory() as db:
        assert db.query(Budget).count() == 0


def test_agent_manage_blocks_credit_card_creation(monkeypatch):
    from app.agents.orchestrator import smart_manage_node

    monkeypatch.setattr("app.agents.nodes.smart.get_llm", lambda *_, **__: None)

    state = {
        "phone_number": "5511999999999",
        "message": "Criar cartão de crédito Inter",
        "response": None,
    }

    result = smart_manage_node(state)

    assert "não crio contas" in result["response"]
    assert "orçamento por categoria" in result["response"]


def test_route_by_intent_sends_account_request_to_blocker():
    from app.agents.orchestrator import route_by_intent

    state = {
        "message": "Criar conta Nubank com saldo 1000",
        "intent": "register_expense",
        "macro_intent": "register",
        "error": None,
        "response": None,
    }

    assert route_by_intent(state) == "smart_manage"


def test_route_after_multimodal_sends_documents_to_document_tool(monkeypatch):
    from app.agents.orchestrator import route_after_multimodal
    from app.core.config import settings

    monkeypatch.setattr(settings, "USE_TOOL_AGENTS", True)
    monkeypatch.setattr("app.agents.routing.has_pending_confirmation_message", lambda *_: False)

    state = {
        "phone_number": "5511999999999",
        "message": "texto extraído",
        "source_format": "document",
        "error": None,
        "response": None,
        "context": {"original_format": "document"},
    }

    assert route_after_multimodal(state) == "document_agent"


def test_agent_category_aliases_do_not_explode_categories(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.persistence import save_transaction

    inputs = [
        ("EXPENSE", "mercado", "Mercado"),
        ("EXPENSE", "supermercado", "Supermercado"),
        ("EXPENSE", "ifood", "iFood"),
        ("INCOME", "freela", "Freela"),
    ]
    for tx_type, category, description in inputs:
        save_transaction({
            "phone_number": "5511999999999",
            "source_format": "text",
            "extracted_data": {
                "type": tx_type,
                "amount": 10.0,
                "category": category,
                "description": description,
                "confidence": 0.9,
            },
        })

    with factory() as db:
        names = {category.name for category in db.query(Category).all()}
        assert "Mercado" not in names
        assert "Ifood" not in names
        assert "Freela" not in names
        assert {"Supermercado", "Delivery", "Freelance"}.issubset(names)


def test_pending_document_import_persists_after_confirmation(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.pending_actions import handle_pending_confirmation, save_pending_action

    summary = save_pending_action(
        "5511999999999",
        action="import_document_transactions",
        params={
            "transactions": [
                {
                    "date": "2026-05-01",
                    "description": "Mercado",
                    "amount": 42.1,
                    "type": "EXPENSE",
                    "category": "Supermercado",
                    "raw": "01/05/2026 Mercado 42,10",
                }
            ]
        },
        summary="Encontrei 1 transação para importar.",
    )

    assert "Confirma?" in summary
    response = handle_pending_confirmation("5511999999999", "sim")

    assert response is not None
    assert "Documento importado com sucesso!" in response
    assert "Valor: R$ 42,10 em Supermercado (Mercado) no dia 01/05/2026." in response
    with factory() as db:
        tx = db.query(Transaction).one()
        assert tx.description == "Mercado"
        assert tx.source_format == "document_import"


def test_pending_document_import_persists_unified_user_id_after_confirmation(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.pending_actions import handle_pending_confirmation, save_pending_action

    web_user_id = 10
    with factory() as db:
        web_user = User(
            id=web_user_id,
            email="linked-doc@bagcoin.com",
            hashed_password="x",
            phone_number="5511888888888",
            email_verified_at=datetime.now(UTC),
        )
        db.add(web_user)
        db.commit()

    save_pending_action(
        "5511888888888",
        action="import_document_transactions",
        params={
            "transactions": [
                {
                    "date": "2026-05-01",
                    "description": "Supermercado",
                    "amount": 185.77,
                    "type": "EXPENSE",
                    "category": "Supermercado",
                    "raw": "R$ 185,77 SUPERMERCADOS",
                }
            ]
        },
        summary="Encontrei 1 transação para importar.",
    )

    response = handle_pending_confirmation("5511888888888", "sim")

    assert response is not None
    with factory() as db:
        tx = db.query(Transaction).one()
        assert tx.user_id == web_user_id
        assert tx.category.name == "Supermercado"


def test_pending_document_import_uses_existing_unified_user_by_phone_digits(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.pending_actions import handle_pending_confirmation, save_pending_action

    web_user_id = 10
    with factory() as db:
        web_user = User(
            id=web_user_id,
            email="digits-doc@bagcoin.com",
            hashed_password="x",
            phone_number="+55 (11) 88888-8888",
            email_verified_at=datetime.now(UTC),
        )
        db.add(web_user)
        db.commit()

    save_pending_action(
        "5511888888888",
        action="import_document_transactions",
        params={
            "transactions": [
                {
                    "date": "2026-05-01",
                    "description": "Padaria",
                    "amount": 35.5,
                    "type": "EXPENSE",
                    "category": "Alimentação",
                    "raw": "Padaria R$ 35,50",
                }
            ]
        },
        summary="Encontrei 1 transação para importar.",
    )

    response = handle_pending_confirmation("5511888888888", "sim")

    assert response is not None
    with factory() as db:
        tx = db.query(Transaction).one()


def test_agent_lists_unified_user_transactions(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.persistence import get_user_transactions

    web_user_id = 10
    with factory() as db:
        web_user = User(
            id=web_user_id,
            email="linked-list@bagcoin.com",
            hashed_password="x",
            phone_number="5511777777777",
            email_verified_at=datetime.now(UTC),
        )
        tx = Transaction(
            user_id=web_user_id,
            type="EXPENSE",
            amount=42,
            description="Web manual",
            source_format="manual",
            transaction_date=datetime.now(UTC),
            confidence_score=1.0,
        )
        db.add_all([web_user, tx])
        db.commit()

    transactions = get_user_transactions("5511777777777")

    assert [tx.description for tx in transactions] == ["Web manual"]


def test_agent_updates_unified_user_transaction(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.persistence import update_transaction

    web_user_id = 10
    with factory() as db:
        web_user = User(
            id=web_user_id,
            email="linked-update@bagcoin.com",
            hashed_password="x",
            phone_number="5511666666666",
            email_verified_at=datetime.now(UTC),
        )
        tx = Transaction(
            user_id=web_user_id,
            type="EXPENSE",
            amount=42,
            description="Valor antigo",
            source_format="manual",
            transaction_date=datetime.now(UTC),
            confidence_score=1.0,
        )
        db.add_all([web_user, tx])
        db.commit()
        tx_id = tx.id

    result = update_transaction("5511666666666", tx_id, amount=64, description="Valor novo")

    assert result is not None
    assert result["amount"] == 64
    assert result["description"] == "Valor novo"
    with factory() as db:
        saved = db.query(Transaction).filter(Transaction.id == tx_id).one()
        assert saved.amount == 64
        assert saved.description == "Valor novo"


def test_agent_deletes_unified_user_transaction(monkeypatch):
    factory = _patch_agent_db(monkeypatch)
    from app.agents.persistence import delete_transaction_by_id

    web_user_id = 10
    with factory() as db:
        web_user = User(
            id=web_user_id,
            email="linked-delete@bagcoin.com",
            hashed_password="x",
            phone_number="5511555555555",
            email_verified_at=datetime.now(UTC),
        )
        tx = Transaction(
            user_id=web_user_id,
            type="EXPENSE",
            amount=18,
            description="Remover",
            source_format="manual",
            transaction_date=datetime.now(UTC),
            confidence_score=1.0,
        )
        db.add_all([web_user, tx])
        db.commit()
        tx_id = tx.id

    assert delete_transaction_by_id("5511555555555", tx_id) is True
    with factory() as db:
        assert db.query(Transaction).count() == 0


def test_pending_confirmation_accepts_sim_registre():
    from app.agents.pending_actions import pending_confirmation_decision

    assert pending_confirmation_decision("sim registre") == "confirm"
