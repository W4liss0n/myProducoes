from __future__ import annotations

import logging
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from ...config.constants import AUTO_BACKUP_LAST_DATE_KEY, BACKUP_DIR, DATABASE_FILE, MAX_BACKUPS

logger = logging.getLogger(__name__)


class SqliteBackupService:
    def __init__(
        self,
        db_path: Path | str | None = None,
        backup_dir: Path | str | None = None,
        max_backups: int = MAX_BACKUPS,
    ) -> None:
        self.db_path = Path(db_path or DATABASE_FILE)
        self.backup_dir = Path(backup_dir or BACKUP_DIR)
        self.max_backups = max_backups

    def create_backup(self, reason: str = "manual") -> Path | None:
        if not self.db_path.exists():
            logger.warning("Backup ignorado: banco não existe em %s", self.db_path)
            return None

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_reason = reason.strip().replace(" ", "_") or "manual"
        backup_path = self.backup_dir / f"productions_{timestamp}_{safe_reason}.db"
        shutil.copy2(self.db_path, backup_path)
        self._rotate_backups()
        logger.info("Backup criado: %s", backup_path)
        return backup_path

    def maybe_create_daily_backup(self) -> Path | None:
        today = datetime.now().strftime("%Y-%m-%d")
        last_backup_day = self._get_metadata_value(AUTO_BACKUP_LAST_DATE_KEY)
        if last_backup_day == today:
            return None

        backup_path = self.create_backup(reason="daily_auto")
        if backup_path:
            self._set_metadata_value(AUTO_BACKUP_LAST_DATE_KEY, today)
        return backup_path

    def restore_backup(self, backup_path: Path | str) -> bool:
        backup_file = Path(backup_path)
        if not backup_file.exists():
            logger.error("Restore falhou: backup não encontrado (%s)", backup_file)
            return False

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        pre_restore_backup = self.create_backup(reason="pre_restore")
        shutil.copy2(backup_file, self.db_path)
        try:
            self._validate_database()
            logger.info("Backup restaurado com sucesso: %s", backup_file)
            return True
        except Exception as exc:  # pragma: no cover
            logger.error("Restore inválido, revertendo: %s", exc)
            if pre_restore_backup and pre_restore_backup.exists():
                shutil.copy2(pre_restore_backup, self.db_path)
            return False

    def list_backups(self) -> list[Path]:
        if not self.backup_dir.exists():
            return []
        return sorted(self.backup_dir.glob("productions_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)

    def _rotate_backups(self) -> None:
        backups = self.list_backups()
        for stale in backups[self.max_backups :]:
            try:
                stale.unlink()
            except OSError as exc:  # pragma: no cover
                logger.warning("Falha ao remover backup antigo %s: %s", stale, exc)

    def _validate_database(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA integrity_check")
            integrity = cursor.fetchone()
            if not integrity or integrity[0] != "ok":
                raise RuntimeError(f"integrity_check falhou: {integrity}")

            cursor.execute("PRAGMA foreign_key_check")
            fk_issues = cursor.fetchall()
            if fk_issues:
                raise RuntimeError(f"foreign_key_check falhou: {fk_issues}")

    def _metadata_table_exists(self) -> bool:
        if not self.db_path.exists():
            return False

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='configuracoes' LIMIT 1")
            return cursor.fetchone() is not None

    def _get_metadata_value(self, key: str) -> str | None:
        if not self._metadata_table_exists():
            return None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT valor FROM configuracoes WHERE chave = ?", (key,))
            row = cursor.fetchone()
            return str(row[0]) if row else None

    def _set_metadata_value(self, key: str, value: str) -> None:
        if not self._metadata_table_exists():
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO configuracoes (chave, valor, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(chave) DO UPDATE SET
                    valor = excluded.valor,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, value),
            )
            conn.commit()
