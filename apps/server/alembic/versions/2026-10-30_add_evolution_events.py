"""Add durable Evolution event and reply records.

Revision ID: 47ecb19df524
Revises: f6a7b8c9d0e1
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "47ecb19df524"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evolution_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("instance", sa.String(100), nullable=False),
        sa.Column("message_id", sa.String(255), nullable=False),
        sa.Column("owner", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("instance", "message_id", name="uq_evolution_event_instance_message"),
        sa.CheckConstraint("status IN ('processing', 'completed', 'uncertain')", name="evolution_event_status"),
    )
    op.create_table(
        "evolution_replies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("evolution_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("event_id", "position", name="uq_evolution_reply_event_position"),
        sa.CheckConstraint("status IN ('pending', 'sending', 'sent', 'uncertain')", name="evolution_reply_status"),
    )


def downgrade() -> None:
    op.drop_table("evolution_replies")
    op.drop_table("evolution_events")
