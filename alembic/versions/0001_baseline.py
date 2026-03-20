"""baseline schema

Revision ID: 0001_baseline
Revises:
Create Date: 2026-03-01 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clientes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("documento", sa.String(length=50), nullable=True),
        sa.Column("contato", sa.String(length=255), nullable=True),
        sa.Column("telefone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("endereco", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clientes_nome", "clientes", ["nome"], unique=True)

    op.create_table(
        "tipos_producao",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tipos_producao_nome", "tipos_producao", ["nome"], unique=True)

    op.create_table(
        "status_producao",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_status_producao_nome", "status_producao", ["nome"], unique=True)

    op.create_table(
        "status_pagamento",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_status_pagamento_nome", "status_pagamento", ["nome"], unique=True)

    op.create_table(
        "producoes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=True),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("data_recebimento", sa.Date(), nullable=True),
        sa.Column("data_conclusao", sa.Date(), nullable=True),
        sa.Column("quantidade_alunos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pasta_producao", sa.Text(), nullable=True),
        sa.Column("relatorio", sa.Text(), nullable=True),
        sa.Column("valor_total", sa.Numeric(10, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("tipo_producao_id", sa.Integer(), nullable=False),
        sa.Column("status_producao_id", sa.Integer(), nullable=False),
        sa.Column("status_pagamento_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete=None),
        sa.ForeignKeyConstraint(["tipo_producao_id"], ["tipos_producao.id"], ondelete=None),
        sa.ForeignKeyConstraint(["status_producao_id"], ["status_producao.id"], ondelete=None),
        sa.ForeignKeyConstraint(["status_pagamento_id"], ["status_pagamento.id"], ondelete=None),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_producoes_codigo", "producoes", ["codigo"], unique=True)

    op.create_table(
        "itens_producao",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("producao_id", sa.Integer(), nullable=False),
        sa.Column("tipo_item", sa.String(length=50), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("quantidade", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valor_unitario", sa.Numeric(10, 2), nullable=True),
        sa.Column("valor_total", sa.Numeric(10, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["producao_id"], ["producoes.id"], ondelete=None),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_itens_producao_producao_id", "itens_producao", ["producao_id"], unique=False)

    op.create_table(
        "pagamentos_producao",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("producao_id", sa.Integer(), nullable=False),
        sa.Column("data_pagamento", sa.Date(), nullable=True),
        sa.Column("valor", sa.Numeric(10, 2), nullable=True),
        sa.Column("forma_pagamento", sa.String(length=100), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["producao_id"], ["producoes.id"], ondelete=None),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pagamentos_producao_producao_id", "pagamentos_producao", ["producao_id"], unique=False)

    op.create_table(
        "configuracoes",
        sa.Column("chave", sa.String(length=100), nullable=False),
        sa.Column("valor", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("chave"),
    )


def downgrade() -> None:
    op.drop_table("configuracoes")
    op.drop_index("ix_pagamentos_producao_producao_id", table_name="pagamentos_producao")
    op.drop_table("pagamentos_producao")
    op.drop_index("ix_itens_producao_producao_id", table_name="itens_producao")
    op.drop_table("itens_producao")
    op.drop_index("ix_producoes_codigo", table_name="producoes")
    op.drop_table("producoes")
    op.drop_index("ix_status_pagamento_nome", table_name="status_pagamento")
    op.drop_table("status_pagamento")
    op.drop_index("ix_status_producao_nome", table_name="status_producao")
    op.drop_table("status_producao")
    op.drop_index("ix_tipos_producao_nome", table_name="tipos_producao")
    op.drop_table("tipos_producao")
    op.drop_index("ix_clientes_nome", table_name="clientes")
    op.drop_table("clientes")
