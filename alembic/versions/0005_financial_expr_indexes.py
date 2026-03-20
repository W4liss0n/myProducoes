"""add expression indexes for financial year/month grouping

Revision ID: 0005_financial_expr_indexes
Revises: 0004_indexes_read_path
Create Date: 2026-03-01 14:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0005_financial_expr_indexes"
down_revision: Union[str, None] = "0004_indexes_read_path"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_producoes_recebimento_year "
            "ON producoes (strftime('%Y', data_recebimento))"
        )
    )
    bind.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_producoes_recebimento_year_month "
            "ON producoes (strftime('%Y-%m', data_recebimento))"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DROP INDEX IF EXISTS ix_producoes_recebimento_year_month"))
    bind.execute(sa.text("DROP INDEX IF EXISTS ix_producoes_recebimento_year"))
