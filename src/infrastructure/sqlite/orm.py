from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy.sql import func

from ...config.constants import DATABASE_FILE


class Base(DeclarativeBase):
    """Base declarativa para os modelos ORM."""


def get_engine(db_path: Path | str | None = None, *, echo: bool = False):
    path = Path(db_path or DATABASE_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}", echo=echo, future=True)

    if engine.url.get_backend_name() == "sqlite":

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


_default_engine = get_engine()
SessionLocal = sessionmaker(bind=_default_engine, expire_on_commit=False, future=True)


def get_session(db_path: Path | str | None = None):
    if db_path:
        engine = get_engine(db_path)
        Session = sessionmaker(bind=engine, expire_on_commit=False, future=True)
        return Session()
    return SessionLocal()


def create_all_tables(db_path: Path | str | None = None, *, echo: bool = False):
    engine = get_engine(db_path, echo=echo)
    Base.metadata.create_all(engine)
    return engine


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    documento: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=False)
    contato: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    telefone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    endereco: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    producoes: Mapped[List["Producao"]] = relationship(back_populates="cliente")
    recebimentos: Mapped[List["RecebimentoCliente"]] = relationship(
        back_populates="cliente",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class TipoProducao(Base):
    __tablename__ = "tipos_producao"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    producoes: Mapped[List["Producao"]] = relationship(back_populates="tipo_producao")


class StatusProducao(Base):
    __tablename__ = "status_producao"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    producoes: Mapped[List["Producao"]] = relationship(back_populates="status_producao")


class StatusPagamento(Base):
    __tablename__ = "status_pagamento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    producoes: Mapped[List["Producao"]] = relationship(back_populates="status_pagamento")


class Producao(Base):
    __tablename__ = "producoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[Optional[str]] = mapped_column(String(50), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(255))
    data_recebimento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    data_conclusao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    quantidade_alunos: Mapped[int] = mapped_column(Integer, default=0)
    pasta_producao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    relatorio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    valor_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), nullable=False)
    tipo_producao_id: Mapped[int] = mapped_column(ForeignKey("tipos_producao.id"), nullable=False)
    status_producao_id: Mapped[int] = mapped_column(ForeignKey("status_producao.id"), nullable=False)
    status_pagamento_id: Mapped[int] = mapped_column(ForeignKey("status_pagamento.id"), nullable=False)

    cliente: Mapped["Cliente"] = relationship(back_populates="producoes")
    tipo_producao: Mapped["TipoProducao"] = relationship(back_populates="producoes")
    status_producao: Mapped["StatusProducao"] = relationship(back_populates="producoes")
    status_pagamento: Mapped["StatusPagamento"] = relationship(back_populates="producoes")

    itens: Mapped[List["ItemProducao"]] = relationship(
        back_populates="producao", cascade="all, delete-orphan", passive_deletes=True
    )
    pagamentos: Mapped[List["PagamentoProducao"]] = relationship(
        back_populates="producao", cascade="all, delete-orphan", passive_deletes=True
    )
    alocacoes: Mapped[List["AlocacaoRecebimento"]] = relationship(
        back_populates="producao", cascade="all, delete-orphan", passive_deletes=True
    )


class RecebimentoCliente(Base):
    __tablename__ = "recebimentos_cliente"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    data_recebimento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    valor_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    valor_nao_alocado: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    forma_pagamento: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    observacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    origem: Mapped[str] = mapped_column(String(50), nullable=False, default="MANUAL")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    cliente: Mapped["Cliente"] = relationship(back_populates="recebimentos")
    alocacoes: Mapped[List["AlocacaoRecebimento"]] = relationship(
        back_populates="recebimento",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AlocacaoRecebimento(Base):
    __tablename__ = "alocacoes_recebimento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recebimento_id: Mapped[int] = mapped_column(
        ForeignKey("recebimentos_cliente.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    producao_id: Mapped[int] = mapped_column(
        ForeignKey("producoes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    valor_alocado: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    recebimento: Mapped["RecebimentoCliente"] = relationship(back_populates="alocacoes")
    producao: Mapped["Producao"] = relationship(back_populates="alocacoes")


class ItemProducao(Base):
    __tablename__ = "itens_producao"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    producao_id: Mapped[int] = mapped_column(
        ForeignKey("producoes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo_item: Mapped[str] = mapped_column(String(50))
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quantidade: Mapped[int] = mapped_column(Integer, default=0)
    valor_unitario: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    valor_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    producao: Mapped["Producao"] = relationship(back_populates="itens")


class PagamentoProducao(Base):
    __tablename__ = "pagamentos_producao"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    producao_id: Mapped[int] = mapped_column(
        ForeignKey("producoes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    data_pagamento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    valor: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    forma_pagamento: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    observacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    producao: Mapped["Producao"] = relationship(back_populates="pagamentos")


class Configuracao(Base):
    __tablename__ = "configuracoes"

    chave: Mapped[str] = mapped_column(String(100), primary_key=True)
    valor: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
