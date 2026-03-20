from __future__ import annotations

import os
import unittest
from datetime import date
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.domain.models import (
    ClientDetail,
    ClientReceipt,
    ClientSummary,
    OpenProductionBalance,
    OperationResult,
    Production,
    ReceiptAllocation,
    ReceiptAllocationRequest,
)
from src.presentation.qt.dialogs.clients_dialog import ClientsDialog
from src.presentation.qt.dialogs.register_receipt_dialog import RegisterReceiptDialog
from src.presentation.qt.viewmodels import ClientsOverviewState


def _build_production() -> Production:
    return Production(
        id=1,
        codigo="FORM-2026-001",
        cliente="Cliente A",
        data_recebimento=date(2026, 3, 1),
        nome="Produção A",
        tipo_producao="Formatura",
        quantidade_alunos=10,
        quantidade_fotos=20,
        quantidade_kits=1,
        quantidade_capas=0,
        valor_por_foto=2.0,
        valor_por_kit=10.0,
        valor_por_capa=0.0,
        valor_total=50.0,
        data_conclusao=date(2026, 3, 5),
        status_pagamento="Em aberto",
        status="Em Andamento",
        relatorio="",
        pasta_producao="C:/tmp",
        valor_recebido=20.0,
        saldo=30.0,
    )


def _build_client_detail() -> ClientDetail:
    summary = ClientSummary(
        client_id=10,
        cliente="Cliente A",
        total_productions=1,
        open_productions=1,
        in_progress_productions=1,
        valor_contratado=50.0,
        valor_recebido=20.0,
        saldo=30.0,
        credito=0.0,
    )
    receipt = ClientReceipt(
        id=7,
        client_id=10,
        cliente="Cliente A",
        data_recebimento=date(2026, 3, 7),
        valor_total=20.0,
        valor_nao_alocado=0.0,
        forma_pagamento="PIX",
        observacao="Entrada",
        origem="MANUAL",
    )
    balance = OpenProductionBalance(
        production_id=1,
        codigo="FORM-2026-001",
        nome="Produção A",
        data_recebimento=date(2026, 3, 1),
        valor_total=50.0,
        valor_recebido=20.0,
        saldo=30.0,
        status="Em Andamento",
        status_pagamento="Parcial",
    )
    return ClientDetail(summary=summary, productions=[_build_production()], open_balances=[balance], receipts=[receipt])


class _FakeClientsViewModel:
    def __init__(self) -> None:
        self.detail = _build_client_detail()
        self.load_detail_calls: list[int] = []
        self.register_calls: list[dict[str, object]] = []

    def load_initial_state(self) -> ClientsOverviewState:
        return ClientsOverviewState(clients=[self.detail.summary], selected_client=self.detail)

    def load_client_detail(self, client_id: int) -> ClientDetail | None:
        self.load_detail_calls.append(client_id)
        return self.detail

    def suggest_allocations(self, client_id: int, valor_total: float) -> list[ReceiptAllocation]:
        return [
            ReceiptAllocation(
                id=0,
                receipt_id=0,
                production_id=1,
                valor_alocado=min(valor_total, 30.0),
                production_name="Produção A",
                production_code="FORM-2026-001",
            )
        ]

    def register_receipt(
        self,
        *,
        client_id: int,
        data_recebimento: str | None,
        valor_total: float,
        forma_pagamento: str,
        observacao: str,
        auto_allocate: bool,
        allocations: list[ReceiptAllocationRequest],
    ) -> OperationResult[ClientReceipt]:
        self.register_calls.append(
            {
                "client_id": client_id,
                "data_recebimento": data_recebimento,
                "valor_total": valor_total,
                "forma_pagamento": forma_pagamento,
                "observacao": observacao,
                "auto_allocate": auto_allocate,
                "allocations": allocations,
            }
        )
        return OperationResult(success=True, data=self.detail.receipts[0])

    @staticmethod
    def format_money(value: float) -> str:
        return f"R$ {float(value):.2f}"


class TestClientsDialogFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_register_receipt_dialog_submits_automatic_flow(self) -> None:
        view_model = _FakeClientsViewModel()
        dialog = RegisterReceiptDialog(view_model=view_model, client_detail=view_model.detail)
        dialog.value_input.setValue(25.0)

        with patch("src.presentation.qt.dialogs.register_receipt_dialog.QMessageBox.information"):
            dialog._save()

        self.assertTrue(dialog.saved)
        self.assertEqual(view_model.register_calls[0]["auto_allocate"], True)
        self.assertEqual(view_model.register_calls[0]["allocations"], [])

    def test_register_receipt_dialog_submits_manual_allocations(self) -> None:
        view_model = _FakeClientsViewModel()
        dialog = RegisterReceiptDialog(view_model=view_model, client_detail=view_model.detail)
        dialog.mode_input.setCurrentText("Manual")
        manual_input = dialog._allocation_inputs[1]
        manual_input.setValue(18.5)

        with patch("src.presentation.qt.dialogs.register_receipt_dialog.QMessageBox.information"):
            dialog._save()

        allocations = view_model.register_calls[0]["allocations"]
        self.assertEqual(view_model.register_calls[0]["auto_allocate"], False)
        self.assertEqual([(item.production_id, item.valor_alocado) for item in allocations], [(1, 18.5)])

    def test_clients_dialog_loads_summary_and_marks_change_after_payment(self) -> None:
        view_model = _FakeClientsViewModel()
        dialog = ClientsDialog(view_model=view_model)

        self.assertEqual(dialog.clients_table.rowCount(), 1)
        self.assertEqual(dialog.summary_labels["cliente"].text(), "Cliente A")

        with patch("src.presentation.qt.dialogs.clients_dialog.RegisterReceiptDialog") as dialog_cls:
            dialog_instance = dialog_cls.return_value
            dialog_instance.saved = True
            dialog_instance.exec.return_value = 1

            dialog._open_register_receipt_dialog()

        self.assertTrue(dialog.changed)
        self.assertGreaterEqual(view_model.load_detail_calls.count(10), 1)
