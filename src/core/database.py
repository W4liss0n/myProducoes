from __future__ import annotations

import logging
import shutil
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload, sessionmaker

from ..config.constants import DATA_DIR, DATABASE_FILE
from .models import (
    Cliente,
    ItemProducao,
    Producao,
    StatusPagamento,
    StatusProducao,
    TipoProducao,
    get_engine,
    SessionLocal,
)

logger = logging.getLogger(__name__)

TIPO_PREFIXOS = {
    "Formatura": "FORM",
    "Separação": "SEP",
    "Completo": "COMP",
    "Edição": "EDIT",
    "Poster": "POST",
    "Foto Tela": "FTELA",
    "Newborn": "NEWB",
    "Casamento": "CASA",
}

STATUS_PRODUCAO_ORDEM = {"Parado": 1, "Em Andamento": 2, "Finalizado": 3}
STATUS_PAGAMENTO_ORDEM = {"Em aberto": 1, "Pago": 2}


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (ArithmeticError, ValueError):
        return None


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_date(value: Any) -> Optional[date]:
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


class DatabaseManager:
    """
    Implementação do gerenciador usando SQLAlchemy e o novo schema normalizado.
    Mantém a interface de dicionários usada pela UI.
    """

    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = Path(db_path or DATABASE_FILE)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        if db_path:
            engine = get_engine(self.db_path)
            self.Session = sessionmaker(bind=engine, expire_on_commit=False, future=True)
        else:
            self.Session = SessionLocal

    @contextmanager
    def _session_scope(self):
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ================================
    # Domínios
    # ================================
    def _get_or_create_cliente(self, session, nome: str) -> Cliente:
        nome = (nome or "").strip()
        obj = session.execute(select(Cliente).where(Cliente.nome == nome)).scalar_one_or_none()
        if obj:
            return obj
        obj = Cliente(nome=nome)
        session.add(obj)
        session.flush()
        return obj

    def _get_or_create_tipo(self, session, nome: str) -> TipoProducao:
        nome = (nome or "").strip()
        obj = session.execute(select(TipoProducao).where(TipoProducao.nome == nome)).scalar_one_or_none()
        if obj:
            return obj
        obj = TipoProducao(nome=nome)
        session.add(obj)
        session.flush()
        return obj

    def _get_or_create_status(self, session, nome: str) -> StatusProducao:
        nome = (nome or "").strip()
        obj = session.execute(select(StatusProducao).where(StatusProducao.nome == nome)).scalar_one_or_none()
        if obj:
            return obj
        ordem = STATUS_PRODUCAO_ORDEM.get(nome, 0)
        obj = StatusProducao(nome=nome, ordem=ordem)
        session.add(obj)
        session.flush()
        return obj

    def _get_or_create_status_pagamento(self, session, nome: str) -> StatusPagamento:
        nome = (nome or "").strip()
        obj = session.execute(select(StatusPagamento).where(StatusPagamento.nome == nome)).scalar_one_or_none()
        if obj:
            return obj
        ordem = STATUS_PAGAMENTO_ORDEM.get(nome, 0)
        obj = StatusPagamento(nome=nome, ordem=ordem)
        session.add(obj)
        session.flush()
        return obj

    # ================================
    # Produções
    # ================================
    def adicionar_producao(self, dados: Dict[str, Any]) -> int:
        with self._session_scope() as session:
            cliente = self._get_or_create_cliente(session, dados.get("cliente", ""))
            tipo = self._get_or_create_tipo(session, dados.get("tipo_producao", ""))
            status_prod = self._get_or_create_status(session, dados.get("status", "Parado"))
            status_pag = self._get_or_create_status_pagamento(session, dados.get("status_pagamento", "Em aberto"))

            data_recebimento = _to_date(dados.get("data_recebimento"))
            codigo = dados.get("codigo") or self._gerar_codigo(session, tipo.nome, data_recebimento)

            producao = Producao(
                codigo=codigo,
                nome=dados.get("nome", ""),
                data_recebimento=data_recebimento,
                data_conclusao=_to_date(dados.get("data_conclusao")),
                quantidade_alunos=_to_int(dados.get("quantidade_alunos", 0)),
                pasta_producao=dados.get("pasta_producao") or None,
                relatorio=dados.get("relatorio") or None,
                valor_total=self._calcular_valor_total(dados),
                cliente_id=cliente.id,
                tipo_producao_id=tipo.id,
                status_producao_id=status_prod.id,
                status_pagamento_id=status_pag.id,
            )

            session.add(producao)
            session.flush()
            self._sincronizar_itens(session, producao, dados)
            session.flush()
            return producao.id

    def atualizar_producao(self, producao_id: int, dados: Dict[str, Any]) -> bool:
        with self._session_scope() as session:
            producao = session.get(Producao, producao_id)
            if not producao:
                return False

            cliente = self._get_or_create_cliente(session, dados.get("cliente", ""))
            tipo = self._get_or_create_tipo(session, dados.get("tipo_producao", ""))
            status_prod = self._get_or_create_status(session, dados.get("status", "Parado"))
            status_pag = self._get_or_create_status_pagamento(session, dados.get("status_pagamento", "Em aberto"))

            producao.cliente_id = cliente.id
            producao.tipo_producao_id = tipo.id
            producao.status_producao_id = status_prod.id
            producao.status_pagamento_id = status_pag.id
            producao.nome = dados.get("nome", producao.nome)
            producao.data_recebimento = _to_date(dados.get("data_recebimento"))
            producao.data_conclusao = _to_date(dados.get("data_conclusao"))
            producao.quantidade_alunos = _to_int(dados.get("quantidade_alunos", 0))
            producao.pasta_producao = dados.get("pasta_producao") or None
            producao.relatorio = dados.get("relatorio") or None
            producao.valor_total = self._calcular_valor_total(dados)

            self._sincronizar_itens(session, producao, dados)
            session.flush()
            return True

    def remover_producoes(self, ids: List[int]) -> int:
        if not ids:
            return 0
        with self._session_scope() as session:
            count = (
                session.query(Producao)
                .filter(Producao.id.in_(ids))
                .delete(synchronize_session=False)
            )
            return count

    def obter_producao(self, producao_id: int) -> Optional[Dict[str, Any]]:
        with self._session_scope() as session:
            producao = (
                session.query(Producao)
                .options(
                    joinedload(Producao.cliente),
                    joinedload(Producao.tipo_producao),
                    joinedload(Producao.status_producao),
                    joinedload(Producao.status_pagamento),
                    joinedload(Producao.itens),
                )
                .filter(Producao.id == producao_id)
                .one_or_none()
            )
            if not producao:
                return None
            return self._row_to_dict(producao)

    def listar_producoes(self, filtros: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        with self._session_scope() as session:
            query = (
                session.query(Producao)
                .options(
                    joinedload(Producao.cliente),
                    joinedload(Producao.tipo_producao),
                    joinedload(Producao.status_producao),
                    joinedload(Producao.status_pagamento),
                    joinedload(Producao.itens),
                )
            )

            if filtros:
                cliente = filtros.get("cliente")
                if cliente:
                    query = query.join(Producao.cliente).filter(Cliente.nome == cliente)

                tipo = filtros.get("tipo_producao")
                if tipo:
                    query = query.join(Producao.tipo_producao).filter(TipoProducao.nome == tipo)

                status = filtros.get("status")
                if status:
                    query = query.join(Producao.status_producao).filter(StatusProducao.nome == status)

                status_pagamento = filtros.get("status_pagamento")
                if status_pagamento:
                    query = query.join(Producao.status_pagamento).filter(StatusPagamento.nome == status_pagamento)

            query = query.order_by(Producao.data_recebimento.desc().nullslast(), Producao.id.desc())
            producoes = query.all()
            return [self._row_to_dict(p) for p in producoes]

    # ================================
    # Tipos de Produção
    # ================================
    def adicionar_tipo_producao(self, nome: str) -> bool:
        with self._session_scope() as session:
            existing = session.execute(select(TipoProducao).where(TipoProducao.nome == nome)).scalar_one_or_none()
            if existing:
                return False
            session.add(TipoProducao(nome=nome.strip()))
            return True

    def remover_tipo_producao(self, nome: str) -> bool:
        with self._session_scope() as session:
            existing = session.execute(select(TipoProducao).where(TipoProducao.nome == nome)).scalar_one_or_none()
            if not existing:
                return False
            session.delete(existing)
            return True

    def listar_tipos_producao(self) -> List[str]:
        with self._session_scope() as session:
            tipos = session.execute(select(TipoProducao.nome).order_by(TipoProducao.nome)).scalars().all()
            return list(tipos)

    # ================================
    # Estatísticas e utilitários
    # ================================
    def obter_clientes_unicos(self) -> List[str]:
        with self._session_scope() as session:
            clientes = session.execute(select(func.distinct(Cliente.nome)).order_by(Cliente.nome)).scalars().all()
            return [c for c in clientes if c]

    def obter_resumo_financeiro(self, ano: Optional[int] = None, cliente: Optional[str] = None) -> Dict[str, Any]:
        with self._session_scope() as session:
            query = select(func.sum(Producao.valor_total), func.count(Producao.id))

            if ano:
                query = query.where(func.strftime("%Y", Producao.data_recebimento) == str(ano))
            if cliente:
                query = query.join(Producao.cliente).where(Cliente.nome == cliente)

            total, quantidade = session.execute(query).one()
            return {"total": float(total or 0.0), "quantidade": int(quantidade or 0)}

    def obter_dados_financeiros_por_periodo(self, filtros: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        with self._session_scope() as session:
            query = select(
                func.strftime("%Y", Producao.data_recebimento).label("ano"),
                func.strftime("%m", Producao.data_recebimento).label("mes"),
                func.strftime("%Y-%m-01", Producao.data_recebimento).label("data"),
                func.sum(Producao.valor_total).label("valor_total"),
                func.count(Producao.id).label("quantidade"),
            ).where(Producao.data_recebimento.isnot(None))

            if filtros:
                if filtros.get("cliente"):
                    query = query.join(Producao.cliente).where(Cliente.nome == filtros["cliente"])
                if filtros.get("ano"):
                    query = query.where(func.strftime("%Y", Producao.data_recebimento) == str(filtros["ano"]))
                if filtros.get("mes"):
                    query = query.where(func.strftime("%m", Producao.data_recebimento) == f"{filtros['mes']:02d}")
                if filtros.get("tipo_producao"):
                    query = query.join(Producao.tipo_producao).where(TipoProducao.nome == filtros["tipo_producao"])
                if filtros.get("status_pagamento"):
                    query = query.join(Producao.status_pagamento).where(
                        StatusPagamento.nome == filtros["status_pagamento"]
                    )

            query = query.group_by("ano", "mes").order_by("ano", "mes")
            rows = session.execute(query).all()
            resultados = []
            for ano, mes, data_str, valor_total, quantidade in rows:
                if not ano or not mes:
                    continue
                try:
                    resultados.append(
                        {
                            "ano": int(ano),
                            "mes": int(mes),
                            "data": data_str,
                            "valor_total": float(valor_total or 0.0),
                            "quantidade": int(quantidade or 0),
                        }
                    )
                except (TypeError, ValueError):
                    continue
            return resultados

    def obter_anos_disponiveis(self) -> List[int]:
        with self._session_scope() as session:
            anos = (
                session.execute(
                    select(func.distinct(func.strftime("%Y", Producao.data_recebimento)))
                    .where(Producao.data_recebimento.isnot(None))
                    .order_by(func.strftime("%Y", Producao.data_recebimento).desc())
                )
                .scalars()
                .all()
            )
            resultado = []
            for ano in anos:
                try:
                    resultado.append(int(ano))
                except (TypeError, ValueError):
                    continue
            return resultado

    def backup_database(self, backup_path: Path) -> bool:
        try:
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Backup do banco criado: {backup_path}")
            return True
        except Exception as exc:
            logger.error(f"Erro ao criar backup do banco: {exc}")
            return False

    # ================================
    # Auxiliares internos
    # ================================
    def _calcular_valor_total(self, dados: Dict[str, Any]) -> Optional[Decimal]:
        total = Decimal("0.0")
        q_fotos = _to_int(dados.get("quantidade_fotos", 0))
        q_kits = _to_int(dados.get("quantidade_kits", 0))
        q_capas = _to_int(dados.get("quantidade_capas", 0))

        if q_fotos:
            unit = _to_decimal(dados.get("valor_por_foto")) or Decimal("0.0")
            total += unit * q_fotos
        if q_kits:
            unit = _to_decimal(dados.get("valor_por_kit")) or Decimal("0.0")
            total += unit * q_kits
        if q_capas:
            unit = _to_decimal(dados.get("valor_por_capa")) or Decimal("0.0")
            total += unit * q_capas

        return total

    def _sincronizar_itens(self, session, producao: Producao, dados: Dict[str, Any]) -> None:
        producao.itens.clear()

        def add_item(tipo: str, quantidade: int, unitario: Optional[Decimal]):
            if quantidade <= 0:
                return
            valor_total = unitario * quantidade if unitario is not None else None
            item = ItemProducao(
                producao_id=producao.id,
                tipo_item=tipo,
                quantidade=quantidade,
                valor_unitario=unitario,
                valor_total=valor_total,
            )
            session.add(item)

        add_item("FOTO", _to_int(dados.get("quantidade_fotos", 0)), _to_decimal(dados.get("valor_por_foto")))
        add_item("KIT", _to_int(dados.get("quantidade_kits", 0)), _to_decimal(dados.get("valor_por_kit")))
        add_item("CAPA", _to_int(dados.get("quantidade_capas", 0)), _to_decimal(dados.get("valor_por_capa")))

    def _gerar_codigo(self, session, tipo_producao: str, data_recebimento: Optional[date]) -> str:
        prefixo = TIPO_PREFIXOS.get(tipo_producao, "PROD")
        ano = str(data_recebimento.year) if data_recebimento else str(datetime.now().year)

        like_pattern = f"{prefixo}-{ano}-%"
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

        nova_seq = 1
        if last_code and isinstance(last_code, str):
            try:
                nova_seq = int(last_code.split("-")[-1]) + 1
            except Exception:
                nova_seq = 1

        return f"{prefixo}-{ano}-{nova_seq:03d}"

    def _row_to_dict(self, producao: Producao) -> Dict[str, Any]:
        itens_info = {"FOTO": {"qtd": 0, "unit": None, "total": Decimal("0")},
                      "KIT": {"qtd": 0, "unit": None, "total": Decimal("0")},
                      "CAPA": {"qtd": 0, "unit": None, "total": Decimal("0")}}

        for item in producao.itens:
            tipo = (item.tipo_item or "").upper()
            if tipo not in itens_info:
                continue
            qtd = item.quantidade or 0
            itens_info[tipo]["qtd"] += qtd
            unit = item.valor_unitario
            if unit is None and item.valor_total is not None and qtd:
                try:
                    unit = Decimal(item.valor_total) / Decimal(qtd)
                except Exception:
                    unit = None
            if unit is not None:
                itens_info[tipo]["unit"] = unit
            if item.valor_total is not None:
                itens_info[tipo]["total"] += Decimal(item.valor_total)

        valor_total = producao.valor_total
        if valor_total is None:
            valor_total = sum((info["total"] for info in itens_info.values()), Decimal("0"))

        def fmt_date(d: Optional[date]) -> str:
            return d.isoformat() if d else ""

        return {
            "ID": producao.id,
            "Código": producao.codigo or "",
            "Cliente": producao.cliente.nome if producao.cliente else "",
            "Data de Recebimento": fmt_date(producao.data_recebimento),
            "Nome": producao.nome,
            "Tipo de Produção": producao.tipo_producao.nome if producao.tipo_producao else "",
            "Quant. Alunos": producao.quantidade_alunos or 0,
            "Quant. Fotos": itens_info["FOTO"]["qtd"],
            "Quant. Kits": itens_info["KIT"]["qtd"],
            "Quant. Capas": itens_info["CAPA"]["qtd"],
            "Valor por Foto": float(itens_info["FOTO"]["unit"]) if itens_info["FOTO"]["unit"] is not None else 0.0,
            "Valor por Kit": float(itens_info["KIT"]["unit"]) if itens_info["KIT"]["unit"] is not None else 0.0,
            "Valor por Capa": float(itens_info["CAPA"]["unit"]) if itens_info["CAPA"]["unit"] is not None else 0.0,
            "Valor Total": float(valor_total or 0.0),
            "Data de Conclusão": fmt_date(producao.data_conclusao),
            "Status Pagamento": producao.status_pagamento.nome if producao.status_pagamento else "",
            "Status": producao.status_producao.nome if producao.status_producao else "",
            "Relatório": producao.relatorio or "",
            "Pasta Produção": producao.pasta_producao or "",
        }
