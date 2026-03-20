from __future__ import annotations

import os
import unittest
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.config.constants import DEFAULT_VISIBLE_COLUMNS
from src.domain.models import OperationResult, PixSettings, Production
from src.presentation.qt.main_window import MainWindow
from src.presentation.qt.viewmodels import MainWindowState


def _build_production() -> Production:
    return Production(
        id=42,
        codigo="FORM-2026-042",
        cliente="Cliente A",
        data_recebimento=date(2026, 3, 1),
        nome="Produção Janela",
        tipo_producao="Formatura",
        quantidade_alunos=20,
        quantidade_fotos=80,
        quantidade_kits=2,
        quantidade_capas=1,
        valor_por_foto=2.0,
        valor_por_kit=10.0,
        valor_por_capa=20.0,
        valor_total=200.0,
        data_conclusao=date(2026, 3, 15),
        status_pagamento="Em aberto",
        status="Parado",
        relatorio="",
        pasta_producao="C:/tmp",
    )


class _FakeMainWindowViewModel:
    def __init__(self) -> None:
        self.production = _build_production()
        self.load_page_calls = 0
        self.saved_visible_columns: list[str] = []
        self.state = MainWindowState(
            producoes=[self.production],
            tipos_producao=["Formatura"],
            clientes_list=["Cliente A"],
            anos_disponiveis=[2026],
            visible_columns=DEFAULT_VISIBLE_COLUMNS.copy(),
            current_page=1,
            page_size=50,
            total_items=1,
            total_pages=1,
        )

    def load_initial_state(self) -> MainWindowState:
        return self.state

    def load_page(self) -> MainWindowState:
        self.load_page_calls += 1
        return self.state

    def set_filters(self, filters) -> MainWindowState:
        self.state.active_filters = filters
        return self.state

    def clear_filters(self) -> MainWindowState:
        return self.state

    def set_page_size(self, page_size: int) -> MainWindowState:
        self.state.page_size = page_size
        return self.state

    def next_page(self) -> MainWindowState:
        return self.state

    def previous_page(self) -> MainWindowState:
        return self.state

    def get_production(self, production_id: int) -> Production | None:
        return self.production if production_id == self.production.id else None

    def delete(self, production_ids: list[int]) -> OperationResult[int]:
        return OperationResult(success=True, data=len(production_ids))

    def add_type(self, nome: str) -> OperationResult[bool]:
        return OperationResult(success=True, data=True)

    def remove_type(self, nome: str) -> OperationResult[bool]:
        return OperationResult(success=True, data=True)

    def create_manual_backup(self) -> OperationResult[bool]:
        return OperationResult(success=True, data=True, output_path=Path("backup.db"))

    def save_visible_columns(self, columns: list[str]) -> None:
        self.saved_visible_columns = list(columns)


class _FakeCoordinator:
    def __init__(self) -> None:
        self.edit_calls: list[int] = []
        self.add_calls = 0
        self.client_calls = 0

    def open_add_production(self, parent, tipos_producao: list[str], clientes_list: list[str]) -> bool:
        self.add_calls += 1
        return True

    def open_edit_production(
        self,
        parent,
        production_id: int,
        tipos_producao: list[str],
        clientes_list: list[str],
    ) -> bool:
        self.edit_calls.append(production_id)
        return False

    def open_open_report_dialog(self, parent) -> bool:
        return False

    def open_financial_summary(self, parent) -> None:
        return None

    def open_clients_dialog(self, parent) -> bool:
        self.client_calls += 1
        return True

    def load_pix_settings(self) -> PixSettings:
        return PixSettings()

    def save_pix_settings(self, config: dict[str, str]) -> None:
        return None


class TestMainWindowFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_edit_selected_production_uses_selected_row_id(self) -> None:
        view_model = _FakeMainWindowViewModel()
        coordinator = _FakeCoordinator()
        window = MainWindow(view_model=view_model, coordinator=coordinator)
        window.show()
        self.app.processEvents()
        window.table.selectRow(0)

        window._edit_selected_production()

        self.assertEqual(coordinator.edit_calls, [42])
        window.close()

    def test_add_production_reloads_state_when_coordinator_reports_change(self) -> None:
        view_model = _FakeMainWindowViewModel()
        coordinator = _FakeCoordinator()
        window = MainWindow(view_model=view_model, coordinator=coordinator)

        window._add_production()

        self.assertEqual(coordinator.add_calls, 1)
        self.assertEqual(view_model.load_page_calls, 1)
        window.close()

    def test_open_clients_overview_reloads_state_when_dialog_reports_change(self) -> None:
        view_model = _FakeMainWindowViewModel()
        coordinator = _FakeCoordinator()
        window = MainWindow(view_model=view_model, coordinator=coordinator)

        window._open_clients_overview()

        self.assertEqual(coordinator.client_calls, 1)
        self.assertEqual(view_model.load_page_calls, 1)
        window.close()


if __name__ == "__main__":
    unittest.main()
