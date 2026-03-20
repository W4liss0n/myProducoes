from __future__ import annotations

from pathlib import Path

from ...domain.models import (
    ClientDetail,
    ClientReceipt,
    ClientSummary,
    FinancialPeriod,
    FinancialSummary,
    Production,
    ProductionFilters,
    ProductionPage,
    ProductionPayload,
    ReceiptAllocation,
    ReceiptAllocationRequest,
)
from .backup import SqliteBackupService
from .bootstrap import SqliteDatabaseBootstrap
from .repositories import (
    SqliteClientFinanceRepository,
    SqliteFinancialReadRepository,
    SqliteProductionRepository,
    SqliteReferenceRepository,
)
from .session import SqliteSessionFactory


class SqliteBackendAdapter:
    """Adapter de composição para os contratos da aplicação."""

    def __init__(
        self,
        *,
        db_path: Path | str | None = None,
        alembic_ini_path: Path | str | None = None,
        backup_dir: Path | str | None = None,
    ) -> None:
        self._sessions = SqliteSessionFactory(db_path=db_path)
        self._production_repository = SqliteProductionRepository(self._sessions)
        self._reference_repository = SqliteReferenceRepository(self._sessions)
        self._financial_repository = SqliteFinancialReadRepository(self._sessions)
        self._client_finance_repository = SqliteClientFinanceRepository(self._sessions)
        self._bootstrap = SqliteDatabaseBootstrap(
            db_path=db_path,
            alembic_ini_path=alembic_ini_path,
            backup_dir=backup_dir,
        )
        self._backup = SqliteBackupService(db_path=db_path, backup_dir=backup_dir)

    def ensure_ready(self) -> None:
        self._bootstrap.ensure_ready()

    def maybe_create_daily_backup(self) -> Path | None:
        return self._backup.maybe_create_daily_backup()

    def create_manual_backup(self) -> Path | None:
        return self._backup.create_backup(reason="manual")

    def list_page(self, filters: ProductionFilters, *, page: int, page_size: int) -> ProductionPage:
        return self._production_repository.list_page(filters, page=page, page_size=page_size)

    def list_all(self, filters: ProductionFilters) -> list[Production]:
        return self._production_repository.list_all(filters)

    def get_by_id(self, production_id: int) -> Production | None:
        return self._production_repository.get_by_id(production_id)

    def create(self, payload: ProductionPayload) -> Production | None:
        return self._production_repository.create(payload)

    def update(self, production_id: int, payload: ProductionPayload) -> Production | None:
        return self._production_repository.update(production_id, payload)

    def delete_many(self, production_ids: list[int]) -> int:
        return self._production_repository.delete_many(production_ids)

    def list_open_by_client(self, cliente: str) -> list[Production]:
        return self._production_repository.list_open_by_client(cliente)

    def get_financial_periods(self, filters: ProductionFilters) -> list[FinancialPeriod]:
        return self._financial_repository.get_financial_periods(filters)

    def get_financial_summary(self, *, ano: int | None = None, cliente: str | None = None) -> FinancialSummary:
        return self._financial_repository.get_financial_summary(ano=ano, cliente=cliente)

    def list_client_summaries(self) -> list[ClientSummary]:
        return self._client_finance_repository.list_client_summaries()

    def get_client_detail(self, client_id: int) -> ClientDetail | None:
        return self._client_finance_repository.get_client_detail(client_id)

    def suggest_receipt_allocations(self, client_id: int, valor_total: float) -> list[ReceiptAllocation]:
        return self._client_finance_repository.suggest_receipt_allocations(client_id, valor_total)

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
    ) -> ClientReceipt | None:
        return self._client_finance_repository.register_client_receipt(
            client_id=client_id,
            data_recebimento=data_recebimento,
            valor_total=valor_total,
            forma_pagamento=forma_pagamento,
            observacao=observacao,
            auto_allocate=auto_allocate,
            allocations=allocations,
        )

    def list_tipos(self) -> list[str]:
        return self._reference_repository.list_tipos()

    def add_tipo(self, nome: str) -> bool:
        return self._reference_repository.add_tipo(nome)

    def remove_tipo(self, nome: str) -> bool:
        return self._reference_repository.remove_tipo(nome)

    def list_clientes(self) -> list[str]:
        return self._reference_repository.list_clientes()

    def list_anos(self) -> list[int]:
        return self._reference_repository.list_anos()

    def list_backups(self) -> list[Path]:
        return self._backup.list_backups()

    def restore_backup(self, backup_path: Path | str) -> bool:
        return self._backup.restore_backup(backup_path)
