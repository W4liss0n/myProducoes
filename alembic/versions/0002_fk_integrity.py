"""enforce FK cascade and clean orphan rows

Revision ID: 0002_fk_integrity
Revises: 0001_baseline
Create Date: 2026-03-01 10:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_fk_integrity"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rebuild_itens_table_with_fk(on_delete_cascade: bool) -> None:
    bind = op.get_bind()
    fk_clause = "ON DELETE CASCADE" if on_delete_cascade else "ON DELETE NO ACTION"

    bind.execute(sa.text(
        f"""
        CREATE TABLE itens_producao_new (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            producao_id INTEGER NOT NULL,
            tipo_item VARCHAR(50) NOT NULL,
            descricao TEXT,
            quantidade INTEGER DEFAULT 0 NOT NULL,
            valor_unitario NUMERIC(10, 2),
            valor_total NUMERIC(10, 2),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            FOREIGN KEY(producao_id) REFERENCES producoes (id) {fk_clause}
        )
        """
    ))

    bind.execute(sa.text(
        """
        INSERT INTO itens_producao_new (
            id,
            producao_id,
            tipo_item,
            descricao,
            quantidade,
            valor_unitario,
            valor_total,
            created_at,
            updated_at
        )
        SELECT
            id,
            producao_id,
            tipo_item,
            descricao,
            quantidade,
            valor_unitario,
            valor_total,
            created_at,
            updated_at
        FROM itens_producao
        WHERE producao_id IN (SELECT id FROM producoes)
        """
    ))

    bind.execute(sa.text("DROP TABLE itens_producao"))
    bind.execute(sa.text("ALTER TABLE itens_producao_new RENAME TO itens_producao"))
    bind.execute(sa.text("CREATE INDEX ix_itens_producao_producao_id ON itens_producao (producao_id)"))


def _rebuild_pagamentos_table_with_fk(on_delete_cascade: bool) -> None:
    bind = op.get_bind()
    fk_clause = "ON DELETE CASCADE" if on_delete_cascade else "ON DELETE NO ACTION"

    bind.execute(sa.text(
        f"""
        CREATE TABLE pagamentos_producao_new (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            producao_id INTEGER NOT NULL,
            data_pagamento DATE,
            valor NUMERIC(10, 2),
            forma_pagamento VARCHAR(100),
            observacao TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            FOREIGN KEY(producao_id) REFERENCES producoes (id) {fk_clause}
        )
        """
    ))

    bind.execute(sa.text(
        """
        INSERT INTO pagamentos_producao_new (
            id,
            producao_id,
            data_pagamento,
            valor,
            forma_pagamento,
            observacao,
            created_at,
            updated_at
        )
        SELECT
            id,
            producao_id,
            data_pagamento,
            valor,
            forma_pagamento,
            observacao,
            created_at,
            updated_at
        FROM pagamentos_producao
        WHERE producao_id IN (SELECT id FROM producoes)
        """
    ))

    bind.execute(sa.text("DROP TABLE pagamentos_producao"))
    bind.execute(sa.text("ALTER TABLE pagamentos_producao_new RENAME TO pagamentos_producao"))
    bind.execute(sa.text("CREATE INDEX ix_pagamentos_producao_producao_id ON pagamentos_producao (producao_id)"))


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(sa.text("PRAGMA foreign_keys=OFF"))
    bind.execute(sa.text("DELETE FROM itens_producao WHERE producao_id NOT IN (SELECT id FROM producoes)"))
    bind.execute(sa.text("DELETE FROM pagamentos_producao WHERE producao_id NOT IN (SELECT id FROM producoes)"))

    _rebuild_itens_table_with_fk(on_delete_cascade=True)
    _rebuild_pagamentos_table_with_fk(on_delete_cascade=True)

    bind.execute(sa.text("PRAGMA foreign_keys=ON"))
    fk_issues = bind.execute(sa.text("PRAGMA foreign_key_check")).fetchall()
    if fk_issues:
        raise RuntimeError(f"foreign_key_check failed after 0002_fk_integrity: {fk_issues}")


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("PRAGMA foreign_keys=OFF"))

    _rebuild_itens_table_with_fk(on_delete_cascade=False)
    _rebuild_pagamentos_table_with_fk(on_delete_cascade=False)

    bind.execute(sa.text("PRAGMA foreign_keys=ON"))
