"""add client receipts and receipt allocations

Revision ID: 0006_client_receipts
Revises: 0005_financial_expr_indexes
Create Date: 2026-03-09 18:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0006_client_receipts"
down_revision: Union[str, None] = "0005_financial_expr_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recebimentos_cliente",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("data_recebimento", sa.Date(), nullable=True),
        sa.Column("valor_total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("valor_nao_alocado", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("forma_pagamento", sa.String(length=100), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("origem", sa.String(length=50), nullable=False, server_default="MANUAL"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recebimentos_cliente_cliente_id", "recebimentos_cliente", ["cliente_id"], unique=False)
    op.create_index(
        "ix_recebimentos_cliente_cliente_data_id",
        "recebimentos_cliente",
        ["cliente_id", "data_recebimento", "id"],
        unique=False,
    )

    op.create_table(
        "alocacoes_recebimento",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("recebimento_id", sa.Integer(), nullable=False),
        sa.Column("producao_id", sa.Integer(), nullable=False),
        sa.Column("valor_alocado", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["recebimento_id"], ["recebimentos_cliente.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["producao_id"], ["producoes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alocacoes_recebimento_recebimento_id", "alocacoes_recebimento", ["recebimento_id"], unique=False)
    op.create_index("ix_alocacoes_recebimento_producao_id", "alocacoes_recebimento", ["producao_id"], unique=False)

    bind = op.get_bind()
    bind.execute(
        sa.text(
            "INSERT INTO status_pagamento (nome, ordem, ativo) "
            "SELECT 'Parcial', 2, 1 "
            "WHERE NOT EXISTS (SELECT 1 FROM status_pagamento WHERE nome = 'Parcial')"
        )
    )
    bind.execute(sa.text("UPDATE status_pagamento SET ordem = 1, ativo = 1 WHERE nome = 'Em aberto'"))
    bind.execute(sa.text("UPDATE status_pagamento SET ordem = 2, ativo = 1 WHERE nome = 'Parcial'"))
    bind.execute(sa.text("UPDATE status_pagamento SET ordem = 3, ativo = 1 WHERE nome = 'Pago'"))

    paid_rows = bind.execute(
        sa.text(
            """
            SELECT
                p.id AS producao_id,
                p.cliente_id AS cliente_id,
                COALESCE(p.data_conclusao, p.data_recebimento, DATE(p.created_at), DATE('now')) AS data_ref,
                COALESCE(p.valor_total, 0) AS valor_total
            FROM producoes p
            JOIN status_pagamento sp ON sp.id = p.status_pagamento_id
            WHERE lower(trim(sp.nome)) = 'pago'
            ORDER BY p.id
            """
        )
    ).mappings()

    for row in paid_rows:
        receipt_result = bind.execute(
            sa.text(
                """
                INSERT INTO recebimentos_cliente (
                    cliente_id,
                    data_recebimento,
                    valor_total,
                    valor_nao_alocado,
                    forma_pagamento,
                    observacao,
                    origem,
                    created_at,
                    updated_at
                )
                VALUES (
                    :cliente_id,
                    :data_recebimento,
                    :valor_total,
                    0,
                    'MIGRACAO',
                    'Backfill automático de produção paga',
                    'MIGRACAO',
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "cliente_id": row["cliente_id"],
                "data_recebimento": row["data_ref"],
                "valor_total": row["valor_total"],
            },
        )
        bind.execute(
            sa.text(
                """
                INSERT INTO alocacoes_recebimento (
                    recebimento_id,
                    producao_id,
                    valor_alocado,
                    created_at
                )
                VALUES (
                    :recebimento_id,
                    :producao_id,
                    :valor_alocado,
                    CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "recebimento_id": receipt_result.lastrowid,
                "producao_id": row["producao_id"],
                "valor_alocado": row["valor_total"],
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM status_pagamento WHERE nome = 'Parcial'"))
    bind.execute(sa.text("UPDATE status_pagamento SET ordem = 1, ativo = 1 WHERE nome = 'Em aberto'"))
    bind.execute(sa.text("UPDATE status_pagamento SET ordem = 2, ativo = 1 WHERE nome = 'Pago'"))

    op.drop_index("ix_alocacoes_recebimento_producao_id", table_name="alocacoes_recebimento")
    op.drop_index("ix_alocacoes_recebimento_recebimento_id", table_name="alocacoes_recebimento")
    op.drop_table("alocacoes_recebimento")
    op.drop_index("ix_recebimentos_cliente_cliente_data_id", table_name="recebimentos_cliente")
    op.drop_index("ix_recebimentos_cliente_cliente_id", table_name="recebimentos_cliente")
    op.drop_table("recebimentos_cliente")
