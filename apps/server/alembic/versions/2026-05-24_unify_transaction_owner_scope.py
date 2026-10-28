"""unify_transaction_owner_scope (superseded by full user unification)

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-24 00:00:00.000000

"""
from typing import Sequence, Union

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Superseded by d4e5f6a7b8c9 (unify_users_table)
    pass


def downgrade() -> None:
    pass
