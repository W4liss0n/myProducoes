from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import patch

from reportlab.lib.units import cm

from src.core.pdf.reports import _build_open_report_month_groups, _resolve_page_number_y
from src.domain.models import Production
from src.infrastructure.filesystem import gateways as filesystem_gateways
from src.infrastructure.filesystem.gateways import ReportLabReportGenerationGateway


class TestOpenReportMonthGroups(unittest.TestCase):
    def test_groups_reference_months_in_chronological_order(self) -> None:
        producoes: list[dict[str, Any]] = [
            {"Nome": "Fevereiro", "Data de Conclusão": "2026-02-15"},
            {"Nome": "Dezembro", "Data de Conclusão": "2025-12-20"},
            {"Nome": "Janeiro", "Data de Conclusão": date(2026, 1, 10)},
        ]

        grupos = _build_open_report_month_groups(producoes)

        self.assertEqual(
            [mes_ano for mes_ano, _ in grupos],
            ["Dezembro de 2025", "Janeiro de 2026", "Fevereiro de 2026"],
        )

    def test_groups_invalid_dates_at_the_end(self) -> None:
        producoes: list[dict[str, Any]] = [
            {"Nome": "Com data", "Data de Conclusão": "2026-01-10"},
            {"Nome": "Sem data", "Data de Conclusão": ""},
            {"Nome": "Data inválida", "Data de Conclusão": "31/31/2026"},
        ]

        grupos = _build_open_report_month_groups(producoes)

        self.assertEqual([mes_ano for mes_ano, _ in grupos], ["Janeiro de 2026", "Sem data definida"])
        self.assertEqual([item["Nome"] for item in grupos[-1][1]], ["Sem data", "Data inválida"])

    def test_page_number_stays_below_content_frame(self) -> None:
        open_report_bottom_margin = 1.2 * cm
        page_number_y = _resolve_page_number_y(open_report_bottom_margin)

        self.assertLess(page_number_y, open_report_bottom_margin)
        self.assertGreaterEqual(page_number_y, 0.6 * cm)


class TestOpenReportGateway(unittest.TestCase):
    @staticmethod
    def _build_production(
        production_id: int,
        *,
        status_pagamento: str,
        valor_total: float,
        valor_recebido: float = 0.0,
        saldo: float = 0.0,
    ) -> Production:
        return Production(
            id=production_id,
            codigo=f"FORM-2026-{production_id:03d}",
            cliente="Cliente A",
            data_recebimento=date(2026, 3, 1),
            nome=f"Produção {production_id}",
            tipo_producao="Formatura",
            quantidade_alunos=10,
            quantidade_fotos=20,
            quantidade_kits=1,
            quantidade_capas=0,
            valor_por_foto=2.0,
            valor_por_kit=10.0,
            valor_por_capa=0.0,
            valor_total=valor_total,
            data_conclusao=date(2026, 3, 15),
            status_pagamento=status_pagamento,
            status="Parado",
            relatorio="",
            pasta_producao="C:/tmp",
            valor_recebido=valor_recebido,
            saldo=saldo,
        )

    def test_generate_open_report_uses_remaining_balance_for_partial_productions(self) -> None:
        gateway = ReportLabReportGenerationGateway()
        producoes = [
            self._build_production(
                1,
                status_pagamento="Parcial",
                valor_total=100.0,
                valor_recebido=30.0,
                saldo=70.0,
            ),
            self._build_production(
                2,
                status_pagamento="Em aberto",
                valor_total=50.0,
            ),
        ]

        captured: dict[str, Any] = {}

        class _FakePDFGenerator:
            def gerar_relatorio_producoes_aberto(
                self,
                *,
                file_path: Path,
                cliente: str,
                producoes: list[dict[str, Any]],
            ) -> bool:
                captured["file_path"] = file_path
                captured["cliente"] = cliente
                captured["producoes"] = producoes
                return True

        with patch.object(filesystem_gateways, "PDFGenerator", _FakePDFGenerator):
            ok = gateway.generate_open_productions_report(
                output_path=Path("relatorio.pdf"),
                cliente="Cliente A",
                producoes=producoes,
            )

        self.assertTrue(ok)
        payload = captured["producoes"]
        self.assertEqual(payload[0]["Valor Total"], 70.0)
        self.assertEqual(payload[1]["Valor Total"], 50.0)


if __name__ == "__main__":
    unittest.main()
