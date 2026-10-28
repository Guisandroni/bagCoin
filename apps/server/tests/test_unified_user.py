"""Smoke test: verify all models and key services import without errors after user unification."""

import pytest


class TestUnifiedUserImports:
    """Verify the unified user model imports correctly across the codebase."""

    def test_models_import(self):
        from app.db.models import (
            User,
            UserRole,
            Transaction,
            Budget,
            BudgetItem,
            Goal,
            Report,
            Category,
            Account,
            CreditCard,
            RecurringTransaction,
            Conversation,
            Message,
            ToolCall,
            ChatFile,
            MessageRating,
            ConversationShare,
            PhoneConversation,
            AgentLog,
            IntegrationLinkToken,
        )
        # Verify User has unified fields
        assert hasattr(User, "email")
        assert hasattr(User, "phone_number")
        assert hasattr(User, "telegram_chat_id")
        assert hasattr(User, "preferences")
        assert hasattr(User, "financial_profile")
        assert hasattr(User, "platform")

    def test_user_model_pk_is_integer(self):
        from app.db.models.user import User
        col = User.__table__.c.id
        assert str(col.type) == "INTEGER"

    def test_transaction_has_single_user_fk(self):
        from app.db.models.transaction import Transaction
        cols = [c.name for c in Transaction.__table__.columns]
        assert "user_id" in cols
        assert not any(col == "user_" + "uuid" for col in cols)

    def test_budget_has_single_user_fk(self):
        from app.db.models.budget import Budget
        cols = [c.name for c in Budget.__table__.columns]
        assert "user_id" in cols
        assert "budget_date" in cols
        assert not any(col == "user_" + "uuid" for col in cols)

    def test_goal_has_single_user_fk(self):
        from app.db.models.goal import Goal
        cols = [c.name for c in Goal.__table__.columns]
        assert "user_id" in cols
        assert not any(col == "user_" + "uuid" for col in cols)

    def test_legacy_channel_user_model_removed(self):
        import importlib.util

        assert importlib.util.find_spec("app.db.models.phone_" + "user") is None

    def test_user_repo_has_phone_methods(self):
        from app.repositories import user as user_repo
        assert hasattr(user_repo, "get_by_phone_number")
        assert hasattr(user_repo, "get_or_create_by_phone")
        assert hasattr(user_repo, "get_by_telegram_chat_id")

    def test_user_service_has_phone_methods(self):
        from app.services.user import UserService
        assert hasattr(UserService, "get_or_create_by_phone")
        assert hasattr(UserService, "get_by_phone_number")

    def test_persistence_imports(self):
        from app.agents.persistence import (
            get_or_create_user_sync,
            get_or_create_user,
            save_transaction,
            get_user_transactions,
            list_categories,
        )
        assert callable(get_or_create_user_sync)

    def test_tenant_context_imports(self):
        from app.agents.tenant_context import (
            assert_valid_tenant_phone,
            assert_valid_tenant_user,
            tenant_phone_error,
            tenant_user_id_error,
        )
        assert tenant_phone_error(None) is not None
        assert tenant_user_id_error(None) is not None
        assert tenant_user_id_error(1) is None

    def test_schemas_use_int_id(self):
        from app.schemas.user import UserRead
        from pydantic import TypeAdapter
        adapter = TypeAdapter(UserRead)
        schema = adapter.json_schema()
        assert schema["properties"]["id"]["type"] == "integer"
