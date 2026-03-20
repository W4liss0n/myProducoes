from __future__ import annotations

import sys
from dataclasses import dataclass

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

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
    RunDatabaseBootstrapCommand,
    SavePixSettingsCommand,
    SaveVisibleColumnsCommand,
    SuggestReceiptAllocationQuery,
    UpdateProductionCommand,
)
from ...infrastructure.filesystem.gateways import (
    FileSystemFolderInspectionGateway,
    ReportLabReportGenerationGateway,
)
from ...infrastructure.settings.file_settings_repository import FileSettingsRepository
from ...infrastructure.sqlite.backend import SqliteBackendAdapter
from ...presentation.qt.constants import APP_STYLESHEET, FONT_FAMILY
from ...presentation.qt.main_window import MainWindow
from ...presentation.qt.viewmodels import (
    ClientsOverviewViewModel,
    FinancialSummaryViewModel,
    MainWindowViewModel,
    OpenReportSelectionViewModel,
    ProductionFormViewModel,
    SettingsViewModel,
)
from .coordinator import DesktopCoordinator


@dataclass(frozen=True)
class DesktopRuntime:
    app: QApplication
    window: MainWindow
    coordinator: DesktopCoordinator
    backend: SqliteBackendAdapter


def build_runtime(
    *,
    db_path=None,
    alembic_ini_path=None,
    backup_dir=None,
) -> DesktopRuntime:
    backend = SqliteBackendAdapter(
        db_path=db_path,
        alembic_ini_path=alembic_ini_path,
        backup_dir=backup_dir,
    )
    settings = FileSettingsRepository()
    folder_gateway = FileSystemFolderInspectionGateway()
    report_gateway = ReportLabReportGenerationGateway()

    RunDatabaseBootstrapCommand(backend)()
    backend.maybe_create_daily_backup()

    list_productions = ListProductionsQuery(backend)
    get_production = GetProductionQuery(backend)
    create_production = CreateProductionCommand(backend)
    update_production = UpdateProductionCommand(backend)
    delete_productions = DeleteProductionsCommand(backend)
    list_types = ListProductionTypesQuery(backend)
    add_type = AddProductionTypeCommand(backend)
    remove_type = RemoveProductionTypeCommand(backend)
    list_clients = ListClientsQuery(backend)
    list_years = ListYearsQuery(backend)
    create_manual_backup = CreateManualBackupCommand(backend)
    get_visible_columns = GetVisibleColumnsQuery(settings)
    save_visible_columns = SaveVisibleColumnsCommand(settings)
    generate_production_report = GenerateProductionReportCommand(folder_gateway, report_gateway)
    get_financial_periods = GetFinancialPeriodsQuery(backend)
    get_client_summaries = GetClientSummariesQuery(backend)
    get_client_detail = GetClientDetailQuery(backend)
    suggest_receipt_allocations = SuggestReceiptAllocationQuery(backend)
    register_client_receipt = RegisterClientReceiptCommand(backend)
    list_open_productions = ListOpenProductionsByClientQuery(backend)
    generate_open_report = GenerateOpenReportCommand(backend, report_gateway)
    get_pix_settings = GetPixSettingsQuery(settings)
    save_pix_settings = SavePixSettingsCommand(settings)

    main_view_model = MainWindowViewModel(
        list_productions=list_productions,
        get_production=get_production,
        create_production=create_production,
        update_production=update_production,
        delete_productions=delete_productions,
        list_types=list_types,
        add_type=add_type,
        remove_type=remove_type,
        list_clients=list_clients,
        list_years=list_years,
        create_manual_backup=create_manual_backup,
        get_visible_columns=get_visible_columns,
        save_visible_columns=save_visible_columns,
    )
    form_view_model = ProductionFormViewModel(generate_report=generate_production_report, folder_gateway=folder_gateway)
    financial_view_model = FinancialSummaryViewModel(
        list_clients=list_clients,
        list_types=list_types,
        list_years=list_years,
        get_periods=get_financial_periods,
    )
    clients_view_model = ClientsOverviewViewModel(
        get_client_summaries=get_client_summaries,
        get_client_detail=get_client_detail,
        suggest_allocations=suggest_receipt_allocations,
        register_receipt=register_client_receipt,
    )
    open_report_view_model = OpenReportSelectionViewModel(
        list_clients=list_clients,
        list_open_productions=list_open_productions,
        generate_open_report=generate_open_report,
    )
    settings_view_model = SettingsViewModel(
        get_pix_settings=get_pix_settings,
        save_pix_settings=save_pix_settings,
    )
    coordinator = DesktopCoordinator(
        main_view_model=main_view_model,
        form_view_model=form_view_model,
        financial_view_model=financial_view_model,
        clients_view_model=clients_view_model,
        open_report_view_model=open_report_view_model,
        settings_view_model=settings_view_model,
    )

    existing_app = QApplication.instance()
    app = existing_app if isinstance(existing_app, QApplication) else QApplication(sys.argv)
    font = QFont(FONT_FAMILY, 10)
    app.setFont(font)
    app.setStyleSheet(APP_STYLESHEET)
    app.setApplicationName("Gerenciador de Produções")
    app.setOrganizationName("MyProducoes")

    window = MainWindow(view_model=main_view_model, coordinator=coordinator)
    return DesktopRuntime(
        app=app,
        window=window,
        coordinator=coordinator,
        backend=backend,
    )


def run() -> int:
    runtime = build_runtime()
    runtime.window.show()
    return runtime.app.exec()
