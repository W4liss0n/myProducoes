from __future__ import annotations

from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.orm import joinedload

from ...config.constants import DEFAULT_STATUS_PAGAMENTO_OPTIONS
from ...domain.models import (
    ClientDetail,
    ClientReceipt,
    ClientSummary,
    FinancialPeriod,
    FinancialSummary,
    OpenProductionBalance,
    Production,
    ProductionFilters,
    ProductionPage,
    ProductionPayload,
    ReceiptAllocation,
    ReceiptAllocationRequest,
)
from .collaborators import (
    ProductionCodeGenerator,
    ProductionItemInput,
    ProductionTotalsCalculator,
    StatusCanonicalizer,
    to_decimal,
)
from .mapper import SqliteOrmMapper
from .orm import (
    AlocacaoRecebimento,
    Cliente,
    ItemProducao,
    Producao,
    RecebimentoCliente,
    StatusPagamento,
    TipoProducao,
)
from .session import SqliteSessionFactory, month_date_range, to_date, to_int, year_date_range

ZERO = Decimal("0.00")
OPEN_PAYMENT_STATUSES = {"Em aberto", "Parcial"}


def _decimal_or_zero(value) -> Decimal:
    return to_decimal(value) or ZERO


class _SqlitePaymentProjectionMixin:
    sessions: SqliteSessionFactory
    mapper: SqliteOrmMapper

    def _payment_status_name(self, valor_total: Decimal, valor_recebido: Decimal) -> str:
        if valor_recebido <= ZERO and valor_total > ZERO:
            return "Em aberto"
        if valor_recebido < valor_total:
            return "Parcial"
        return "Pago"

    def _status_pagamento_map(self, session) -> dict[str, StatusPagamento]:
        return {
            name: self.sessions.get_or_create_status_pagamento(session, name)
            for name in DEFAULT_STATUS_PAGAMENTO_OPTIONS
        }

    def _allocated_total_for_production(self, session, production_id: int) -> Decimal:
        total = session.execute(
            select(func.coalesce(func.sum(AlocacaoRecebimento.valor_alocado), 0)).where(
                AlocacaoRecebimento.producao_id == production_id
            )
        ).scalar_one()
        return _decimal_or_zero(total)

    def _refresh_payment_projection(self, session, production_ids: list[int]) -> None:
        target_ids = sorted({int(production_id) for production_id in production_ids if production_id})
        if not target_ids:
            return

        statuses = self._status_pagamento_map(session)
        producoes = session.execute(select(Producao).where(Producao.id.in_(target_ids))).scalars().all()
        for producao in producoes:
            valor_total = _decimal_or_zero(producao.valor_total)
            valor_recebido = self._allocated_total_for_production(session, producao.id)
            status_name = self._payment_status_name(valor_total, valor_recebido)
            producao.status_pagamento_id = statuses[status_name].id

    def _build_open_balances(
        self,
        session,
        client_id: int,
        *,
        only_with_balance: bool = True,
    ) -> list[OpenProductionBalance]:
        query = self.sessions.base_producao_query(session).filter(Producao.cliente_id == client_id)
        query = query.order_by(Producao.data_recebimento.asc(), Producao.id.asc())
        balances: list[OpenProductionBalance] = []
        for producao in query.all():
            mapped = self.mapper.production_from_orm(producao)
            if only_with_balance and mapped.saldo <= 0:
                continue
            balances.append(
                OpenProductionBalance(
                    production_id=mapped.id,
                    codigo=mapped.codigo,
                    nome=mapped.nome,
                    data_recebimento=mapped.data_recebimento,
                    valor_total=mapped.valor_total,
                    valor_recebido=mapped.valor_recebido,
                    saldo=mapped.saldo,
                    status=mapped.status,
                    status_pagamento=mapped.status_pagamento,
                )
            )
        return balances

    @staticmethod
    def _receipt_from_orm(receipt: RecebimentoCliente) -> ClientReceipt:
        allocations = [
            ReceiptAllocation(
                id=allocation.id,
                receipt_id=receipt.id,
                production_id=allocation.producao_id,
                valor_alocado=float(_decimal_or_zero(allocation.valor_alocado)),
                production_name=allocation.producao.nome if allocation.producao else "",
                production_code=allocation.producao.codigo or "" if allocation.producao else "",
            )
            for allocation in sorted(receipt.alocacoes, key=lambda item: item.id)
        ]
        return ClientReceipt(
            id=receipt.id,
            client_id=receipt.cliente_id,
            cliente=receipt.cliente.nome if receipt.cliente else "",
            data_recebimento=receipt.data_recebimento,
            valor_total=float(_decimal_or_zero(receipt.valor_total)),
            valor_nao_alocado=float(_decimal_or_zero(receipt.valor_nao_alocado)),
            forma_pagamento=receipt.forma_pagamento or "",
            observacao=receipt.observacao or "",
            origem=receipt.origem or "",
            allocations=allocations,
        )


class SqliteProductionRepository(_SqlitePaymentProjectionMixin):
    def __init__(
        self,
        sessions: SqliteSessionFactory,
        mapper: SqliteOrmMapper | None = None,
        *,
        status_canonicalizer: StatusCanonicalizer | None = None,
        totals_calculator: ProductionTotalsCalculator | None = None,
        code_generator: ProductionCodeGenerator | None = None,
    ) -> None:
        self.sessions = sessions
        self.mapper = mapper or SqliteOrmMapper()
        self.status_canonicalizer = status_canonicalizer or StatusCanonicalizer()
        self.totals_calculator = totals_calculator or ProductionTotalsCalculator()
        self.code_generator = code_generator or ProductionCodeGenerator()

    def create(self, payload: ProductionPayload) -> Production | None:
        with self.sessions.session_scope() as session:
            cliente = self.sessions.get_or_create_cliente(session, payload.cliente)
            tipo = self.sessions.get_or_create_tipo(session, payload.tipo_producao)
            data_recebimento = to_date(payload.data_recebimento)
            status_prod_nome = self.status_canonicalizer.production_status(payload.status or "Parado")
            status_prod = self.sessions.get_or_create_status_producao(session, status_prod_nome)
            status_pag = self.sessions.get_or_create_status_pagamento(session, "Em aberto")
            code_context = self.code_generator.sequence_context(tipo.nome, data_recebimento)
            last_code = self.sessions.find_last_code(session, like_pattern=code_context.like_pattern)
            codigo = payload.codigo or self.code_generator.build_code(code_context, last_code)

            producao = Producao(
                codigo=codigo,
                nome=payload.nome,
                data_recebimento=data_recebimento,
                data_conclusao=to_date(payload.data_conclusao),
                quantidade_alunos=to_int(payload.quantidade_alunos, 0),
                pasta_producao=payload.pasta_producao or None,
                relatorio=payload.relatorio or None,
                valor_total=self.totals_calculator.calculate_total(payload),
                cliente_id=cliente.id,
                tipo_producao_id=tipo.id,
                status_producao_id=status_prod.id,
                status_pagamento_id=status_pag.id,
            )

            session.add(producao)
            session.flush()
            self._sync_items(session, producao, self.totals_calculator.build_item_inputs(payload))
            self._refresh_payment_projection(session, [producao.id])
            session.flush()
            created = self.sessions.base_producao_query(session).filter(Producao.id == producao.id).one_or_none()
            return self.mapper.production_from_orm(created) if created else None

    def update(self, production_id: int, payload: ProductionPayload) -> Production | None:
        with self.sessions.session_scope() as session:
            producao = session.get(Producao, production_id)
            if not producao:
                return None

            cliente = self.sessions.get_or_create_cliente(session, payload.cliente)
            if producao.alocacoes and producao.cliente_id != cliente.id:
                raise ValueError("Não é possível alterar o cliente de uma produção com recebimentos alocados.")

            novo_valor_total = self.totals_calculator.calculate_total(payload)
            valor_recebido = self._allocated_total_for_production(session, production_id)
            if valor_recebido > novo_valor_total:
                raise ValueError("Não é possível reduzir o valor total abaixo do valor já recebido.")

            tipo = self.sessions.get_or_create_tipo(session, payload.tipo_producao)
            status_prod_nome = self.status_canonicalizer.production_status(payload.status or "Parado")
            status_prod = self.sessions.get_or_create_status_producao(session, status_prod_nome)

            producao.cliente_id = cliente.id
            producao.tipo_producao_id = tipo.id
            producao.status_producao_id = status_prod.id
            producao.nome = payload.nome
            producao.data_recebimento = to_date(payload.data_recebimento)
            producao.data_conclusao = to_date(payload.data_conclusao)
            producao.quantidade_alunos = to_int(payload.quantidade_alunos, 0)
            producao.pasta_producao = payload.pasta_producao or None
            producao.relatorio = payload.relatorio or None
            producao.valor_total = novo_valor_total
            self._sync_items(session, producao, self.totals_calculator.build_item_inputs(payload))
            self._refresh_payment_projection(session, [production_id])
            session.flush()

            updated = self.sessions.base_producao_query(session).filter(Producao.id == production_id).one_or_none()
            return self.mapper.production_from_orm(updated) if updated else None

    def delete_many(self, production_ids: list[int]) -> int:
        if not production_ids:
            return 0
        with self.sessions.session_scope() as session:
            impacted_allocations = session.execute(
                select(
                    AlocacaoRecebimento.recebimento_id,
                    func.coalesce(func.sum(AlocacaoRecebimento.valor_alocado), 0),
                )
                .where(AlocacaoRecebimento.producao_id.in_(production_ids))
                .group_by(AlocacaoRecebimento.recebimento_id)
            ).all()
            for receipt_id, value in impacted_allocations:
                receipt = session.get(RecebimentoCliente, receipt_id)
                if receipt is None:
                    continue
                receipt.valor_nao_alocado = _decimal_or_zero(receipt.valor_nao_alocado) + _decimal_or_zero(value)

            count = session.query(Producao).filter(Producao.id.in_(production_ids)).count()
            session.query(Producao).filter(Producao.id.in_(production_ids)).delete(synchronize_session=False)
            return int(count)

    def get_by_id(self, production_id: int) -> Production | None:
        with self.sessions.session_scope() as session:
            producao = self.sessions.base_producao_query(session).filter(Producao.id == production_id).one_or_none()
            return self.mapper.production_from_orm(producao) if producao else None

    def list_all(self, filters: ProductionFilters) -> list[Production]:
        with self.sessions.session_scope() as session:
            query = self.sessions.base_producao_query(session)
            query = self.sessions.apply_producao_filters(query, filters)
            query = query.order_by(Producao.data_recebimento.desc(), Producao.id.desc())
            return [self.mapper.production_from_orm(row) for row in query.all()]

    def list_page(self, filters: ProductionFilters, *, page: int, page_size: int) -> ProductionPage:
        current_page = max(1, int(page or 1))
        per_page = max(1, int(page_size or 100))
        with self.sessions.session_scope() as session:
            count_query = session.query(func.count(Producao.id))
            count_query = self.sessions.apply_producao_filters(count_query, filters)
            total = int(count_query.scalar() or 0)

            query = self.sessions.base_producao_query(session)
            query = self.sessions.apply_producao_filters(query, filters)
            query = query.order_by(Producao.data_recebimento.desc(), Producao.id.desc())
            query = query.offset((current_page - 1) * per_page).limit(per_page)
            items = [self.mapper.production_from_orm(row) for row in query.all()]
            return ProductionPage(items=items, total=total, page=current_page, page_size=per_page)

    def list_open_by_client(self, cliente: str) -> list[Production]:
        with self.sessions.session_scope() as session:
            query = self.sessions.base_producao_query(session)
            query = query.join(Producao.cliente).filter(Cliente.nome == cliente)
            query = query.join(Producao.status_pagamento).filter(StatusPagamento.nome.in_(tuple(OPEN_PAYMENT_STATUSES)))
            query = query.order_by(Producao.data_recebimento.desc(), Producao.id.desc())
            return [self.mapper.production_from_orm(row) for row in query.all()]

    @staticmethod
    def _sync_items(session, producao: Producao, item_inputs: list[ProductionItemInput]) -> None:
        producao.itens.clear()
        for item_input in item_inputs:
            session.add(
                ItemProducao(
                    producao_id=producao.id,
                    tipo_item=item_input.tipo_item,
                    quantidade=item_input.quantidade,
                    valor_unitario=item_input.valor_unitario,
                    valor_total=item_input.valor_total,
                )
            )


class SqliteReferenceRepository:
    def __init__(self, sessions: SqliteSessionFactory) -> None:
        self.sessions = sessions

    def add_tipo(self, nome: str) -> bool:
        nome = (nome or "").strip()
        if not nome:
            return False
        with self.sessions.session_scope() as session:
            existing = session.execute(select(TipoProducao).where(TipoProducao.nome == nome)).scalar_one_or_none()
            if existing:
                return False
            session.add(TipoProducao(nome=nome))
            return True

    def remove_tipo(self, nome: str) -> bool:
        with self.sessions.session_scope() as session:
            existing = session.execute(select(TipoProducao).where(TipoProducao.nome == nome)).scalar_one_or_none()
            if not existing:
                return False
            session.delete(existing)
            return True

    def list_tipos(self) -> list[str]:
        with self.sessions.session_scope() as session:
            return list(session.execute(select(TipoProducao.nome).order_by(TipoProducao.nome)).scalars().all())

    def list_clientes(self) -> list[str]:
        with self.sessions.session_scope() as session:
            clientes = session.execute(select(func.distinct(Cliente.nome)).order_by(Cliente.nome)).scalars().all()
            return [cliente for cliente in clientes if cliente]

    def list_anos(self) -> list[int]:
        with self.sessions.session_scope() as session:
            anos = (
                session.execute(
                    select(func.distinct(func.strftime("%Y", Producao.data_recebimento)))
                    .where(Producao.data_recebimento.isnot(None))
                    .order_by(func.strftime("%Y", Producao.data_recebimento).desc())
                )
                .scalars()
                .all()
            )
            result = []
            for ano in anos:
                try:
                    result.append(int(ano))
                except (TypeError, ValueError):
                    continue
            return result


class SqliteFinancialReadRepository:
    def __init__(self, sessions: SqliteSessionFactory) -> None:
        self.sessions = sessions

    def get_financial_summary(self, *, ano: int | None = None, cliente: str | None = None) -> FinancialSummary:
        with self.sessions.session_scope() as session:
            query = select(func.sum(Producao.valor_total), func.count(Producao.id))
            if ano:
                start, end = year_date_range(int(ano))
                query = query.where(and_(Producao.data_recebimento >= start, Producao.data_recebimento < end))
            if cliente:
                query = query.join(Producao.cliente).where(Cliente.nome == cliente)
            total, quantidade = session.execute(query).one()
            return FinancialSummary(total=float(total or 0.0), quantidade=int(quantidade or 0))

    def get_financial_periods(self, filters: ProductionFilters) -> list[FinancialPeriod]:
        with self.sessions.session_scope() as session:
            query = select(
                func.strftime("%Y", Producao.data_recebimento).label("ano"),
                func.strftime("%m", Producao.data_recebimento).label("mes"),
                func.strftime("%Y-%m-01", Producao.data_recebimento).label("data"),
                func.sum(Producao.valor_total).label("valor_total"),
                func.count(Producao.id).label("quantidade"),
            ).where(Producao.data_recebimento.isnot(None))

            if filters.cliente:
                query = query.join(Producao.cliente).where(Cliente.nome == filters.cliente)
            if filters.tipo_producao:
                query = query.join(Producao.tipo_producao).where(TipoProducao.nome == filters.tipo_producao)
            if filters.status_pagamento:
                query = query.join(Producao.status_pagamento).where(StatusPagamento.nome == filters.status_pagamento)
            if filters.ano and filters.mes:
                start, end = month_date_range(int(filters.ano), int(filters.mes))
                query = query.where(and_(Producao.data_recebimento >= start, Producao.data_recebimento < end))
            elif filters.ano:
                start, end = year_date_range(int(filters.ano))
                query = query.where(and_(Producao.data_recebimento >= start, Producao.data_recebimento < end))
            elif filters.mes:
                query = query.where(func.strftime("%m", Producao.data_recebimento) == f"{int(filters.mes):02d}")

            query = query.group_by("ano", "mes").order_by("ano", "mes")
            rows = session.execute(query).all()
            result: list[FinancialPeriod] = []
            for ano, mes, data_str, valor_total, quantidade in rows:
                if not ano or not mes:
                    continue
                try:
                    result.append(
                        FinancialPeriod(
                            ano=int(ano),
                            mes=int(mes),
                            data=data_str,
                            valor_total=float(valor_total or 0.0),
                            quantidade=int(quantidade or 0),
                        )
                    )
                except (TypeError, ValueError):
                    continue
            return result


class SqliteClientFinanceRepository(_SqlitePaymentProjectionMixin):
    def __init__(self, sessions: SqliteSessionFactory, mapper: SqliteOrmMapper | None = None) -> None:
        self.sessions = sessions
        self.mapper = mapper or SqliteOrmMapper()

    def list_client_summaries(self) -> list[ClientSummary]:
        with self.sessions.session_scope() as session:
            clients = session.execute(select(Cliente).order_by(Cliente.nome)).scalars().all()
            return [self._build_client_summary(session, client) for client in clients]

    def get_client_detail(self, client_id: int) -> ClientDetail | None:
        with self.sessions.session_scope() as session:
            client = session.get(Cliente, client_id)
            if client is None:
                return None

            producoes = self.sessions.base_producao_query(session).filter(Producao.cliente_id == client_id)
            producoes = producoes.order_by(Producao.data_recebimento.desc(), Producao.id.desc()).all()
            receipts = (
                session.execute(
                    select(RecebimentoCliente)
                    .options(
                        joinedload(RecebimentoCliente.cliente),
                        joinedload(RecebimentoCliente.alocacoes).joinedload(AlocacaoRecebimento.producao),
                    )
                    .where(RecebimentoCliente.cliente_id == client_id)
                    .order_by(RecebimentoCliente.data_recebimento.desc(), RecebimentoCliente.id.desc())
                )
                .unique()
                .scalars()
                .all()
            )

            return ClientDetail(
                summary=self._build_client_summary(session, client),
                productions=[self.mapper.production_from_orm(producao) for producao in producoes],
                open_balances=self._build_open_balances(session, client_id),
                receipts=[self._receipt_from_orm(receipt) for receipt in receipts],
            )

    def suggest_receipt_allocations(self, client_id: int, valor_total: float) -> list[ReceiptAllocation]:
        remaining = _decimal_or_zero(valor_total)
        with self.sessions.session_scope() as session:
            return self._suggest_receipt_allocations(session, client_id, remaining)

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
        valor_recebimento = _decimal_or_zero(valor_total)
        if valor_recebimento <= ZERO:
            raise ValueError("O valor do recebimento deve ser maior que zero.")

        with self.sessions.session_scope() as session:
            client = session.get(Cliente, client_id)
            if client is None:
                raise ValueError("Cliente não encontrado.")

            receipt = RecebimentoCliente(
                cliente_id=client_id,
                data_recebimento=to_date(data_recebimento),
                valor_total=valor_recebimento,
                valor_nao_alocado=valor_recebimento,
                forma_pagamento=(forma_pagamento or "").strip() or None,
                observacao=(observacao or "").strip() or None,
                origem="MANUAL",
            )
            session.add(receipt)
            session.flush()

            normalized_allocations = self._normalize_allocations(
                session,
                client_id=client_id,
                valor_total=valor_recebimento,
                allocations=allocations,
                auto_allocate=auto_allocate,
            )
            affected_production_ids: list[int] = []
            total_allocated = ZERO
            for allocation in normalized_allocations:
                if allocation.valor_alocado <= ZERO:
                    continue
                value = _decimal_or_zero(allocation.valor_alocado)
                session.add(
                    AlocacaoRecebimento(
                        recebimento_id=receipt.id,
                        producao_id=allocation.production_id,
                        valor_alocado=value,
                    )
                )
                total_allocated += value
                affected_production_ids.append(allocation.production_id)

            if total_allocated > valor_recebimento:
                raise ValueError("A soma das alocações não pode exceder o valor do recebimento.")

            receipt.valor_nao_alocado = valor_recebimento - total_allocated
            self._refresh_payment_projection(session, affected_production_ids)
            session.flush()

            stored_receipt = (
                session.execute(
                    select(RecebimentoCliente)
                    .options(
                        joinedload(RecebimentoCliente.cliente),
                        joinedload(RecebimentoCliente.alocacoes).joinedload(AlocacaoRecebimento.producao),
                    )
                    .where(RecebimentoCliente.id == receipt.id)
                )
                .unique()
                .scalar_one()
            )
            return self._receipt_from_orm(stored_receipt)

    def _build_client_summary(self, session, client: Cliente) -> ClientSummary:
        producoes = self.sessions.base_producao_query(session).filter(Producao.cliente_id == client.id).all()
        mapped_producoes = [self.mapper.production_from_orm(producao) for producao in producoes]
        receipts = session.execute(
            select(RecebimentoCliente).where(RecebimentoCliente.cliente_id == client.id)
        ).scalars().all()

        valor_contratado = sum(producao.valor_total for producao in mapped_producoes)
        valor_recebido = sum(producao.valor_recebido for producao in mapped_producoes)
        credito = sum(float(_decimal_or_zero(receipt.valor_nao_alocado)) for receipt in receipts)
        saldo = max(valor_contratado - valor_recebido, 0.0)

        return ClientSummary(
            client_id=client.id,
            cliente=client.nome,
            total_productions=len(mapped_producoes),
            open_productions=sum(
                1 for producao in mapped_producoes if producao.status_pagamento in OPEN_PAYMENT_STATUSES
            ),
            in_progress_productions=sum(1 for producao in mapped_producoes if producao.status == "Em Andamento"),
            valor_contratado=valor_contratado,
            valor_recebido=valor_recebido,
            saldo=saldo,
            credito=credito,
        )

    def _normalize_allocations(
        self,
        session,
        *,
        client_id: int,
        valor_total: Decimal,
        allocations: list[ReceiptAllocationRequest],
        auto_allocate: bool,
    ) -> list[ReceiptAllocationRequest]:
        if auto_allocate:
            return [
                ReceiptAllocationRequest(
                    production_id=suggestion.production_id,
                    valor_alocado=suggestion.valor_alocado,
                )
                for suggestion in self._suggest_receipt_allocations(session, client_id, valor_total)
            ]

        available_balances = {
            balance.production_id: _decimal_or_zero(balance.saldo)
            for balance in self._build_open_balances(session, client_id)
        }
        normalized: dict[int, Decimal] = {}
        for allocation in allocations:
            value = _decimal_or_zero(allocation.valor_alocado)
            if value <= ZERO:
                continue
            if allocation.production_id not in available_balances:
                raise ValueError("Uma das produções selecionadas não está disponível para alocação.")
            normalized[allocation.production_id] = normalized.get(allocation.production_id, ZERO) + value

        total_allocated = sum(normalized.values(), ZERO)
        if total_allocated > valor_total:
            raise ValueError("A soma das alocações não pode exceder o valor do recebimento.")

        for production_id, value in normalized.items():
            saldo = available_balances[production_id]
            if value > saldo:
                raise ValueError("Uma das alocações excede o saldo disponível da produção.")

        return [
            ReceiptAllocationRequest(production_id=production_id, valor_alocado=float(value))
            for production_id, value in normalized.items()
        ]

    def _suggest_receipt_allocations(self, session, client_id: int, valor_total: Decimal) -> list[ReceiptAllocation]:
        remaining = _decimal_or_zero(valor_total)
        balances = self._build_open_balances(session, client_id)
        suggestions: list[ReceiptAllocation] = []
        for balance in balances:
            if remaining <= ZERO:
                break
            saldo = _decimal_or_zero(balance.saldo)
            if saldo <= ZERO:
                continue
            valor_alocado = min(remaining, saldo)
            if valor_alocado <= ZERO:
                continue
            suggestions.append(
                ReceiptAllocation(
                    id=0,
                    receipt_id=0,
                    production_id=balance.production_id,
                    valor_alocado=float(valor_alocado),
                    production_name=balance.nome,
                    production_code=balance.codigo,
                )
            )
            remaining -= valor_alocado
        return suggestions
