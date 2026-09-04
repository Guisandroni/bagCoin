"""add_agent_conversation_memory

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-24 20:30:00.000000

"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False, server_default="whatsapp"),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["phone_conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("conversation_messages_conversation_id_idx", "conversation_messages", ["conversation_id"])
    op.create_index("conversation_messages_user_id_idx", "conversation_messages", ["user_id"])

    op.create_table(
        "agent_memory_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("entity_id", sa.String(length=80), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=False, server_default="agent"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["phone_conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("agent_memory_events_user_id_idx", "agent_memory_events", ["user_id"])
    op.create_index("agent_memory_events_conversation_id_idx", "agent_memory_events", ["conversation_id"])
    op.create_index("agent_memory_events_event_type_idx", "agent_memory_events", ["event_type"])
    op.create_index("agent_memory_events_entity_type_idx", "agent_memory_events", ["entity_type"])
    op.create_index("agent_memory_events_entity_id_idx", "agent_memory_events", ["entity_id"])

    _migrate_legacy_message_history()


def downgrade() -> None:
    op.drop_index("agent_memory_events_entity_id_idx", table_name="agent_memory_events")
    op.drop_index("agent_memory_events_entity_type_idx", table_name="agent_memory_events")
    op.drop_index("agent_memory_events_event_type_idx", table_name="agent_memory_events")
    op.drop_index("agent_memory_events_conversation_id_idx", table_name="agent_memory_events")
    op.drop_index("agent_memory_events_user_id_idx", table_name="agent_memory_events")
    op.drop_table("agent_memory_events")

    op.drop_index("conversation_messages_user_id_idx", table_name="conversation_messages")
    op.drop_index("conversation_messages_conversation_id_idx", table_name="conversation_messages")
    op.drop_table("conversation_messages")


def _migrate_legacy_message_history() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, user_id, channel, message_history, created_at, updated_at "
            "FROM phone_conversations"
        )
    ).mappings()
    insert_rows = []
    for row in rows:
        history = row["message_history"] or []
        if isinstance(history, str):
            try:
                history = json.loads(history)
            except json.JSONDecodeError:
                history = []
        if not isinstance(history, list):
            continue
        for item in history:
            if not isinstance(item, dict):
                continue
            content = str(item.get("content") or "").strip()
            if not content:
                continue
            timestamp = _parse_timestamp(item.get("timestamp")) or row["created_at"] or datetime.utcnow()
            insert_rows.append({
                "conversation_id": row["id"],
                "user_id": row["user_id"],
                "channel": row["channel"] or "whatsapp",
                "role": str(item.get("role") or "user")[:20],
                "content": content,
                "metadata": {"migrated_from": "phone_conversations.message_history"},
                "created_at": timestamp,
                "updated_at": row["updated_at"],
            })
    if insert_rows:
        table = sa.table(
            "conversation_messages",
            sa.column("conversation_id", sa.Integer),
            sa.column("user_id", sa.Integer),
            sa.column("channel", sa.String),
            sa.column("role", sa.String),
            sa.column("content", sa.Text),
            sa.column("metadata", sa.JSON),
            sa.column("created_at", sa.DateTime(timezone=True)),
            sa.column("updated_at", sa.DateTime(timezone=True)),
        )
        bind.execute(table.insert(), insert_rows)


def _parse_timestamp(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
