from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .models import (
    ClientDetail,
    ClientReceipt,
    ClientSummary,
    FinancialPeriod,
    FinancialSummary,
    FolderInspection,
    PixSettings,
    Production,
    ProductionFilters,
    ProductionPage,
    ProductionPayload,
    ReceiptAllocation,
    ReceiptAllocationRequest,
    StudentReportRow,
)


class ProductionRepository(Protocol):
    def list_page(self, filters: ProductionFilters, *, page: int, page_size: int) -> ProductionPage: ...

    def list_all(self, filters: ProductionFilters) -> list[Production]: ...

    def get_by_id(self, production_id: int) -> Production | None: ...

    def create(self, payload: ProductionPayload) -> Production | None: ...

    def update(self, production_id: int, payload: ProductionPayload) -> Production | None: ...

    def delete_many(self, production_ids: list[int]) -> int: ...

    def list_open_by_client(self, cliente: str) -> list[Production]: ...

    def get_financial_periods(self, filters: ProductionFilters) -> list[FinancialPeriod]: ...

    def get_financial_summary(self, *, ano: int | None = None, cliente: str | None = None) -> FinancialSummary: ...


class ClientFinanceRepository(Protocol):
    def list_client_summaries(self) -> list[ClientSummary]: ...

    def get_client_detail(self, client_id: int) -> ClientDetail | None: ...

    def suggest_receipt_allocations(self, client_id: int, valor_total: float) -> list[ReceiptAllocation]: ...

    def register_client_receipt(
        self,
        *,
        client_id: int,
        data_recebimento: str | None,
        valor_total: float,
        forma_pagamento: str,
        observacao: str,
        auto_allocate: bool,
        allocations: list[ReceiptAllocationRequest],
    ) -> ClientReceipt | None: ...


class ReferenceRepository(Protocol):
    def list_tipos(self) -> list[str]: ...

    def add_tipo(self, nome: str) -> bool: ...

    def remove_tipo(self, nome: str) -> bool: ...

    def list_clientes(self) -> list[str]: ...

    def list_anos(self) -> list[int]: ...


class SettingsRepository(Protocol):
    def load_pix_settings(self) -> PixSettings: ...

    def save_pix_settings(self, settings: PixSettings) -> None: ...

    def load_visible_columns(self) -> list[str] | None: ...

    def save_visible_columns(self, columns: list[str]) -> None: ...


class BackupGateway(Protocol):
    def create_manual_backup(self) -> Path | None: ...


class OperationsGateway(Protocol):
    def ensure_ready(self) -> None: ...

    def maybe_create_daily_backup(self) -> Path | None: ...


class FolderInspectionGateway(Protocol):
    def inspect(self, folder_path: str) -> FolderInspection: ...

    def extract_students(self, folder_path: str) -> list[StudentReportRow]: ...


class ReportGenerationGateway(Protocol):
    def generate_production_report(
        self,
        *,
        folder_path: str,
        output_path: Path,
        production_name: str,
        company: str,
        include_covers: bool = True,
    ) -> bool: ...

    def generate_open_productions_report(
        self,
        *,
        output_path: Path,
        cliente: str,
        producoes: list[Production],
    ) -> bool: ...
