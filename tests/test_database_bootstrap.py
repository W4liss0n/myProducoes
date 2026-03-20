from __future__ import annotations

import importlib.util
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import text

from src.infrastructure.sqlite.orm import get_engine

HAS_ALEMBIC = importlib.util.find_spec("alembic.command") is not None
if HAS_ALEMBIC:
    from alembic import command
    from alembic.config import Config
    from src.infrastructure.sqlite.backup import SqliteBackupService
    from src.infrastructure.sqlite.bootstrap import SqliteDatabaseBootstrap

ROOT_DIR = Path(__file__).resolve().parent.parent


@unittest.skipUnless(HAS_ALEMBIC, "Alembic package não instalado no ambiente de teste.")
class TestDatabaseBootstrap(unittest.TestCase):
    def _build_alembic_config(self, db_path: Path) -> Config:
        cfg = Config()
        cfg.set_main_option("script_location", str(ROOT_DIR / "alembic"))
        cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
        return cfg

    def _seed_legacy_db(self, db_path: Path) -> None:
        cfg = self._build_alembic_config(db_path)
        command.upgrade(cfg, "0001_baseline")

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE alembic_version")

            cursor.execute("INSERT INTO clientes (nome) VALUES ('Cliente Legacy')")
            cursor.execute("INSERT INTO tipos_producao (nome) VALUES ('Formatura')")
            cursor.execute("INSERT INTO status_producao (nome, ordem, ativo) VALUES ('Parado', 1, 1)")
            cursor.execute("INSERT INTO status_pagamento (nome, ordem, ativo) VALUES ('pago', 2, 1)")

            cursor.execute("SELECT id FROM clientes WHERE nome='Cliente Legacy'")
            cliente_id = int(cursor.fetchone()[0])
            cursor.execute("SELECT id FROM tipos_producao WHERE nome='Formatura'")
            tipo_id = int(cursor.fetchone()[0])
            cursor.execute("SELECT id FROM status_producao WHERE nome='Parado'")
            status_producao_id = int(cursor.fetchone()[0])
            cursor.execute("SELECT id FROM status_pagamento WHERE nome='pago'")
            status_pagamento_id = int(cursor.fetchone()[0])

            cursor.execute(
                """
                INSERT INTO producoes (
                    codigo, nome, data_recebimento, quantidade_alunos, valor_total,
                    cliente_id, tipo_producao_id, status_producao_id, status_pagamento_id
                )
                VALUES ('LEG-2026-001', 'Produção Legada', '2026-01-10', 1, 100.0, ?, ?, ?, ?)
                """,
                (cliente_id, tipo_id, status_producao_id, status_pagamento_id),
            )

            # Inserir órfão propositalmente (foreign keys OFF por padrão em conexão sqlite3)
            cursor.execute(
                """
                INSERT INTO itens_producao (producao_id, tipo_item, quantidade, valor_unitario, valor_total)
                VALUES (999999, 'FOTO', 1, 10.0, 10.0)
                """
            )
            conn.commit()

    def test_legacy_migration_sanitizes_and_versions_database(self) -> None:
        tmp_dir = Path(tempfile.mkdtemp())
        try:
            db_path = tmp_dir / "legacy.db"
            self._seed_legacy_db(db_path)

            bootstrap = SqliteDatabaseBootstrap(
                db_path=db_path,
                alembic_ini_path=ROOT_DIR / "alembic.ini",
                backup_dir=tmp_dir / "backups",
            )
            bootstrap.backup_service = SqliteBackupService(db_path=db_path, backup_dir=tmp_dir / "backups")
            bootstrap.ensure_ready()

            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA foreign_key_check")
                self.assertEqual(cursor.fetchall(), [])

                cursor.execute("SELECT version_num FROM alembic_version")
                versions = [row[0] for row in cursor.fetchall()]
                self.assertEqual(versions, ["0006_client_receipts"])

                cursor.execute("SELECT nome FROM status_pagamento ORDER BY nome")
                status_pagamento = [row[0] for row in cursor.fetchall()]
                self.assertEqual(status_pagamento, ["Em aberto", "Pago", "Parcial"])

                cursor.execute(
                    "SELECT COUNT(*), MIN(origem), MIN(forma_pagamento) FROM recebimentos_cliente"
                )
                receipt_count, origem, forma_pagamento = cursor.fetchone()
                self.assertEqual(receipt_count, 1)
                self.assertEqual(origem, "MIGRACAO")
                self.assertEqual(forma_pagamento, "MIGRACAO")

                cursor.execute("SELECT COUNT(*) FROM alocacoes_recebimento")
                self.assertEqual(cursor.fetchone()[0], 1)

                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='producoes' ORDER BY name"
                )
                indexes = {row[0] for row in cursor.fetchall()}
                self.assertIn("ix_producoes_recebimento_year", indexes)
                self.assertIn("ix_producoes_recebimento_year_month", indexes)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_sqlalchemy_engine_enables_foreign_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "fk.db"
            engine = get_engine(db_path)
            with engine.connect() as conn:
                pragma_value = conn.execute(text("PRAGMA foreign_keys")).scalar()
            engine.dispose()
            self.assertEqual(pragma_value, 1)


if __name__ == "__main__":
    unittest.main()
