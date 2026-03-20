from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.presentation.qt.dialogs.production_form import ProductionFormDialog
from src.presentation.qt.types import ProductionFormData


class _FakeFormViewModel:
    def inspect_folder(self, folder_path: str):  # pragma: no cover - not used here
        raise NotImplementedError

    def generate_report(self, **kwargs):  # pragma: no cover - not used here
        raise NotImplementedError


class TestQtFormFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_production_form_dialog_saves_typed_form_data(self) -> None:
        saved: list[ProductionFormData] = []
        dialog = ProductionFormDialog(
            view_model=_FakeFormViewModel(),
            mode="add",
            tipos_producao=["Formatura", "Casamento"],
            clientes_list=["Cliente A"],
            on_save=lambda form_data: saved.append(form_data),
        )
        self.assertFalse(dialog.widgets["status_pagamento"].isEnabled())

        dialog.widgets["cliente"].setText("Cliente A")
        dialog.widgets["nome"].setText("Produção A")
        dialog.widgets["tipo_producao"].setCurrentText("Formatura")
        dialog.widgets["quantidade_alunos"].setText("12")
        dialog.widgets["quantidade_fotos"].setText("80")
        dialog.widgets["quantidade_kits"].setText("2")
        dialog.widgets["quantidade_capas"].setText("1")
        dialog.widgets["valor_por_foto"].setValue(2.5)
        dialog.widgets["valor_por_kit"].setValue(30.0)
        dialog.widgets["valor_por_capa"].setValue(40.0)

        dialog._on_save()

        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].cliente, "Cliente A")
        self.assertEqual(saved[0].tipo_producao, "Formatura")
        self.assertEqual(saved[0].quantidade_fotos, 80)


if __name__ == "__main__":
    unittest.main()
