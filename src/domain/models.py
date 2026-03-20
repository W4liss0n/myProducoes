from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from math import ceil
from pathlib import Path
from typing import Generic, Optional, TypeVar


@dataclass(slots=True)
class ProductionFilters:
    cliente: Optional[str] = None
    tipo_producao: Optional[str] = None
    status: Optional[str] = None
    status_pagamento: Optional[str] = None
    ano: Optional[int] = None
    mes: Optional[int] = None


@dataclass(slots=True)
class Production:
    id: int
    codigo: str
    cliente: str
    data_recebimento: Optional[date]
    nome: str
    tipo_producao: str
    quantidade_alunos: int
    quantidade_fotos: int
    quantidade_kits: int
    quantidade_capas: int
    valor_por_foto: float
    valor_por_kit: float
    valor_por_capa: float
    valor_total: float
    data_conclusao: Optional[date]
    status_pagamento: str
    status: str
    relatorio: str
    pasta_producao: str
    valor_recebido: float = 0.0
    saldo: float = 0.0


@dataclass(slots=True)
class ProductionPayload:
    cliente: str
    nome: str
    tipo_producao: str
    data_recebimento: Optional[str]
    data_conclusao: Optional[str]
    status: str
    status_pagamento: str
    quantidade_alunos: int
    quantidade_fotos: int
    quantidade_kits: int
    quantidade_capas: int
    valor_por_foto: float
    valor_por_kit: float
    valor_por_capa: float
    pasta_producao: str = ""
    relatorio: str = ""
    codigo: str = ""

    def to_legacy_dict(self) -> dict[str, object]:
        return {
            "cliente": self.cliente,
            "nome": self.nome,
            "tipo_producao": self.tipo_producao,
            "data_recebimento": self.data_recebimento,
            "data_conclusao": self.data_conclusao,
            "status": self.status,
            "status_pagamento": self.status_pagamento,
            "quantidade_alunos": self.quantidade_alunos,
            "quantidade_fotos": self.quantidade_fotos,
            "quantidade_kits": self.quantidade_kits,
            "quantidade_capas": self.quantidade_capas,
            "valor_por_foto": self.valor_por_foto,
            "valor_por_kit": self.valor_por_kit,
            "valor_por_capa": self.valor_por_capa,
            "pasta_producao": self.pasta_producao,
            "relatorio": self.relatorio,
            "codigo": self.codigo or None,
        }


@dataclass(slots=True)
class ProductionPage:
    items: list[Production]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        if self.page_size <= 0:
            return 1
        return max(1, ceil(self.total / self.page_size))


@dataclass(slots=True)
class FinancialPeriod:
    ano: int
    mes: int
    data: str
    valor_total: float
    quantidade: int


@dataclass(slots=True)
class FinancialSummary:
    total: float
    quantidade: int
    periodos: list[FinancialPeriod] = field(default_factory=list)


@dataclass(slots=True)
class ReceiptAllocationRequest:
    production_id: int
    valor_alocado: float


@dataclass(slots=True)
class ReceiptAllocation:
    id: int
    receipt_id: int
    production_id: int
    valor_alocado: float
    production_name: str = ""
    production_code: str = ""


@dataclass(slots=True)
class ClientReceipt:
    id: int
    client_id: int
    cliente: str
    data_recebimento: Optional[date]
    valor_total: float
    valor_nao_alocado: float
    forma_pagamento: str = ""
    observacao: str = ""
    origem: str = ""
    allocations: list[ReceiptAllocation] = field(default_factory=list)


@dataclass(slots=True)
class OpenProductionBalance:
    production_id: int
    codigo: str
    nome: str
    data_recebimento: Optional[date]
    valor_total: float
    valor_recebido: float
    saldo: float
    status: str
    status_pagamento: str


@dataclass(slots=True)
class ClientSummary:
    client_id: int
    cliente: str
    total_productions: int
    open_productions: int
    in_progress_productions: int
    valor_contratado: float
    valor_recebido: float
    saldo: float
    credito: float


@dataclass(slots=True)
class ClientDetail:
    summary: ClientSummary
    productions: list[Production] = field(default_factory=list)
    open_balances: list[OpenProductionBalance] = field(default_factory=list)
    receipts: list[ClientReceipt] = field(default_factory=list)


@dataclass(slots=True)
class StudentReportRow:
    id: str
    fotos: int
    kits: int
    capas: int
    curso: str


@dataclass(slots=True)
class FolderInspection:
    total_fotos: int
    total_alunos: int
    total_kits: int


@dataclass(slots=True)
class PixSettings:
    nome_beneficiario: str = ""
    chave_pix: str = ""
    cidade: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "nome_beneficiario": self.nome_beneficiario,
            "chave_pix": self.chave_pix,
            "cidade": self.cidade,
        }


T = TypeVar("T")


@dataclass(slots=True)
class OperationResult(Generic[T]):
    success: bool
    message: str = ""
    data: Optional[T] = None
    output_path: Optional[Path] = None
