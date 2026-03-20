from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from PyQt6.QtWidgets import QWidget

from ...domain.models import (
    ClientDetail,
    ClientReceipt,
    FinancialPeriod,
    FolderInspection,
    OperationResult,
    PixSettings,
    Production,
    ProductionFilters,
    ReceiptAllocation,
    ReceiptAllocationRequest,
)
from .viewmodels import ClientsOverviewState, FinancialDashboardState, MainWindowState


@runtime_checkable
class ProductionFormViewModelProtocol(Protocol):
    def inspect_folder(self, folder_path: str) -> FolderInspection: ...

    def generate_report(
        self,
        *,
        folder_path: str,
        output_path: Path,
        production_name: str,
        company: str,
    ) -> OperationResult[object]: ...


@runtime_checkable
class OpenReportSelectionViewModelProtocol(Protocol):
    def list_clients(self) -> list[str]: ...

    def list_open_by_client(self, cliente: str) -> list[Production]: ...


@runtime_checkable
class FinancialSummaryViewModelProtocol(Protocol):
    def load_initial_state(self) -> FinancialDashboardState: ...

    def load_periods(self, filters: ProductionFilters) -> list[FinancialPeriod]: ...


@runtime_checkable
class ClientsOverviewViewModelProtocol(Protocol):
    def load_initial_state(self) -> ClientsOverviewState: ...

    def load_client_detail(self, client_id: int) -> ClientDetail | None: ...

    def suggest_allocations(self, client_id: int, valor_total: float) -> list[ReceiptAllocation]: ...

    def register_receipt(
        self,
        *,
        client_id: int,
        data_recebimento: str | None,
        valor_total: float,
        forma_pagamento: str,
        observacao: str,
        auto_allocate: bool,
        allocations: list[ReceiptAllocationRequest],
    ) -> OperationResult[ClientReceipt]: ...

    def format_money(self, value: float) -> str: ...


@runtime_checkable
class MainWindowCoordinatorProtocol(Protocol):
    def open_add_production(
        self,
        parent: QWidget | None,
        tipos_producao: list[str],
        clientes_list: list[str],
    ) -> bool: ...

    def open_edit_production(
        self,
        parent: QWidget | None,
        production_id: int,
        tipos_producao: list[str],
        clientes_list: list[str],
    ) -> bool: ...

    def open_open_report_dialog(self, parent: QWidget | None) -> bool: ...

    def open_financial_summary(self, parent: QWidget | None) -> None: ...

    def open_clients_dialog(self, parent: QWidget | None) -> bool: ...

    def load_pix_settings(self) -> PixSettings: ...

    def save_pix_settings(self, config: dict[str, str]) -> None: ...


@runtime_checkable
class MainWindowViewModelProtocol(Protocol):
    def load_initial_state(self) -> MainWindowState: ...

    def load_page(self) -> MainWindowState: ...

    def set_filters(self, filters: ProductionFilters) -> MainWindowState: ...

    def clear_filters(self) -> MainWindowState: ...

    def set_page_size(self, page_size: int) -> MainWindowState: ...

    def next_page(self) -> MainWindowState: ...

    def previous_page(self) -> MainWindowState: ...

    def get_production(self, production_id: int) -> Production | None: ...

    def delete(self, production_ids: list[int]) -> OperationResult[int]: ...

    def add_type(self, nome: str) -> OperationResult[bool]: ...

    def remove_type(self, nome: str) -> OperationResult[bool]: ...

    def create_manual_backup(self) -> OperationResult[bool]: ...

    def save_visible_columns(self, columns: list[str]) -> None: ...
