from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.domain.models import FinancialPeriod, ProductionFilters
from src.presentation.qt.dialogs.financial_summary import FinancialSummaryDialog
from src.presentation.qt.dialogs.financial_summary_metrics import compute_dashboard_metrics
from src.presentation.qt.dialogs.financial_summary_support import (
    build_month_options,
    map_periods_to_dashboard_rows,
    recent_dashboard_rows,
)
from src.presentation.qt.viewmodels import FinancialDashboardState


class _FakeFinancialSummaryViewModel:
    def __init__(self, periods: list[FinancialPeriod]) -> None:
        self._periods = periods

    def load_initial_state(self) -> FinancialDashboardState:
        return FinancialDashboardState(
            clientes_list=["Cliente A"],
            tipos_producao=["Formatura"],
            anos_disponiveis=[2025, 2026],
        )

    def load_periods(self, filters: ProductionFilters) -> list[FinancialPeriod]:
        return list(self._periods)


class TestFinancialSummarySupport(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_map_rows_metrics_and_recent_order(self) -> None:
        periods = [
            FinancialPeriod(ano=2026, mes=1, data="2026-01-01", valor_total=100.0, quantidade=2),
            FinancialPeriod(ano=2026, mes=2, data="2026-02-01", valor_total=250.0, quantidade=5),
            FinancialPeriod(ano=2025, mes=12, data="2025-12-01", valor_total=50.0, quantidade=1),
        ]

        rows = map_periods_to_dashboard_rows(periods)
        metrics = compute_dashboard_metrics(rows)
        recent = recent_dashboard_rows(rows, limit=2)

        self.assertEqual(rows[0].ano, 2026)
        self.assertEqual(metrics.quantidade_total, 8)
        self.assertEqual(metrics.valor_total_fmt, "R$ 400,00")
        self.assertEqual([row.data for row in recent], ["2026-02-01", "2026-01-01"])
        self.assertEqual(len(build_month_options()), 12)

    def test_dialog_handles_empty_rows_without_crashing(self) -> None:
        dialog = FinancialSummaryDialog(view_model=_FakeFinancialSummaryViewModel([]))

        self.assertEqual(dialog.dados_financeiros, [])
        self.assertEqual(dialog.details_layout.count(), 1)


if __name__ == "__main__":
    unittest.main()
