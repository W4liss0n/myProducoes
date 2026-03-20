from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Iterable

from alembic import command
from alembic.config import Config

from ...config.constants import ALEMBIC_BASELINE_REVISION, ALEMBIC_INI_FILE, DATABASE_FILE
from .backup import SqliteBackupService

logger = logging.getLogger(__name__)

_LEGACY_REQUIRED_SCHEMA: dict[str, set[str]] = {
    "clientes": {"id", "nome"},
    "tipos_producao": {"id", "nome"},
    "status_producao": {"id", "nome"},
    "status_pagamento": {"id", "nome"},
    "producoes": {"id", "cliente_id", "tipo_producao_id", "status_producao_id", "status_pagamento_id"},
    "itens_producao": {"id", "producao_id"},
    "pagamentos_producao": {"id", "producao_id"},
    "configuracoes": {"chave", "valor"},
}

_REQUIRED_PRODUCOES_INDEXES = {
    "ix_producoes_codigo",
    "ix_producoes_cliente_id",
    "ix_producoes_tipo_producao_id",
    "ix_producoes_status_producao_id",
    "ix_producoes_status_pagamento_id",
    "ix_producoes_data_recebimento",
    "ix_producoes_data_conclusao",
    "ix_producoes_data_recebimento_id_desc",
    "ix_producoes_cliente_status_pagamento_data",
    "ix_producoes_tipo_status_data",
    "ix_producoes_recebimento_year",
    "ix_producoes_recebimento_year_month",
}

_CANONICAL_STATUS_PRODUCAO = {"Parado", "Em Andamento", "Finalizado"}
_CANONICAL_STATUS_PAGAMENTO = {"Em aberto", "Parcial", "Pago"}


class SqliteDatabaseBootstrap:
    def __init__(
        self,
        db_path: Path | str | None = None,
        alembic_ini_path: Path | str | None = None,
        backup_dir: Path | str | None = None,
    ) -> None:
        self.db_path = Path(db_path or DATABASE_FILE)
        self.alembic_ini_path = Path(alembic_ini_path or ALEMBIC_INI_FILE)
        self.backup_service = SqliteBackupService(db_path=self.db_path, backup_dir=backup_dir)

    def ensure_ready(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        db_exists = self.db_path.exists() and self.db_path.stat().st_size > 0
        if db_exists:
            backup_path = self.backup_service.create_backup(reason="pre_migration")
            if backup_path:
                logger.info("Backup pré-migração criado: %s", backup_path)

        alembic_cfg = self._build_alembic_config()
        if not db_exists:
            command.upgrade(alembic_cfg, "head")
            self._validate_database()
            return

        if not self._has_alembic_version_table():
            self._validate_legacy_schema_for_stamp()
            logger.info("Banco sem versionamento Alembic. Aplicando stamp em %s.", ALEMBIC_BASELINE_REVISION)
            command.stamp(alembic_cfg, ALEMBIC_BASELINE_REVISION)

        command.upgrade(alembic_cfg, "head")
        self._validate_database()

    def _build_alembic_config(self) -> Config:
        if not self.alembic_ini_path.exists():
            raise FileNotFoundError(f"Arquivo Alembic não encontrado: {self.alembic_ini_path}")

        config = Config()
        script_location = self.alembic_ini_path.parent / "alembic"
        config.set_main_option("script_location", str(script_location))
        config.set_main_option("sqlalchemy.url", f"sqlite:///{self.db_path.as_posix()}")
        return config

    def _has_alembic_version_table(self) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='alembic_version' LIMIT 1")
            return cursor.fetchone() is not None

    def _validate_legacy_schema_for_stamp(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}
            missing_tables = [table for table in _LEGACY_REQUIRED_SCHEMA if table not in tables]
            if missing_tables:
                raise RuntimeError(
                    "Schema legado incompatível para stamp Alembic. "
                    f"Tabelas ausentes: {', '.join(sorted(missing_tables))}"
                )

            for table, required_columns in _LEGACY_REQUIRED_SCHEMA.items():
                cursor.execute(f"PRAGMA table_info({table})")
                existing_columns = {row[1] for row in cursor.fetchall()}
                missing_columns = sorted(required_columns - existing_columns)
                if missing_columns:
                    raise RuntimeError(
                        "Schema legado incompatível para stamp Alembic. "
                        f"Tabela '{table}' sem colunas mínimas: {', '.join(missing_columns)}"
                    )

    def _fetch_unique_values(self, conn: sqlite3.Connection, table: str) -> set[str]:
        cursor = conn.cursor()
        cursor.execute(f"SELECT DISTINCT nome FROM {table}")
        return {str(row[0]) for row in cursor.fetchall() if row[0]}

    def _fetch_casefold_duplicates(self, conn: sqlite3.Connection, table: str) -> list[tuple[str, int]]:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT lower(trim(nome)) AS nome_norm, COUNT(*) AS quantidade
            FROM {table}
            GROUP BY nome_norm
            HAVING COUNT(*) > 1
            """
        )
        return [(str(row[0]), int(row[1])) for row in cursor.fetchall()]

    def _ensure_indexes(self, conn: sqlite3.Connection, required_indexes: Iterable[str]) -> None:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='producoes'")
        existing = {row[0] for row in cursor.fetchall()}
        missing = sorted(set(required_indexes) - existing)
        if missing:
            raise RuntimeError(f"Índices obrigatórios ausentes em producoes: {', '.join(missing)}")

    def _validate_database(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")

            cursor.execute("PRAGMA integrity_check")
            integrity = cursor.fetchone()
            if not integrity or integrity[0] != "ok":
                raise RuntimeError(f"integrity_check falhou após bootstrap: {integrity}")

            cursor.execute("PRAGMA foreign_key_check")
            issues = cursor.fetchall()
            if issues:
                raise RuntimeError(f"foreign_key_check falhou após bootstrap: {issues}")

            duplicates_pagamento = self._fetch_casefold_duplicates(conn, "status_pagamento")
            duplicates_producao = self._fetch_casefold_duplicates(conn, "status_producao")
            if duplicates_pagamento or duplicates_producao:
                raise RuntimeError(
                    "Status duplicados por case-insensitive após bootstrap: "
                    f"status_pagamento={duplicates_pagamento}, status_producao={duplicates_producao}"
                )

            status_pagamento = self._fetch_unique_values(conn, "status_pagamento")
            if status_pagamento != _CANONICAL_STATUS_PAGAMENTO:
                raise RuntimeError(
                    "Status de pagamento fora do conjunto canônico após bootstrap: "
                    f"{sorted(status_pagamento)}"
                )

            status_producao = self._fetch_unique_values(conn, "status_producao")
            if status_producao != _CANONICAL_STATUS_PRODUCAO:
                raise RuntimeError(
                    "Status de produção fora do conjunto canônico após bootstrap: "
                    f"{sorted(status_producao)}"
                )

            self._ensure_indexes(conn, _REQUIRED_PRODUCOES_INDEXES)
