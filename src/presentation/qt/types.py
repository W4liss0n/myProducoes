from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ProductionFormData:
    cliente: str = ""
    nome: str = ""
    tipo_producao: str = ""
    data_recebimento: str | None = None
    data_conclusao: str | None = None
    status: str = ""
    status_pagamento: str = ""
    quantidade_alunos: int = 0
    quantidade_fotos: int = 0
    quantidade_kits: int = 0
    quantidade_capas: int = 0
    valor_por_foto: float = 0.0
    valor_por_kit: float = 0.0
    valor_por_capa: float = 0.0
    valor_recebido: float = 0.0
    saldo: float = 0.0
    pasta_producao: str = ""
    relatorio: str = ""
    codigo: str = ""


@dataclass(slots=True)
class ProductionTableRow:
    production_id: int
    values: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class FinancialDashboardRow:
    ano: int
    mes: int
    data: str
    valor_total: float
    quantidade: int
