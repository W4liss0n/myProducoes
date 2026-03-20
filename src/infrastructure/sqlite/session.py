from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy import and_, func, select
from sqlalchemy.orm import joinedload, sessionmaker

from ...config.constants import DATABASE_FILE
from ...domain.models import ProductionFilters
from .collaborators import STATUS_PAGAMENTO_ORDEM, STATUS_PRODUCAO_ORDEM
from .orm import (
    Cliente,
    Producao,
    SessionLocal,
    StatusPagamento,
    StatusProducao,
    TipoProducao,
    get_engine,
)


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def to_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def month_date_range(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        return start, date(year + 1, 1, 1)
    return start, date(year, month + 1, 1)


def year_date_range(year: int) -> tuple[date, date]:
    return date(year, 1, 1), date(year + 1, 1, 1)


class SqliteSessionFactory:
    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path or DATABASE_FILE)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if db_path:
            engine = get_engine(self.db_path)
            self.Session = sessionmaker(bind=engine, expire_on_commit=False, future=True)
        else:
            self.Session = SessionLocal

    @contextmanager
    def session_scope(self) -> Iterator:
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_or_create_cliente(self, session, nome: str) -> Cliente:
        nome = (nome or "").strip()
        if not nome:
            raise ValueError("Cliente é obrigatório.")
        obj = session.execute(select(Cliente).where(Cliente.nome == nome)).scalar_one_or_none()
        if obj:
            return obj
        obj = Cliente(nome=nome)
        session.add(obj)
        session.flush()
        return obj

    def get_or_create_tipo(self, session, nome: str) -> TipoProducao:
        nome = (nome or "").strip()
        if not nome:
            raise ValueError("Tipo de produção é obrigatório.")
        obj = session.execute(select(TipoProducao).where(TipoProducao.nome == nome)).scalar_one_or_none()
        if obj:
            return obj
        obj = TipoProducao(nome=nome)
        session.add(obj)
        session.flush()
        return obj

    def get_or_create_status_producao(self, session, nome: str) -> StatusProducao:
        obj = session.execute(
            select(StatusProducao).where(func.lower(StatusProducao.nome) == nome.lower())
        ).scalar_one_or_none()
        if obj:
            return obj
        obj = StatusProducao(nome=nome, ordem=STATUS_PRODUCAO_ORDEM.get(nome, 0), ativo=True)
        session.add(obj)
        session.flush()
        return obj

    def get_or_create_status_pagamento(self, session, nome: str) -> StatusPagamento:
        obj = session.execute(
            select(StatusPagamento).where(func.lower(StatusPagamento.nome) == nome.lower())
        ).scalar_one_or_none()
        if obj:
            return obj
        obj = StatusPagamento(nome=nome, ordem=STATUS_PAGAMENTO_ORDEM.get(nome, 0), ativo=True)
        session.add(obj)
        session.flush()
        return obj

    def base_producao_query(self, session):
        return session.query(Producao).options(
            joinedload(Producao.cliente),
            joinedload(Producao.tipo_producao),
            joinedload(Producao.status_producao),
            joinedload(Producao.status_pagamento),
            joinedload(Producao.itens),
            joinedload(Producao.alocacoes),
        )

    def apply_producao_filters(self, query, filters: ProductionFilters):
        if filters.cliente:
            query = query.join(Producao.cliente).filter(Cliente.nome == filters.cliente)
        if filters.tipo_producao:
            query = query.join(Producao.tipo_producao).filter(TipoProducao.nome == filters.tipo_producao)
        if filters.status:
            query = query.join(Producao.status_producao).filter(StatusProducao.nome == filters.status)
        if filters.status_pagamento:
            query = query.join(Producao.status_pagamento).filter(StatusPagamento.nome == filters.status_pagamento)
        if filters.ano and filters.mes:
            start, end = month_date_range(int(filters.ano), int(filters.mes))
            query = query.filter(and_(Producao.data_recebimento >= start, Producao.data_recebimento < end))
        elif filters.ano:
            start, end = year_date_range(int(filters.ano))
            query = query.filter(and_(Producao.data_recebimento >= start, Producao.data_recebimento < end))
        elif filters.mes:
            query = query.filter(func.strftime("%m", Producao.data_recebimento) == f"{int(filters.mes):02d}")
        return query

    def find_last_code(self, session, *, like_pattern: str) -> str | None:
        last_code = (
            session.execute(
                select(Producao.codigo)
                .where(Producao.codigo.like(like_pattern))
                .order_by(Producao.codigo.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        return str(last_code) if last_code else None
