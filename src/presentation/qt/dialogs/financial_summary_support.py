from __future__ import annotations

from typing import Sequence

from ....domain.models import FinancialPeriod
from ..types import FinancialDashboardRow

FULL_MONTH_NAMES = [
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
]

SHORT_MONTH_NAMES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def build_month_options() -> list[str]:
    return [f"{month:02d} - {name}" for month, name in enumerate(FULL_MONTH_NAMES, start=1)]


def map_periods_to_dashboard_rows(periodos: Sequence[FinancialPeriod]) -> list[FinancialDashboardRow]:
    return [
        FinancialDashboardRow(
            ano=periodo.ano,
            mes=periodo.mes,
            data=periodo.data,
            valor_total=periodo.valor_total,
            quantidade=periodo.quantidade,
        )
        for periodo in periodos
    ]


def recent_dashboard_rows(
    rows: Sequence[FinancialDashboardRow],
    *,
    limit: int = 10,
) -> list[FinancialDashboardRow]:
    return sorted(rows, key=lambda row: row.data, reverse=True)[:limit]
