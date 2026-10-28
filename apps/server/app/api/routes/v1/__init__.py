"""API v1 router aggregation."""
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals

from fastapi import APIRouter

from app.api.routes.v1 import health
from app.api.routes.v1 import admin_ratings, auth, support, users
from app.api.routes.v1 import conversations
from app.api.routes.v1 import admin_conversations
from app.api.routes.v1 import agent
from app.api.routes.v1 import files
from app.api.routes.v1 import webhook

# BagCoin REST endpoints
from app.api.routes.v1 import categories, exports, transactions
from app.api.routes.v1 import budgets, goals, reports
from app.api.routes.v1 import credit_cards, accounts
from app.api.routes.v1 import bagcoin_conversations
from app.api.routes.v1 import integrations

v1_router = APIRouter()

# Health check routes (no auth required)
v1_router.include_router(health.router, tags=["health"])

# Authentication routes
v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
v1_router.include_router(support.router)

# User routes
v1_router.include_router(users.router, prefix="/users", tags=["users"])

v1_router.include_router(
    integrations.router, prefix="/integrations", tags=["integrations"]
)

# Admin routes
v1_router.include_router(admin_ratings.router, prefix="/admin/ratings", tags=["admin:ratings"])

# Conversation routes (AI chat persistence)
v1_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])

# AI Agent routes
v1_router.include_router(agent.router, tags=["agent"])

# File upload/download routes
v1_router.include_router(files.router, tags=["files"])

# Admin: conversation browser + user listing
v1_router.include_router(
    admin_conversations.router, prefix="/admin/conversations", tags=["admin-conversations"]
)

# BagCoin Webhook routes (WhatsApp)
v1_router.include_router(webhook.router, tags=["webhook"])

# BagCoin REST endpoints
v1_router.include_router(categories.router, prefix="/bagcoin")
v1_router.include_router(exports.router)
v1_router.include_router(transactions.router, prefix="/bagcoin/transactions", tags=["bagcoin"])
v1_router.include_router(budgets.router)
v1_router.include_router(goals.router)
v1_router.include_router(reports.router)
v1_router.include_router(credit_cards.router)
v1_router.include_router(accounts.router)
v1_router.include_router(bagcoin_conversations.router)
