from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ..types import FinancialDashboardRow


def _fmt_currency(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@dataclass(slots=True, frozen=True)
class FinancialDashboardMetrics:
    valor_total: float
    quantidade_total: int
    ticket_medio: float
    crescimento_pct: float
    valor_total_fmt: str
    quantidade_fmt: str
    ticket_medio_fmt: str
    crescimento_fmt: str


def compute_dashboard_metrics(dados_financeiros: Sequence[FinancialDashboardRow]) -> FinancialDashboardMetrics:
    valor_total = sum(float(dado.valor_total or 0.0) for dado in dados_financeiros)
    quantidade_total = sum(int(dado.quantidade or 0) for dado in dados_financeiros)
    ticket_medio = valor_total / quantidade_total if quantidade_total > 0 else 0.0

    crescimento_pct = 0.0
    if len(dados_financeiros) >= 2:
        dados_ordenados = sorted(dados_financeiros, key=lambda item: item.data)
        ultimo = float(dados_ordenados[-1].valor_total or 0.0)
        penultimo = float(dados_ordenados[-2].valor_total or 0.0)
        if penultimo > 0:
            crescimento_pct = ((ultimo - penultimo) / penultimo) * 100

    return FinancialDashboardMetrics(
        valor_total=valor_total,
        quantidade_total=quantidade_total,
        ticket_medio=ticket_medio,
        crescimento_pct=crescimento_pct,
        valor_total_fmt=_fmt_currency(valor_total),
        quantidade_fmt=str(quantidade_total),
        ticket_medio_fmt=_fmt_currency(ticket_medio),
        crescimento_fmt=f"{crescimento_pct:+.1f}%",
    )
