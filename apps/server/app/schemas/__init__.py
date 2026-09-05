"""Pydantic schemas."""
# ruff: noqa: I001, RUF022 - Imports structured for Jinja2 template conditionals

from app.schemas.token import Token, TokenPayload
from app.schemas.auth import (
    AuthPendingResponse,
    EmailVerificationRequest,
    EmailVerificationResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
)
from app.schemas.user import UserCreate, UserRead, UserUpdate

from app.schemas.conversation import (
    ConversationCreate,
    ConversationRead,
    ConversationUpdate,
    MessageCreate,
    MessageRead,
    ToolCallRead,
)

# BagCoin schemas
from app.schemas.enums import IntentType, SourceFormat, TransactionType, GoalStatus
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse, BudgetItemSchema
from app.schemas.goal import GoalCreate, GoalUpdate, GoalResponse
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.schemas.common import (
    WebhookPayload,
    WhatsAppResponse,
    ExtractedTransaction,
    QueryResult,
    ReportRequest,
    AgentState,
)

__all__ = [
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "Token",
    "TokenPayload",
    "AuthPendingResponse",
    "EmailVerificationRequest",
    "EmailVerificationResponse",
    "ResendVerificationRequest",
    "ResendVerificationResponse",
    "ConversationCreate",
    "ConversationRead",
    "ConversationUpdate",
    "MessageCreate",
    "MessageRead",
    "ToolCallRead",
    # BagCoin schemas
    "IntentType",
    "SourceFormat",
    "TransactionType",
    "GoalStatus",
    "TransactionCreate",
    "TransactionUpdate",
    "TransactionResponse",
    "BudgetCreate",
    "BudgetUpdate",
    "BudgetResponse",
    "BudgetItemSchema",
    "GoalCreate",
    "GoalUpdate",
    "GoalResponse",
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryResponse",
    "WebhookPayload",
    "WhatsAppResponse",
    "ExtractedTransaction",
    "QueryResult",
    "ReportRequest",
    "AgentState",
]
