from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QApplication, QComboBox, QDateEdit, QLineEdit

from src.domain.models import FolderInspection
from src.presentation.qt.dialogs.production_form_support import ProductionFormFields, ProductionFormValidator
from src.presentation.qt.types import ProductionFormData
from src.presentation.qt.widgets import AutocompleteLineEdit, MoneyLineEdit


class TestProductionFormSupport(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.validator = ProductionFormValidator()
        self.fields = self._build_fields()

    def _build_fields(self) -> ProductionFormFields:
        tipo = QComboBox()
        tipo.addItems(["Formatura", "Casamento"])
        status = QComboBox()
        status.addItems(["Parado", "Em Andamento", "Finalizado"])
        status_pagamento = QComboBox()
        status_pagamento.addItems(["Em aberto", "Parcial", "Pago"])
        data_recebimento = QDateEdit()
        data_conclusao = QDateEdit()
        return ProductionFormFields(
            cliente=AutocompleteLineEdit(["Cliente A", "Cliente B"]),
            nome=QLineEdit(),
            tipo_producao=tipo,
            data_recebimento=data_recebimento,
            data_conclusao=data_conclusao,
            status=status,
            status_pagamento=status_pagamento,
            quantidade_alunos=QLineEdit(),
            quantidade_fotos=QLineEdit(),
            quantidade_kits=QLineEdit(),
            quantidade_capas=QLineEdit(),
            valor_por_foto=MoneyLineEdit(),
            valor_por_kit=MoneyLineEdit(),
            valor_por_capa=MoneyLineEdit(),
        )

    def test_populate_hydrates_widgets_from_form_data(self) -> None:
        data = ProductionFormData(
            cliente="Cliente A",
            nome="Produção Teste",
            tipo_producao="Formatura",
            data_recebimento="2026-03-10",
            data_conclusao="2026-03-20",
            status="Em Andamento",
            status_pagamento="Pago",
            quantidade_alunos=12,
            quantidade_fotos=80,
            quantidade_kits=4,
            quantidade_capas=2,
            valor_por_foto=2.5,
            valor_por_kit=30.0,
            valor_por_capa=40.0,
        )

        self.validator.populate(self.fields, data)

        self.assertEqual(self.fields.cliente.text(), "Cliente A")
        self.assertEqual(self.fields.nome.text(), "Produção Teste")
        self.assertEqual(self.fields.tipo_producao.currentText(), "Formatura")
        self.assertEqual(self.fields.data_recebimento.date().toString("yyyy-MM-dd"), "2026-03-10")
        self.assertEqual(self.fields.status.currentText(), "Em Andamento")
        self.assertEqual(self.fields.quantidade_fotos.text(), "80")
        self.assertAlmostEqual(self.fields.valor_por_kit.value(), 30.0)

    def test_collect_and_validate_required_fields(self) -> None:
        self.fields.cliente.setText("Cliente B")
        self.fields.nome.setText("Produção B")
        self.fields.tipo_producao.setCurrentText("Casamento")
        self.fields.data_recebimento.setDate(QDate(2026, 4, 1))
        self.fields.data_conclusao.setDate(QDate(2026, 4, 5))
        self.fields.status.setCurrentText("Parado")
        self.fields.status_pagamento.setCurrentText("Em aberto")
        self.fields.quantidade_alunos.setText("10")
        self.fields.quantidade_fotos.setText("25")
        self.fields.quantidade_kits.setText("2")
        self.fields.quantidade_capas.setText("1")
        self.fields.valor_por_foto.setValue(1.5)
        self.fields.valor_por_kit.setValue(20.0)
        self.fields.valor_por_capa.setValue(30.0)

        data = self.validator.collect(
            self.fields,
            initial_data=ProductionFormData(codigo="FORM-2026-001", relatorio="ok"),
            pasta_producao="C:/tmp/producao-b",
        )

        self.assertIsNone(self.validator.validate_required(data))
        self.assertEqual(data.codigo, "FORM-2026-001")
        self.assertEqual(data.pasta_producao, "C:/tmp/producao-b")
        self.assertEqual(data.quantidade_fotos, 25)
        self.assertAlmostEqual(data.valor_por_capa, 30.0)

    def test_apply_folder_helpers_and_total(self) -> None:
        self.validator.apply_folder_name(self.fields, "Pasta Teste")
        self.validator.apply_folder_inspection(
            self.fields,
            FolderInspection(total_fotos=120, total_alunos=30, total_kits=5),
        )
        self.fields.quantidade_capas.setText("2")
        self.fields.valor_por_foto.setValue(2.0)
        self.fields.valor_por_kit.setValue(10.0)
        self.fields.valor_por_capa.setValue(15.0)

        total = self.validator.calculate_total(self.fields)

        self.assertEqual(self.fields.nome.text(), "Pasta Teste")
        self.assertEqual(self.fields.quantidade_alunos.text(), "30")
        self.assertEqual(self.fields.quantidade_fotos.text(), "120")
        self.assertAlmostEqual(total, 120 * 2.0 + 5 * 10.0 + 2 * 15.0)

    def test_validate_required_returns_message_for_missing_name(self) -> None:
        message = self.validator.validate_required(ProductionFormData(cliente="Cliente A"))

        self.assertEqual(message, "O campo Nome é obrigatório!")


if __name__ == "__main__":
    unittest.main()
