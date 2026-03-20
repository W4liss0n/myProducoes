from __future__ import annotations

from dataclasses import dataclass

from ..domain.contracts import (
    BackupGateway,
    ClientFinanceRepository,
    FolderInspectionGateway,
    OperationsGateway,
    ProductionRepository,
    ReferenceRepository,
    ReportGenerationGateway,
    SettingsRepository,
)
from ..domain.models import (
    ClientDetail,
    ClientReceipt,
    ClientSummary,
    FinancialSummary,
    OperationResult,
    PixSettings,
    Production,
    ProductionFilters,
    ReceiptAllocation,
)
from .commands import (
    CreateProductionInput,
    DeleteProductionsInput,
    GenerateOpenReportInput,
    GenerateProductionReportInput,
    RegisterClientReceiptInput,
    SavePixSettingsInput,
    SaveVisibleColumnsInput,
    UpdateProductionInput,
)


@dataclass(slots=True)
class ListProductionsQuery:
    repository: ProductionRepository

    def __call__(self, filters: ProductionFilters, *, page: int, page_size: int):
        return self.repository.list_page(filters, page=page, page_size=page_size)


@dataclass(slots=True)
class GetProductionQuery:
    repository: ProductionRepository

    def __call__(self, production_id: int) -> Production | None:
        return self.repository.get_by_id(production_id)


@dataclass(slots=True)
class CreateProductionCommand:
    repository: ProductionRepository

    def __call__(self, command: CreateProductionInput) -> OperationResult[Production]:
        try:
            created = self.repository.create(command.payload)
        except ValueError as exc:
            return OperationResult(success=False, message=str(exc))
        if created is None:
            return OperationResult(success=False, message="Não foi possível criar a produção.")
        return OperationResult(success=True, message="Produção criada com sucesso.", data=created)


@dataclass(slots=True)
class UpdateProductionCommand:
    repository: ProductionRepository

    def __call__(self, command: UpdateProductionInput) -> OperationResult[Production]:
        try:
            updated = self.repository.update(command.production_id, command.payload)
        except ValueError as exc:
            return OperationResult(success=False, message=str(exc))
        if updated is None:
            return OperationResult(success=False, message="Produção não encontrada.")
        return OperationResult(success=True, message="Produção atualizada com sucesso.", data=updated)


@dataclass(slots=True)
class DeleteProductionsCommand:
    repository: ProductionRepository

    def __call__(self, command: DeleteProductionsInput) -> OperationResult[int]:
        removed = self.repository.delete_many(command.production_ids)
        return OperationResult(success=True, message="Produções removidas com sucesso.", data=removed)


@dataclass(slots=True)
class ListOpenProductionsByClientQuery:
    repository: ProductionRepository

    def __call__(self, cliente: str) -> list[Production]:
        return self.repository.list_open_by_client(cliente)


@dataclass(slots=True)
class GetFinancialPeriodsQuery:
    repository: ProductionRepository

    def __call__(self, filters: ProductionFilters):
        return self.repository.get_financial_periods(filters)


@dataclass(slots=True)
class GetFinancialSummaryQuery:
    repository: ProductionRepository

    def __call__(self, *, ano: int | None = None, cliente: str | None = None) -> FinancialSummary:
        return self.repository.get_financial_summary(ano=ano, cliente=cliente)


@dataclass(slots=True)
class GetClientSummariesQuery:
    repository: ClientFinanceRepository

    def __call__(self) -> list[ClientSummary]:
        return self.repository.list_client_summaries()


@dataclass(slots=True)
class GetClientDetailQuery:
    repository: ClientFinanceRepository

    def __call__(self, client_id: int) -> ClientDetail | None:
        return self.repository.get_client_detail(client_id)


@dataclass(slots=True)
class SuggestReceiptAllocationQuery:
    repository: ClientFinanceRepository

    def __call__(self, client_id: int, valor_total: float) -> list[ReceiptAllocation]:
        return self.repository.suggest_receipt_allocations(client_id, valor_total)


@dataclass(slots=True)
class RegisterClientReceiptCommand:
    repository: ClientFinanceRepository

    def __call__(self, command: RegisterClientReceiptInput) -> OperationResult[ClientReceipt]:
        try:
            receipt = self.repository.register_client_receipt(
                client_id=command.client_id,
                data_recebimento=command.data_recebimento,
                valor_total=command.valor_total,
                forma_pagamento=command.forma_pagamento,
                observacao=command.observacao,
                auto_allocate=command.auto_allocate,
                allocations=command.allocations,
            )
        except ValueError as exc:
            return OperationResult(success=False, message=str(exc))
        if receipt is None:
            return OperationResult(success=False, message="Não foi possível registrar o recebimento.")
        return OperationResult(success=True, message="Recebimento registrado com sucesso.", data=receipt)


@dataclass(slots=True)
class ListProductionTypesQuery:
    repository: ReferenceRepository

    def __call__(self) -> list[str]:
        return self.repository.list_tipos()


@dataclass(slots=True)
class AddProductionTypeCommand:
    repository: ReferenceRepository

    def __call__(self, nome: str) -> OperationResult[bool]:
        created = self.repository.add_tipo(nome)
        if not created:
            return OperationResult(success=False, message="Tipo já existe ou é inválido.", data=False)
        return OperationResult(success=True, message="Tipo cadastrado com sucesso.", data=True)


@dataclass(slots=True)
class RemoveProductionTypeCommand:
    repository: ReferenceRepository

    def __call__(self, nome: str) -> OperationResult[bool]:
        removed = self.repository.remove_tipo(nome)
        if not removed:
            return OperationResult(success=False, message="Tipo não encontrado.", data=False)
        return OperationResult(success=True, message="Tipo removido com sucesso.", data=True)


@dataclass(slots=True)
class ListClientsQuery:
    repository: ReferenceRepository

    def __call__(self) -> list[str]:
        return self.repository.list_clientes()


@dataclass(slots=True)
class ListYearsQuery:
    repository: ReferenceRepository

    def __call__(self) -> list[int]:
        return self.repository.list_anos()


@dataclass(slots=True)
class GenerateProductionReportCommand:
    folder_gateway: FolderInspectionGateway
    report_gateway: ReportGenerationGateway

    def __call__(self, command: GenerateProductionReportInput) -> OperationResult[bool]:
        inspection = self.folder_gateway.inspect(command.folder_path)
        if inspection.total_alunos <= 0:
            return OperationResult(success=False, message="Não foram encontrados alunos na pasta.")

        ok = self.report_gateway.generate_production_report(
            folder_path=command.folder_path,
            output_path=command.output_path,
            production_name=command.production_name,
            company=command.company,
            include_covers=command.include_covers,
        )
        message = "Relatório gerado com sucesso." if ok else "Não foi possível gerar o relatório."
        return OperationResult(success=ok, message=message, data=ok, output_path=command.output_path if ok else None)


@dataclass(slots=True)
class GenerateOpenReportCommand:
    repository: ProductionRepository
    report_gateway: ReportGenerationGateway

    def __call__(self, command: GenerateOpenReportInput) -> OperationResult[bool]:
        producoes = self.repository.list_open_by_client(command.cliente)
        if command.production_ids:
            allowed = set(command.production_ids)
            producoes = [producao for producao in producoes if producao.id in allowed]

        if not producoes:
            return OperationResult(success=False, message="Nenhuma produção em aberto selecionada.")

        ok = self.report_gateway.generate_open_productions_report(
            output_path=command.output_path,
            cliente=command.cliente,
            producoes=producoes,
        )
        message = "Relatório gerado com sucesso." if ok else "Não foi possível gerar o relatório."
        return OperationResult(success=ok, message=message, data=ok, output_path=command.output_path if ok else None)


@dataclass(slots=True)
class CreateManualBackupCommand:
    gateway: BackupGateway

    def __call__(self):
        backup_path = self.gateway.create_manual_backup()
        if backup_path is None:
            return OperationResult(success=False, message="Não foi possível criar backup manual.")
        return OperationResult(success=True, message="Backup criado com sucesso.", output_path=backup_path)


@dataclass(slots=True)
class RunDatabaseBootstrapCommand:
    gateway: OperationsGateway

    def __call__(self) -> None:
        self.gateway.ensure_ready()


@dataclass(slots=True)
class GetPixSettingsQuery:
    repository: SettingsRepository

    def __call__(self) -> PixSettings:
        return self.repository.load_pix_settings()


@dataclass(slots=True)
class SavePixSettingsCommand:
    repository: SettingsRepository

    def __call__(self, command: SavePixSettingsInput) -> OperationResult[PixSettings]:
        self.repository.save_pix_settings(command.settings)
        return OperationResult(success=True, message="Configurações PIX salvas com sucesso.", data=command.settings)


@dataclass(slots=True)
class GetVisibleColumnsQuery:
    repository: SettingsRepository

    def __call__(self) -> list[str] | None:
        return self.repository.load_visible_columns()


@dataclass(slots=True)
class SaveVisibleColumnsCommand:
    repository: SettingsRepository

    def __call__(self, command: SaveVisibleColumnsInput) -> OperationResult[list[str]]:
        self.repository.save_visible_columns(command.columns)
        return OperationResult(success=True, message="Preferências de colunas salvas.", data=command.columns)
