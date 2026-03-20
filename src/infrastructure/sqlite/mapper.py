from __future__ import annotations

from decimal import Decimal
from typing import Any

from ...domain.models import Production
from .orm import Producao


class SqliteOrmMapper:
    @staticmethod
    def _derive_payment_status(valor_total: Decimal, valor_recebido: Decimal) -> str:
        if valor_recebido <= Decimal("0") and valor_total > Decimal("0"):
            return "Em aberto"
        if valor_recebido < valor_total:
            return "Parcial"
        return "Pago"

    @staticmethod
    def _to_decimal(value: Any) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (ArithmeticError, ValueError):
            return None

    @staticmethod
    def _to_int(value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def production_from_orm(producao: Producao) -> Production:
        quantities: dict[str, int] = {"FOTO": 0, "KIT": 0, "CAPA": 0}
        unit_values: dict[str, Decimal | None] = {"FOTO": None, "KIT": None, "CAPA": None}
        totals: dict[str, Decimal] = {"FOTO": Decimal("0"), "KIT": Decimal("0"), "CAPA": Decimal("0")}

        for item in producao.itens:
            tipo = (item.tipo_item or "").upper()
            if tipo not in quantities:
                continue

            quantidade = SqliteOrmMapper._to_int(item.quantidade)
            quantities[tipo] += quantidade
            unit = SqliteOrmMapper._to_decimal(item.valor_unitario)
            if unit is None and item.valor_total is not None and quantidade:
                try:
                    total_value = SqliteOrmMapper._to_decimal(item.valor_total)
                    unit = total_value / Decimal(quantidade) if total_value is not None else None
                except (ArithmeticError, ValueError, ZeroDivisionError):
                    unit = None
            if unit is not None:
                unit_values[tipo] = unit
            total_value = SqliteOrmMapper._to_decimal(item.valor_total)
            if total_value is not None:
                totals[tipo] += total_value

        valor_total = SqliteOrmMapper._to_decimal(producao.valor_total)
        if valor_total is None:
            valor_total = sum(totals.values(), Decimal("0"))
        valor_recebido = sum(
            (
                SqliteOrmMapper._to_decimal(alocacao.valor_alocado) or Decimal("0")
                for alocacao in getattr(producao, "alocacoes", [])
            ),
            Decimal("0"),
        )
        saldo = valor_total - valor_recebido
        status_pagamento = SqliteOrmMapper._derive_payment_status(valor_total, valor_recebido)

        return Production(
            id=producao.id,
            codigo=producao.codigo or "",
            cliente=producao.cliente.nome if producao.cliente else "",
            data_recebimento=producao.data_recebimento,
            nome=producao.nome,
            tipo_producao=producao.tipo_producao.nome if producao.tipo_producao else "",
            quantidade_alunos=SqliteOrmMapper._to_int(producao.quantidade_alunos),
            quantidade_fotos=quantities["FOTO"],
            quantidade_kits=quantities["KIT"],
            quantidade_capas=quantities["CAPA"],
            valor_por_foto=float(unit_values["FOTO"] or Decimal("0")),
            valor_por_kit=float(unit_values["KIT"] or Decimal("0")),
            valor_por_capa=float(unit_values["CAPA"] or Decimal("0")),
            valor_total=float(valor_total or 0.0),
            data_conclusao=producao.data_conclusao,
            status_pagamento=status_pagamento,
            status=producao.status_producao.nome if producao.status_producao else "",
            relatorio=producao.relatorio or "",
            pasta_producao=producao.pasta_producao or "",
            valor_recebido=float(valor_recebido or 0.0),
            saldo=float(saldo or 0.0),
        )
