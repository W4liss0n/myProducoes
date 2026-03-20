"""normalize and lock canonical statuses

Revision ID: 0003_status_canonical
Revises: 0002_fk_integrity
Create Date: 2026-03-01 10:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_status_canonical"
down_revision: Union[str, None] = "0002_fk_integrity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(sa.text("INSERT INTO status_producao (nome, ordem, ativo) SELECT 'Parado', 1, 1 WHERE NOT EXISTS (SELECT 1 FROM status_producao WHERE nome = 'Parado')"))
    bind.execute(sa.text("INSERT INTO status_producao (nome, ordem, ativo) SELECT 'Em Andamento', 2, 1 WHERE NOT EXISTS (SELECT 1 FROM status_producao WHERE nome = 'Em Andamento')"))
    bind.execute(sa.text("INSERT INTO status_producao (nome, ordem, ativo) SELECT 'Finalizado', 3, 1 WHERE NOT EXISTS (SELECT 1 FROM status_producao WHERE nome = 'Finalizado')"))

    bind.execute(sa.text("INSERT INTO status_pagamento (nome, ordem, ativo) SELECT 'Em aberto', 1, 1 WHERE NOT EXISTS (SELECT 1 FROM status_pagamento WHERE nome = 'Em aberto')"))
    bind.execute(sa.text("INSERT INTO status_pagamento (nome, ordem, ativo) SELECT 'Pago', 2, 1 WHERE NOT EXISTS (SELECT 1 FROM status_pagamento WHERE nome = 'Pago')"))

    bind.execute(sa.text("""
        UPDATE producoes
        SET status_producao_id = (SELECT id FROM status_producao WHERE nome = 'Parado' LIMIT 1)
        WHERE status_producao_id IN (
            SELECT id FROM status_producao WHERE lower(trim(nome)) = 'parado'
        )
    """))
    bind.execute(sa.text("""
        UPDATE producoes
        SET status_producao_id = (SELECT id FROM status_producao WHERE nome = 'Em Andamento' LIMIT 1)
        WHERE status_producao_id IN (
            SELECT id FROM status_producao WHERE lower(trim(nome)) = 'em andamento'
        )
    """))
    bind.execute(sa.text("""
        UPDATE producoes
        SET status_producao_id = (SELECT id FROM status_producao WHERE nome = 'Finalizado' LIMIT 1)
        WHERE status_producao_id IN (
            SELECT id FROM status_producao WHERE lower(trim(nome)) = 'finalizado'
        )
    """))

    bind.execute(sa.text("""
        UPDATE producoes
        SET status_pagamento_id = (SELECT id FROM status_pagamento WHERE nome = 'Em aberto' LIMIT 1)
        WHERE status_pagamento_id IN (
            SELECT id FROM status_pagamento WHERE lower(trim(nome)) = 'em aberto'
        )
    """))
    bind.execute(sa.text("""
        UPDATE producoes
        SET status_pagamento_id = (SELECT id FROM status_pagamento WHERE nome = 'Pago' LIMIT 1)
        WHERE status_pagamento_id IN (
            SELECT id FROM status_pagamento WHERE lower(trim(nome)) = 'pago'
        )
    """))

    bind.execute(sa.text("""
        UPDATE producoes
        SET status_producao_id = (SELECT id FROM status_producao WHERE nome = 'Parado' LIMIT 1)
        WHERE status_producao_id NOT IN (
            SELECT id FROM status_producao WHERE nome IN ('Parado', 'Em Andamento', 'Finalizado')
        )
    """))

    bind.execute(sa.text("""
        UPDATE producoes
        SET status_pagamento_id = (SELECT id FROM status_pagamento WHERE nome = 'Em aberto' LIMIT 1)
        WHERE status_pagamento_id NOT IN (
            SELECT id FROM status_pagamento WHERE nome IN ('Em aberto', 'Pago')
        )
    """))

    bind.execute(sa.text("DELETE FROM status_producao WHERE nome NOT IN ('Parado', 'Em Andamento', 'Finalizado')"))
    bind.execute(sa.text("DELETE FROM status_pagamento WHERE nome NOT IN ('Em aberto', 'Pago')"))

    bind.execute(sa.text("UPDATE status_producao SET ordem = 1, ativo = 1 WHERE nome = 'Parado'"))
    bind.execute(sa.text("UPDATE status_producao SET ordem = 2, ativo = 1 WHERE nome = 'Em Andamento'"))
    bind.execute(sa.text("UPDATE status_producao SET ordem = 3, ativo = 1 WHERE nome = 'Finalizado'"))
    bind.execute(sa.text("UPDATE status_pagamento SET ordem = 1, ativo = 1 WHERE nome = 'Em aberto'"))
    bind.execute(sa.text("UPDATE status_pagamento SET ordem = 2, ativo = 1 WHERE nome = 'Pago'"))

    bind.execute(sa.text("CREATE UNIQUE INDEX IF NOT EXISTS ux_status_producao_nome_ci ON status_producao (LOWER(nome))"))
    bind.execute(sa.text("CREATE UNIQUE INDEX IF NOT EXISTS ux_status_pagamento_nome_ci ON status_pagamento (LOWER(nome))"))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DROP INDEX IF EXISTS ux_status_producao_nome_ci"))
    bind.execute(sa.text("DROP INDEX IF EXISTS ux_status_pagamento_nome_ci"))
