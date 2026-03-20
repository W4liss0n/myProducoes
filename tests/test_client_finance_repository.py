from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.domain.models import ProductionFilters, ProductionPayload, ReceiptAllocationRequest
from src.infrastructure.sqlite.backend import SqliteBackendAdapter
from src.infrastructure.sqlite.orm import create_all_tables


class TestClientFinanceRepository(unittest.TestCase):
    @staticmethod
    def _dispose_adapter(db: SqliteBackendAdapter) -> None:
        bind = getattr(db._sessions.Session, "kw", {}).get("bind")
        if bind is not None:
            bind.dispose()

    def _make_adapter(self, db_path: Path) -> SqliteBackendAdapter:
        engine = create_all_tables(db_path)
        engine.dispose()
        return SqliteBackendAdapter(db_path=db_path, backup_dir=db_path.parent / "backups")

    @staticmethod
    def _payload(*, cliente: str, nome: str, data_recebimento: str, valor_total: float) -> ProductionPayload:
        return ProductionPayload(
            cliente=cliente,
            nome=nome,
            tipo_producao="Formatura",
            data_recebimento=data_recebimento,
            data_conclusao=None,
            status="Parado",
            status_pagamento="Em aberto",
            quantidade_alunos=1,
            quantidade_fotos=1,
            quantidade_kits=0,
            quantidade_capas=0,
            valor_por_foto=valor_total,
            valor_por_kit=0.0,
            valor_por_capa=0.0,
        )

    @staticmethod
    def _client_id(db: SqliteBackendAdapter, cliente: str) -> int:
        summary = next(item for item in db.list_client_summaries() if item.cliente == cliente)
        return summary.client_id

    def test_partial_and_total_payment_update_projection_and_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = self._make_adapter(Path(tmp) / "partial.db")
            try:
                production = db.create(
                    self._payload(
                        cliente="Cliente Parcial",
                        nome="Produção Parcial",
                        data_recebimento="2026-01-10",
                        valor_total=100.0,
                    )
                )
                client_id = self._client_id(db, "Cliente Parcial")

                db.register_client_receipt(
                    client_id=client_id,
                    data_recebimento="2026-01-15",
                    valor_total=30.0,
                    forma_pagamento="PIX",
                    observacao="Entrada",
                    auto_allocate=True,
                    allocations=[],
                )

                parcial = db.get_by_id(production.id)
                page = db.list_page(ProductionFilters(status_pagamento="Parcial"), page=1, page_size=10)
                self.assertEqual(parcial.status_pagamento, "Parcial")
                self.assertAlmostEqual(parcial.valor_recebido, 30.0)
                self.assertAlmostEqual(parcial.saldo, 70.0)
                self.assertEqual([item.id for item in page.items], [production.id])

                db.register_client_receipt(
                    client_id=client_id,
                    data_recebimento="2026-01-20",
                    valor_total=70.0,
                    forma_pagamento="PIX",
                    observacao="Quitação",
                    auto_allocate=True,
                    allocations=[],
                )

                paid = db.get_by_id(production.id)
                self.assertEqual(paid.status_pagamento, "Pago")
                self.assertAlmostEqual(paid.valor_recebido, 100.0)
                self.assertAlmostEqual(paid.saldo, 0.0)
            finally:
                self._dispose_adapter(db)

    def test_fifo_allocation_and_credit_are_reflected_in_client_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = self._make_adapter(Path(tmp) / "fifo.db")
            try:
                first = db.create(
                    self._payload(
                        cliente="Cliente FIFO",
                        nome="Produção 1",
                        data_recebimento="2026-01-10",
                        valor_total=60.0,
                    )
                )
                second = db.create(
                    self._payload(
                        cliente="Cliente FIFO",
                        nome="Produção 2",
                        data_recebimento="2026-02-10",
                        valor_total=50.0,
                    )
                )
                client_id = self._client_id(db, "Cliente FIFO")

                receipt = db.register_client_receipt(
                    client_id=client_id,
                    data_recebimento="2026-02-15",
                    valor_total=130.0,
                    forma_pagamento="Transferência",
                    observacao="Pagamento geral",
                    auto_allocate=True,
                    allocations=[],
                )
                detail = db.get_client_detail(client_id)

                self.assertEqual(
                    [(allocation.production_id, allocation.valor_alocado) for allocation in receipt.allocations],
                    [(first.id, 60.0), (second.id, 50.0)],
                )
                self.assertAlmostEqual(receipt.valor_nao_alocado, 20.0)
                self.assertAlmostEqual(detail.summary.credito, 20.0)
                self.assertAlmostEqual(detail.summary.valor_recebido, 110.0)
                self.assertTrue(all(item.status_pagamento == "Pago" for item in detail.productions))
            finally:
                self._dispose_adapter(db)

    def test_manual_allocation_rejects_value_above_balance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = self._make_adapter(Path(tmp) / "manual.db")
            try:
                production = db.create(
                    self._payload(
                        cliente="Cliente Manual",
                        nome="Produção Manual",
                        data_recebimento="2026-03-01",
                        valor_total=40.0,
                    )
                )
                client_id = self._client_id(db, "Cliente Manual")

                with self.assertRaises(ValueError):
                    db.register_client_receipt(
                        client_id=client_id,
                        data_recebimento="2026-03-05",
                        valor_total=50.0,
                        forma_pagamento="PIX",
                        observacao="Erro",
                        auto_allocate=False,
                        allocations=[ReceiptAllocationRequest(production_id=production.id, valor_alocado=50.0)],
                    )
            finally:
                self._dispose_adapter(db)

    def test_update_production_rejects_client_change_and_total_below_received(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = self._make_adapter(Path(tmp) / "guards.db")
            try:
                production = db.create(
                    self._payload(
                        cliente="Cliente Original",
                        nome="Produção Guard",
                        data_recebimento="2026-04-01",
                        valor_total=80.0,
                    )
                )
                client_id = self._client_id(db, "Cliente Original")
                db.register_client_receipt(
                    client_id=client_id,
                    data_recebimento="2026-04-10",
                    valor_total=20.0,
                    forma_pagamento="PIX",
                    observacao="Entrada",
                    auto_allocate=True,
                    allocations=[],
                )

                with self.assertRaises(ValueError):
                    db.update(
                        production.id,
                        self._payload(
                            cliente="Cliente Novo",
                            nome="Produção Guard",
                            data_recebimento="2026-04-01",
                            valor_total=80.0,
                        ),
                    )

                with self.assertRaises(ValueError):
                    db.update(
                        production.id,
                        self._payload(
                            cliente="Cliente Original",
                            nome="Produção Guard",
                            data_recebimento="2026-04-01",
                            valor_total=10.0,
                        ),
                    )
            finally:
                self._dispose_adapter(db)
