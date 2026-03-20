from __future__ import annotations

import unittest
from datetime import date

from src.domain.models import Production
from src.presentation.qt.mappers import ProductionPresentationMapper
from src.presentation.qt.types import ProductionFormData


class TestProductionPresentationMapper(unittest.TestCase):
    def test_production_to_table_row_and_form_data(self) -> None:
        production = Production(
            id=10,
            codigo="FORM-2026-010",
            cliente="Cliente A",
            data_recebimento=date(2026, 3, 1),
            nome="Produção A",
            tipo_producao="Formatura",
            quantidade_alunos=30,
            quantidade_fotos=100,
            quantidade_kits=10,
            quantidade_capas=5,
            valor_por_foto=1.5,
            valor_por_kit=20.0,
            valor_por_capa=30.0,
            valor_total=500.0,
            data_conclusao=date(2026, 3, 10),
            status_pagamento="Em aberto",
            status="Parado",
            relatorio="",
            pasta_producao="C:/tmp/prod",
            valor_recebido=150.0,
            saldo=350.0,
        )

        row = ProductionPresentationMapper.production_to_table_row(production)
        self.assertEqual(row.production_id, 10)
        self.assertEqual(row.values["Cliente"], "Cliente A")
        self.assertEqual(row.values["Data de Recebimento"], "2026-03-01")
        self.assertEqual(row.values["Data de Conclusão"], "2026-03-10")
        self.assertEqual(row.values["Valor Total"], 500.0)

        form_data = ProductionPresentationMapper.production_to_form_data(production)
        self.assertEqual(form_data.codigo, "FORM-2026-010")
        self.assertEqual(form_data.status_pagamento, "Em aberto")
        self.assertEqual(form_data.valor_recebido, 150.0)
        self.assertEqual(form_data.saldo, 350.0)

    def test_form_to_payload_normalizes_numbers(self) -> None:
        payload = ProductionPresentationMapper.form_to_payload(
            ProductionFormData(
                cliente="Cliente B",
                nome="Produção B",
                tipo_producao="Casamento",
                data_recebimento="2026-02-15",
                data_conclusao="2026-03-01",
                status="Finalizado",
                status_pagamento="Pago",
                quantidade_alunos=12,
                quantidade_fotos=80,
                quantidade_kits=2,
                quantidade_capas=1,
                valor_por_foto=2.5,
                valor_por_kit=30,
                valor_por_capa=40,
                pasta_producao="C:/tmp/prod-b",
                relatorio="ok",
            )
        )

        self.assertEqual(payload.cliente, "Cliente B")
        self.assertEqual(payload.quantidade_fotos, 80)
        self.assertEqual(payload.valor_por_foto, 2.5)
        self.assertEqual(payload.pasta_producao, "C:/tmp/prod-b")
        self.assertEqual(payload.relatorio, "ok")


if __name__ == "__main__":
    unittest.main()
