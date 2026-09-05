"""merge_reports_and_recurring_heads

Revision ID: 9a8b7c6d5e4f
Revises: 73bb5f501751, 7e9c2a4b8f11
Create Date: 2026-05-09 23:35:00.000000

"""
from typing import Sequence, Union


revision: str = "9a8b7c6d5e4f"
down_revision: Union[str, tuple[str, str], None] = ("73bb5f501751", "7e9c2a4b8f11")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
