from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from src.domain.models import ProductionPayload
from src.infrastructure.sqlite.collaborators import (
    ProductionCodeGenerator,
    ProductionTotalsCalculator,
    StatusCanonicalizer,
)


class TestSqliteCollaborators(unittest.TestCase):
    def test_status_canonicalizer_normalizes_case_insensitive_values(self) -> None:
        canonicalizer = StatusCanonicalizer()

        self.assertEqual(canonicalizer.production_status("finalizado"), "Finalizado")
        self.assertEqual(canonicalizer.payment_status("pago"), "Pago")

    def test_totals_calculator_returns_total_and_items(self) -> None:
        payload = ProductionPayload(
            cliente="Cliente",
            nome="Produção",
            tipo_producao="Formatura",
            data_recebimento="2026-01-10",
            data_conclusao=None,
            status="Parado",
            status_pagamento="Em aberto",
            quantidade_alunos=5,
            quantidade_fotos=10,
            quantidade_kits=2,
            quantidade_capas=1,
            valor_por_foto=2.5,
            valor_por_kit=15.0,
            valor_por_capa=20.0,
        )
        calculator = ProductionTotalsCalculator()

        total = calculator.calculate_total(payload)
        items = calculator.build_item_inputs(payload)

        self.assertEqual(total, Decimal("75.0"))
        self.assertEqual([item.tipo_item for item in items], ["FOTO", "KIT", "CAPA"])
        self.assertEqual(items[0].valor_total, Decimal("25.0"))

    def test_code_generator_uses_context_and_last_code(self) -> None:
        generator = ProductionCodeGenerator()

        context = generator.sequence_context("Formatura", date(2026, 1, 10))
        new_code = generator.build_code(context, "FORM-2026-009")

        self.assertEqual(context.like_pattern, "FORM-2026-%")
        self.assertEqual(new_code, "FORM-2026-010")


if __name__ == "__main__":
    unittest.main()
