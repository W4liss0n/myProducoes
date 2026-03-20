from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Any


def _bootstrap_project_root() -> Path:
    root_dir = Path(__file__).resolve().parent.parent
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
    return root_dir


ROOT_DIR = _bootstrap_project_root()

from src.config.constants import DATABASE_FILE  # noqa: E402

logger = logging.getLogger(__name__)

REQUIRED_PRODUCOES_INDEXES = {
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


def _get_db_path(db_path_arg: str | None) -> Path:
    return Path(db_path_arg or DATABASE_FILE)


def _fetch_report(db_path: Path) -> dict[str, Any]:
    report: dict[str, Any] = {
        "database": str(db_path),
        "exists": db_path.exists(),
    }
    if not db_path.exists():
        return report

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        report["tables"] = sorted(tables)

        report["has_alembic_version"] = "alembic_version" in tables
        if report["has_alembic_version"]:
            cursor.execute("SELECT version_num FROM alembic_version")
            report["alembic_versions"] = [row[0] for row in cursor.fetchall()]
        else:
            report["alembic_versions"] = []

        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()
        report["integrity_check"] = integrity[0] if integrity else None

        cursor.execute("PRAGMA foreign_key_check")
        fk_issues = cursor.fetchall()
        report["foreign_key_check_count"] = len(fk_issues)
        report["foreign_key_check_issues"] = [list(row) for row in fk_issues]

        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='producoes'")
        producoes_indexes = {row[0] for row in cursor.fetchall()}
        report["producoes_indexes"] = sorted(producoes_indexes)
        report["missing_required_producoes_indexes"] = sorted(REQUIRED_PRODUCOES_INDEXES - producoes_indexes)

        duplicates: dict[str, list[dict[str, Any]]] = {}
        for table_name in ("status_pagamento", "status_producao"):
            cursor.execute(
                f"""
                SELECT lower(trim(nome)) AS normalized_name, COUNT(*) AS total
                FROM {table_name}
                GROUP BY normalized_name
                HAVING COUNT(*) > 1
                """
            )
            duplicates[table_name] = [
                {"normalized_name": str(row[0]), "count": int(row[1])}
                for row in cursor.fetchall()
            ]
        report["status_case_insensitive_duplicates"] = duplicates

    return report


def _is_postcheck_ok(report: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if not report.get("exists"):
        errors.append("Banco não encontrado.")
        return False, errors

    if report.get("integrity_check") != "ok":
        errors.append(f"integrity_check inválido: {report.get('integrity_check')}")

    if int(report.get("foreign_key_check_count", 0)) != 0:
        errors.append(f"foreign_key_check com inconsistências: {report.get('foreign_key_check_count')}")

    if not report.get("has_alembic_version"):
        errors.append("Tabela alembic_version ausente.")

    missing_indexes = report.get("missing_required_producoes_indexes") or []
    if missing_indexes:
        errors.append(f"Índices obrigatórios ausentes em producoes: {', '.join(missing_indexes)}")

    duplicates = report.get("status_case_insensitive_duplicates") or {}
    for table_name, rows in duplicates.items():
        if rows:
            errors.append(f"Duplicidades case-insensitive em {table_name}: {rows}")

    return not errors, errors


def cmd_preflight(args: argparse.Namespace) -> int:
    report = _fetch_report(_get_db_path(args.db))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def cmd_migrate(args: argparse.Namespace) -> int:
    from src.infrastructure.sqlite.bootstrap import SqliteDatabaseBootstrap

    db_path = _get_db_path(args.db)
    logger.info("Iniciando migração para %s", db_path)
    bootstrap = SqliteDatabaseBootstrap(db_path=db_path)
    bootstrap.ensure_ready()
    logger.info("Migração concluída para %s", db_path)
    return 0


def cmd_postcheck(args: argparse.Namespace) -> int:
    report = _fetch_report(_get_db_path(args.db))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    ok, errors = _is_postcheck_ok(report)
    if ok:
        return 0
    for err in errors:
        logger.error(err)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ferramenta de manutenção e validação do banco SQLite.")
    parser.add_argument("--db", help="Caminho opcional para o banco SQLite.")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Nível de log.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("preflight", help="Coleta diagnóstico do banco.")
    subparsers.add_parser("migrate", help="Executa bootstrap/migrações do banco.")
    subparsers.add_parser("postcheck", help="Valida integridade e consistência após migração.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s - %(message)s")

    if args.command == "preflight":
        return cmd_preflight(args)
    if args.command == "migrate":
        return cmd_migrate(args)
    if args.command == "postcheck":
        return cmd_postcheck(args)

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
