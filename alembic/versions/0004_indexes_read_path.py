"""add read path indexes for listing and financial queries

Revision ID: 0004_indexes_read_path
Revises: 0003_status_canonical
Create Date: 2026-03-01 10:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_indexes_read_path"
down_revision: Union[str, None] = "0003_status_canonical"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    op.create_index("ix_producoes_cliente_id", "producoes", ["cliente_id"], unique=False)
    op.create_index("ix_producoes_tipo_producao_id", "producoes", ["tipo_producao_id"], unique=False)
    op.create_index("ix_producoes_status_producao_id", "producoes", ["status_producao_id"], unique=False)
    op.create_index("ix_producoes_status_pagamento_id", "producoes", ["status_pagamento_id"], unique=False)
    op.create_index("ix_producoes_data_recebimento", "producoes", ["data_recebimento"], unique=False)
    op.create_index("ix_producoes_data_conclusao", "producoes", ["data_conclusao"], unique=False)

    bind.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_producoes_data_recebimento_id_desc ON producoes (data_recebimento DESC, id DESC)"))
    bind.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_producoes_cliente_status_pagamento_data ON producoes (cliente_id, status_pagamento_id, data_recebimento)"))
    bind.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_producoes_tipo_status_data ON producoes (tipo_producao_id, status_producao_id, data_recebimento)"))


def downgrade() -> None:
    bind = op.get_bind()

    bind.execute(sa.text("DROP INDEX IF EXISTS ix_producoes_tipo_status_data"))
    bind.execute(sa.text("DROP INDEX IF EXISTS ix_producoes_cliente_status_pagamento_data"))
    bind.execute(sa.text("DROP INDEX IF EXISTS ix_producoes_data_recebimento_id_desc"))

    op.drop_index("ix_producoes_data_conclusao", table_name="producoes")
    op.drop_index("ix_producoes_data_recebimento", table_name="producoes")
    op.drop_index("ix_producoes_status_pagamento_id", table_name="producoes")
    op.drop_index("ix_producoes_status_producao_id", table_name="producoes")
    op.drop_index("ix_producoes_tipo_producao_id", table_name="producoes")
    op.drop_index("ix_producoes_cliente_id", table_name="producoes")
