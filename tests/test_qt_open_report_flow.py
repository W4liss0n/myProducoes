from __future__ import annotations

import os
import unittest
from datetime import date
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QMessageBox

from src.domain.models import Production
from src.presentation.qt.dialogs.relatorio_aberto_dialog import RelatorioAbertoDialog


class _FakeOpenReportViewModel:
    def __init__(self, productions: list[Production]) -> None:
        self._productions = productions

    def list_clients(self) -> list[str]:
        return ["Cliente A"]

    def list_open_by_client(self, cliente: str) -> list[Production]:
        return list(self._productions) if cliente == "Cliente A" else []


def _build_production(production_id: int, nome: str) -> Production:
    return Production(
        id=production_id,
        codigo=f"FORM-2026-{production_id:03d}",
        cliente="Cliente A",
        data_recebimento=date(2026, 3, 1),
        nome=nome,
        tipo_producao="Formatura",
        quantidade_alunos=10,
        quantidade_fotos=20,
        quantidade_kits=1,
        quantidade_capas=0,
        valor_por_foto=2.0,
        valor_por_kit=10.0,
        valor_por_capa=0.0,
        valor_total=50.0,
        data_conclusao=date(2026, 3, 15),
        status_pagamento="Em aberto",
        status="Parado",
        relatorio="",
        pasta_producao="C:/tmp",
    )


class TestQtOpenReportFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_warns_when_client_is_not_selected(self) -> None:
        dialog = RelatorioAbertoDialog(view_model=_FakeOpenReportViewModel([]))

        with patch.object(QMessageBox, "warning") as warning:
            dialog._generate_pdf()

        warning.assert_called_once()

    def test_warns_when_no_production_is_selected(self) -> None:
        dialog = RelatorioAbertoDialog(view_model=_FakeOpenReportViewModel([_build_production(1, "Produção 1")]))
        dialog.combo_cliente.setCurrentText("Cliente A")
        for checkbox in dialog.checkboxes.values():
            checkbox.setChecked(False)

        with patch.object(QMessageBox, "warning") as warning:
            dialog._generate_pdf()

        warning.assert_called_once()

    def test_calls_callback_with_selected_ids(self) -> None:
        captured: list[tuple[str, list[int]]] = []
        dialog = RelatorioAbertoDialog(
            view_model=_FakeOpenReportViewModel(
                [_build_production(1, "Produção 1"), _build_production(2, "Produção 2")]
            ),
            on_generate=lambda cliente, ids: captured.append((cliente, ids)),
        )
        dialog.combo_cliente.setCurrentText("Cliente A")
        dialog.checkboxes[2].setChecked(False)

        dialog._generate_pdf()

        self.assertEqual(captured, [("Cliente A", [1])])


if __name__ == "__main__":
    unittest.main()
