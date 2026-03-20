from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.domain.models import ProductionFilters, ProductionPage, ProductionPayload
from src.infrastructure.sqlite.backend import SqliteBackendAdapter
from src.infrastructure.sqlite.backup import SqliteBackupService
from src.infrastructure.sqlite.orm import create_all_tables


class TestDatabasePagination(unittest.TestCase):
    @staticmethod
    def _dispose_adapter(db: SqliteBackendAdapter) -> None:
        bind = getattr(db._sessions.Session, "kw", {}).get("bind")
        if bind is not None:
            bind.dispose()

    def _make_adapter(self, db_path: Path) -> SqliteBackendAdapter:
        engine = create_all_tables(db_path)
        engine.dispose()
        return SqliteBackendAdapter(db_path=db_path, backup_dir=db_path.parent / "backups")

    def _seed_data(self, db: SqliteBackendAdapter, total: int = 120) -> None:
        for i in range(total):
            cliente = f"Cliente {i % 4}"
            status_pagamento = "Pago" if i % 2 == 0 else "Em aberto"
            tipo = "Formatura" if i % 3 == 0 else "Casamento"
            mes = (i % 12) + 1
            dia = (i % 28) + 1
            db.create(
                ProductionPayload(
                    cliente=cliente,
                    nome=f"Produção {i}",
                    tipo_producao=tipo,
                    data_recebimento=f"2026-{mes:02d}-{dia:02d}",
                    data_conclusao=f"2026-{mes:02d}-{min(dia + 1, 28):02d}",
                    status="Parado",
                    status_pagamento=status_pagamento,
                    quantidade_alunos=10,
                    quantidade_fotos=20,
                    quantidade_kits=1,
                    quantidade_capas=1,
                    valor_por_foto=2.0,
                    valor_por_kit=10.0,
                    valor_por_capa=15.0,
                )
            )

    def test_listar_producoes_paginado_returns_typed_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "pagination.db"
            db = self._make_adapter(db_path)
            self._seed_data(db, total=120)

            page = db.list_page(ProductionFilters(), page=1, page_size=25)
            self.assertIsInstance(page, ProductionPage)
            self.assertEqual(page.total, 120)
            self.assertEqual(page.page, 1)
            self.assertEqual(page.page_size, 25)
            self.assertEqual(len(page.items), 25)
            self.assertGreaterEqual(page.total_pages, 5)
            self.assertTrue(all(item.codigo for item in page.items))
            self._dispose_adapter(db)

    def test_listar_producoes_paginado_applies_filters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "filters.db"
            db = self._make_adapter(db_path)
            self._seed_data(db, total=100)

            page = db.list_page(
                ProductionFilters(cliente="Cliente 1", status_pagamento="Em aberto"),
                page=1,
                page_size=50,
            )

            self.assertGreater(page.total, 0)
            self.assertLessEqual(len(page.items), 50)
            for item in page.items:
                self.assertEqual(item.cliente, "Cliente 1")
                self.assertEqual(item.status_pagamento, "Em aberto")
            self._dispose_adapter(db)

    def test_create_normalizes_status_and_generates_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "create_dto.db"
            db = self._make_adapter(db_path)
            try:
                result = db.create(
                    ProductionPayload(
                        cliente="Cliente DTO",
                        nome="Produção DTO",
                        tipo_producao="Formatura",
                        data_recebimento="2026-01-10",
                        data_conclusao=None,
                        status="finalizado",
                        status_pagamento="pago",
                        quantidade_alunos=5,
                        quantidade_fotos=10,
                        quantidade_kits=1,
                        quantidade_capas=0,
                        valor_por_foto=1.0,
                        valor_por_kit=10.0,
                        valor_por_capa=0.0,
                    )
                )

                self.assertIsNotNone(result)
                self.assertEqual(result.cliente, "Cliente DTO")
                self.assertEqual(result.nome, "Produção DTO")
                self.assertEqual(result.status, "Finalizado")
                self.assertEqual(result.status_pagamento, "Em aberto")
                self.assertTrue(result.codigo.startswith("FORM-2026-"))
            finally:
                self._dispose_adapter(db)

    def test_financial_queries_and_backup_restore(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = tmp_path / "finance.db"
            backup_dir = tmp_path / "backups"
            db = self._make_adapter(db_path)

            created = db.create(
                ProductionPayload(
                    cliente="Cliente Financeiro",
                    nome="Produção Financeira",
                    tipo_producao="Formatura",
                    data_recebimento="2026-03-10",
                    data_conclusao="2026-03-12",
                    status="Parado",
                    status_pagamento="Em aberto",
                    quantidade_alunos=5,
                    quantidade_fotos=10,
                    quantidade_kits=2,
                    quantidade_capas=1,
                    valor_por_foto=2.0,
                    valor_por_kit=30.0,
                    valor_por_capa=40.0,
                )
            )

            summary = db.get_financial_summary(ano=2026, cliente="Cliente Financeiro")
            periods = db.get_financial_periods(ProductionFilters(cliente="Cliente Financeiro", ano=2026))
            self.assertEqual(summary.quantidade, 1)
            self.assertGreater(summary.total, 0.0)
            self.assertEqual(len(periods), 1)

            backup_service = SqliteBackupService(db_path=db_path, backup_dir=backup_dir)
            backup_path = backup_service.create_backup()
            self.assertIsNotNone(backup_path)

            db.delete_many([created.id])
            self._dispose_adapter(db)

            restored = backup_service.restore_backup(backup_path)
            self.assertTrue(restored)

            restored_db = SqliteBackendAdapter(db_path=db_path, backup_dir=backup_dir)
            restored_page = restored_db.list_page(ProductionFilters(cliente="Cliente Financeiro"), page=1, page_size=10)
            self.assertEqual(restored_page.total, 1)
            self._dispose_adapter(restored_db)


if __name__ == "__main__":
    unittest.main()
