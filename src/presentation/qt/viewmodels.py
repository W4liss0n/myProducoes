from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ...application.commands import (
    CreateProductionInput,
    DeleteProductionsInput,
    GenerateOpenReportInput,
    GenerateProductionReportInput,
    RegisterClientReceiptInput,
    SavePixSettingsInput,
    SaveVisibleColumnsInput,
    UpdateProductionInput,
)
from ...application.use_cases import (
    AddProductionTypeCommand,
    CreateManualBackupCommand,
    CreateProductionCommand,
    DeleteProductionsCommand,
    GenerateOpenReportCommand,
    GenerateProductionReportCommand,
    GetClientDetailQuery,
    GetClientSummariesQuery,
    GetFinancialPeriodsQuery,
    GetPixSettingsQuery,
    GetProductionQuery,
    GetVisibleColumnsQuery,
    ListClientsQuery,
    ListOpenProductionsByClientQuery,
    ListProductionsQuery,
    ListProductionTypesQuery,
    ListYearsQuery,
    RegisterClientReceiptCommand,
    RemoveProductionTypeCommand,
    SavePixSettingsCommand,
    SaveVisibleColumnsCommand,
    SuggestReceiptAllocationQuery,
    UpdateProductionCommand,
)
from ...config.constants import (
    DEFAULT_STATUS_OPTIONS,
    DEFAULT_STATUS_PAGAMENTO_OPTIONS,
    DEFAULT_TIPOS_PRODUCAO,
    DEFAULT_VISIBLE_COLUMNS,
)
from ...domain.models import (
    ClientDetail,
    ClientReceipt,
    ClientSummary,
    FolderInspection,
    OperationResult,
    PixSettings,
    Production,
    ProductionFilters,
    ProductionPayload,
    ReceiptAllocation,
    ReceiptAllocationRequest,
)


@dataclass(slots=True)
class MainWindowState:
    producoes: list[Production] = field(default_factory=list)
    tipos_producao: list[str] = field(default_factory=list)
    clientes_list: list[str] = field(default_factory=list)
    anos_disponiveis: list[int] = field(default_factory=list)
    visible_columns: list[str] = field(default_factory=lambda: DEFAULT_VISIBLE_COLUMNS.copy())
    active_filters: ProductionFilters = field(default_factory=ProductionFilters)
    current_page: int = 1
    page_size: int = 100
    total_items: int = 0
    total_pages: int = 1


class MainWindowViewModel:
    def __init__(
        self,
        *,
        list_productions: ListProductionsQuery,
        get_production: GetProductionQuery,
        create_production: CreateProductionCommand,
        update_production: UpdateProductionCommand,
        delete_productions: DeleteProductionsCommand,
        list_types: ListProductionTypesQuery,
        add_type: AddProductionTypeCommand,
        remove_type: RemoveProductionTypeCommand,
        list_clients: ListClientsQuery,
        list_years: ListYearsQuery,
        create_manual_backup: CreateManualBackupCommand,
        get_visible_columns: GetVisibleColumnsQuery,
        save_visible_columns: SaveVisibleColumnsCommand,
    ) -> None:
        self._list_productions = list_productions
        self._get_production = get_production
        self._create_production = create_production
        self._update_production = update_production
        self._delete_productions = delete_productions
        self._list_types = list_types
        self._add_type = add_type
        self._remove_type = remove_type
        self._list_clients = list_clients
        self._list_years = list_years
        self._create_manual_backup = create_manual_backup
        self._get_visible_columns = get_visible_columns
        self._save_visible_columns = save_visible_columns
        self.state = MainWindowState()

    def load_initial_state(self) -> MainWindowState:
        self._ensure_default_types()
        self.state.tipos_producao = self._list_types()
        self.state.clientes_list = self._list_clients()
        self.state.anos_disponiveis = self._list_years()
        self.state.visible_columns = self._get_visible_columns() or DEFAULT_VISIBLE_COLUMNS.copy()
        return self.load_page()

    def load_page(self) -> MainWindowState:
        page = self._list_productions(
            self.state.active_filters,
            page=self.state.current_page,
            page_size=self.state.page_size,
        )
        self.state.producoes = page.items
        self.state.total_items = page.total
        self.state.current_page = page.page
        self.state.total_pages = page.total_pages
        self.state.tipos_producao = self._list_types()
        self.state.clientes_list = self._list_clients()
        self.state.anos_disponiveis = self._list_years()
        return self.state

    def set_filters(self, filters: ProductionFilters) -> MainWindowState:
        self.state.active_filters = filters
        self.state.current_page = 1
        return self.load_page()

    def clear_filters(self) -> MainWindowState:
        return self.set_filters(ProductionFilters())

    def set_page_size(self, page_size: int) -> MainWindowState:
        self.state.page_size = page_size
        self.state.current_page = 1
        return self.load_page()

    def next_page(self) -> MainWindowState:
        if self.state.current_page < self.state.total_pages:
            self.state.current_page += 1
        return self.load_page()

    def previous_page(self) -> MainWindowState:
        if self.state.current_page > 1:
            self.state.current_page -= 1
        return self.load_page()

    def get_production(self, production_id: int) -> Production | None:
        return self._get_production(production_id)

    def create(self, payload: ProductionPayload) -> OperationResult[Production]:
        result = self._create_production(CreateProductionInput(payload=payload))
        self.load_page()
        return result

    def update(self, production_id: int, payload: ProductionPayload) -> OperationResult[Production]:
        result = self._update_production(UpdateProductionInput(production_id=production_id, payload=payload))
        self.load_page()
        return result

    def delete(self, production_ids: list[int]) -> OperationResult[int]:
        result = self._delete_productions(DeleteProductionsInput(production_ids=production_ids))
        self.load_page()
        return result

    def add_type(self, nome: str) -> OperationResult[bool]:
        result = self._add_type(nome)
        self.state.tipos_producao = self._list_types()
        return result

    def remove_type(self, nome: str) -> OperationResult[bool]:
        result = self._remove_type(nome)
        self.state.tipos_producao = self._list_types()
        return result

    def create_manual_backup(self):
        return self._create_manual_backup()

    def save_visible_columns(self, columns: list[str]) -> None:
        self.state.visible_columns = columns
        self._save_visible_columns(SaveVisibleColumnsInput(columns=columns))

    def _ensure_default_types(self) -> None:
        tipos = self._list_types()
        if tipos:
            return
        for tipo in DEFAULT_TIPOS_PRODUCAO:
            self._add_type(tipo)


class ProductionFormViewModel:
    def __init__(self, *, generate_report: GenerateProductionReportCommand, folder_gateway) -> None:
        self._generate_report = generate_report
        self._folder_gateway = folder_gateway

    def inspect_folder(self, folder_path: str) -> FolderInspection:
        return self._folder_gateway.inspect(folder_path)

    def generate_report(self, *, folder_path: str, output_path: Path, production_name: str, company: str):
        return self._generate_report(
            GenerateProductionReportInput(
                folder_path=folder_path,
                output_path=output_path,
                production_name=production_name,
                company=company,
            )
        )


@dataclass(slots=True)
class FinancialDashboardState:
    clientes_list: list[str] = field(default_factory=list)
    tipos_producao: list[str] = field(default_factory=list)
    anos_disponiveis: list[int] = field(default_factory=list)
    periodos: list = field(default_factory=list)


@dataclass(slots=True)
class ClientsOverviewState:
    clients: list[ClientSummary] = field(default_factory=list)
    selected_client: ClientDetail | None = None


class FinancialSummaryViewModel:
    def __init__(
        self,
        *,
        list_clients: ListClientsQuery,
        list_types: ListProductionTypesQuery,
        list_years: ListYearsQuery,
        get_periods: GetFinancialPeriodsQuery,
    ) -> None:
        self._list_clients = list_clients
        self._list_types = list_types
        self._list_years = list_years
        self._get_periods = get_periods
        self.state = FinancialDashboardState()

    def load_initial_state(self) -> FinancialDashboardState:
        self.state.clientes_list = self._list_clients()
        self.state.tipos_producao = self._list_types()
        self.state.anos_disponiveis = self._list_years()
        return self.state

    def load_periods(self, filters: ProductionFilters):
        self.state.periodos = self._get_periods(filters)
        return self.state.periodos


class ClientsOverviewViewModel:
    def __init__(
        self,
        *,
        get_client_summaries: GetClientSummariesQuery,
        get_client_detail: GetClientDetailQuery,
        suggest_allocations: SuggestReceiptAllocationQuery,
        register_receipt: RegisterClientReceiptCommand,
    ) -> None:
        self._get_client_summaries = get_client_summaries
        self._get_client_detail = get_client_detail
        self._suggest_allocations = suggest_allocations
        self._register_receipt = register_receipt
        self.state = ClientsOverviewState()

    def load_initial_state(self) -> ClientsOverviewState:
        self.state.clients = self._get_client_summaries()
        self.state.selected_client = (
            self._get_client_detail(self.state.clients[0].client_id) if self.state.clients else None
        )
        return self.state

    def load_client_detail(self, client_id: int) -> ClientDetail | None:
        self.state.selected_client = self._get_client_detail(client_id)
        return self.state.selected_client

    def suggest_allocations(self, client_id: int, valor_total: float) -> list[ReceiptAllocation]:
        return self._suggest_allocations(client_id, valor_total)

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
    ) -> OperationResult[ClientReceipt]:
        result = self._register_receipt(
            RegisterClientReceiptInput(
                client_id=client_id,
                data_recebimento=data_recebimento,
                valor_total=valor_total,
                forma_pagamento=forma_pagamento,
                observacao=observacao,
                auto_allocate=auto_allocate,
                allocations=allocations,
            )
        )
        if result.success:
            self.state.clients = self._get_client_summaries()
            self.state.selected_client = self._get_client_detail(client_id)
        return result

    @staticmethod
    def format_money(value: float) -> str:
        return f"R$ {float(value or 0.0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class OpenReportSelectionViewModel:
    def __init__(
        self,
        *,
        list_clients: ListClientsQuery,
        list_open_productions: ListOpenProductionsByClientQuery,
        generate_open_report: GenerateOpenReportCommand,
    ) -> None:
        self._list_clients = list_clients
        self._list_open_productions = list_open_productions
        self._generate_open_report = generate_open_report

    def list_clients(self) -> list[str]:
        return self._list_clients()

    def list_open_by_client(self, cliente: str) -> list[Production]:
        return self._list_open_productions(cliente)

    def generate_report(self, *, cliente: str, output_path: Path, production_ids: list[int]):
        return self._generate_open_report(
            GenerateOpenReportInput(
                cliente=cliente,
                output_path=output_path,
                production_ids=production_ids,
            )
        )


class SettingsViewModel:
    def __init__(
        self,
        *,
        get_pix_settings: GetPixSettingsQuery,
        save_pix_settings: SavePixSettingsCommand,
    ) -> None:
        self._get_pix_settings = get_pix_settings
        self._save_pix_settings = save_pix_settings

    def load_pix_settings(self) -> PixSettings:
        return self._get_pix_settings()

    def save_pix_settings(self, settings: PixSettings):
        return self._save_pix_settings(SavePixSettingsInput(settings=settings))

    @staticmethod
    def payment_status_options() -> list[str]:
        return list(DEFAULT_STATUS_PAGAMENTO_OPTIONS)

    @staticmethod
    def production_status_options() -> list[str]:
        return list(DEFAULT_STATUS_OPTIONS)
