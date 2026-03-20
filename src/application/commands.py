from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..domain.models import PixSettings, ProductionFilters, ProductionPayload, ReceiptAllocationRequest


@dataclass(slots=True)
class CreateProductionInput:
    payload: ProductionPayload


@dataclass(slots=True)
class UpdateProductionInput:
    production_id: int
    payload: ProductionPayload


@dataclass(slots=True)
class DeleteProductionsInput:
    production_ids: list[int]


@dataclass(slots=True)
class GenerateProductionReportInput:
    folder_path: str
    output_path: Path
    production_name: str
    company: str
    include_covers: bool = True


@dataclass(slots=True)
class GenerateOpenReportInput:
    cliente: str
    output_path: Path
    production_ids: list[int] | None = None
    filters: ProductionFilters | None = None


@dataclass(slots=True)
class SavePixSettingsInput:
    settings: PixSettings


@dataclass(slots=True)
class SaveVisibleColumnsInput:
    columns: list[str]


@dataclass(slots=True)
class RegisterClientReceiptInput:
    client_id: int
    data_recebimento: str | None
    valor_total: float
    forma_pagamento: str = ""
    observacao: str = ""
    auto_allocate: bool = True
    allocations: list[ReceiptAllocationRequest] = field(default_factory=list)
