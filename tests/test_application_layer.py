from __future__ import annotations

import unittest
from pathlib import Path

from src.application.commands import GenerateOpenReportInput
from src.application.use_cases import GenerateOpenReportCommand
from src.domain.models import Production, ProductionFilters, ProductionPage
from src.presentation.qt.viewmodels import MainWindowViewModel


class _FakeBackend:
    def __init__(self) -> None:
        self.items = [
            Production(
                id=1,
                codigo="FORM-2026-001",
                cliente="Cliente A",
                data_recebimento=None,
                nome="Produção A",
                tipo_producao="Formatura",
                quantidade_alunos=10,
                quantidade_fotos=20,
                quantidade_kits=2,
                quantidade_capas=1,
                valor_por_foto=1.5,
                valor_por_kit=10.0,
                valor_por_capa=20.0,
                valor_total=70.0,
                data_conclusao=None,
                status_pagamento="Em aberto",
                status="Parado",
                relatorio="",
                pasta_producao="",
            ),
            Production(
                id=2,
                codigo="FORM-2026-002",
                cliente="Cliente B",
                data_recebimento=None,
                nome="Produção B",
                tipo_producao="Casamento",
                quantidade_alunos=8,
                quantidade_fotos=10,
                quantidade_kits=1,
                quantidade_capas=0,
                valor_por_foto=2.0,
                valor_por_kit=15.0,
                valor_por_capa=0.0,
                valor_total=35.0,
                data_conclusao=None,
                status_pagamento="Pago",
                status="Finalizado",
                relatorio="",
                pasta_producao="",
            ),
        ]

    def list_page(self, filters: ProductionFilters, *, page: int, page_size: int) -> ProductionPage:
        filtered = self.list_all(filters)
        start = (page - 1) * page_size
        end = start + page_size
        return ProductionPage(items=filtered[start:end], total=len(filtered), page=page, page_size=page_size)

    def list_all(self, filters: ProductionFilters) -> list[Production]:
        items = list(self.items)
        if filters.cliente:
            items = [item for item in items if item.cliente == filters.cliente]
        return items

    def get_by_id(self, production_id: int) -> Production | None:
        return next((item for item in self.items if item.id == production_id), None)

    def create(self, payload):  # pragma: no cover - not used here
        raise NotImplementedError

    def update(self, production_id, payload):  # pragma: no cover - not used here
        raise NotImplementedError

    def delete_many(self, production_ids):  # pragma: no cover - not used here
        raise NotImplementedError

    def list_open_by_client(self, cliente: str) -> list[Production]:
        return [item for item in self.items if item.cliente == cliente and item.status_pagamento == "Em aberto"]

    def get_financial_periods(self, filters):  # pragma: no cover - not used here
        return []

    def get_financial_summary(self, *, ano=None, cliente=None):  # pragma: no cover - not used here
        raise NotImplementedError

    def list_tipos(self):
        return ["Formatura", "Casamento"]

    def add_tipo(self, nome):  # pragma: no cover - not used here
        return True

    def remove_tipo(self, nome):  # pragma: no cover - not used here
        return True

    def list_clientes(self):
        return ["Cliente A", "Cliente B"]

    def list_anos(self):
        return [2026]

    def create_manual_backup(self):  # pragma: no cover - not used here
        return None


class _FakeColumnsRepo:
    def load_visible_columns(self):
        return ["Cliente", "Nome"]

    def save_visible_columns(self, columns):
        self.columns = columns


class _FakeReportGateway:
    def __init__(self) -> None:
        self.calls = []

    def generate_open_productions_report(self, *, output_path: Path, cliente: str, producoes: list[Production]) -> bool:
        self.calls.append((output_path, cliente, [producao.id for producao in producoes]))
        return True


class TestApplicationLayer(unittest.TestCase):
    def test_main_window_view_model_applies_filters_and_visible_columns(self) -> None:
        backend = _FakeBackend()
        columns_repo = _FakeColumnsRepo()
        view_model = MainWindowViewModel(
            list_productions=lambda filters, page, page_size: backend.list_page(
                filters,
                page=page,
                page_size=page_size,
            ),
            get_production=backend.get_by_id,
            create_production=None,
            update_production=None,
            delete_productions=None,
            list_types=backend.list_tipos,
            add_type=backend.add_tipo,
            remove_type=backend.remove_tipo,
            list_clients=backend.list_clientes,
            list_years=backend.list_anos,
            create_manual_backup=backend.create_manual_backup,
            get_visible_columns=columns_repo.load_visible_columns,
            save_visible_columns=lambda command: columns_repo.save_visible_columns(command.columns),
        )

        state = view_model.load_initial_state()
        self.assertEqual(state.visible_columns, ["Cliente", "Nome"])

        state = view_model.set_filters(ProductionFilters(cliente="Cliente A"))
        self.assertEqual(len(state.producoes), 1)
        self.assertEqual(state.producoes[0].cliente, "Cliente A")

    def test_generate_open_report_command_respects_selected_ids(self) -> None:
        backend = _FakeBackend()
        report_gateway = _FakeReportGateway()
        command = GenerateOpenReportCommand(backend, report_gateway)

        result = command(
            GenerateOpenReportInput(
                cliente="Cliente A",
                output_path=Path("relatorio.pdf"),
                production_ids=[1],
            )
        )

        self.assertTrue(result.success)
        self.assertEqual(report_gateway.calls[0][2], [1])


if __name__ == "__main__":
    unittest.main()
