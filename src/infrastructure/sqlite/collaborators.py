from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from ...config.constants import DEFAULT_STATUS_OPTIONS, DEFAULT_STATUS_PAGAMENTO_OPTIONS
from ...domain.models import ProductionPayload

DEFAULT_TIPO_PREFIXOS = {
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
STATUS_PAGAMENTO_ORDEM = {"Em aberto": 1, "Parcial": 2, "Pago": 3}


def to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (ArithmeticError, ValueError):
        return None


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True, slots=True)
class ProductionItemInput:
    tipo_item: str
    quantidade: int
    valor_unitario: Decimal | None
    valor_total: Decimal | None


@dataclass(frozen=True, slots=True)
class CodeSequenceContext:
    prefixo: str
    ano: str

    @property
    def like_pattern(self) -> str:
        return f"{self.prefixo}-{self.ano}-%"


class StatusCanonicalizer:
    def __init__(
        self,
        *,
        production_statuses: tuple[str, ...] = tuple(DEFAULT_STATUS_OPTIONS),
        payment_statuses: tuple[str, ...] = tuple(DEFAULT_STATUS_PAGAMENTO_OPTIONS),
    ) -> None:
        self._production_statuses = production_statuses
        self._payment_statuses = payment_statuses

    def production_status(self, value: str) -> str:
        return self._canonicalize(value, self._production_statuses, "Status de produção")

    def payment_status(self, value: str) -> str:
        return self._canonicalize(value, self._payment_statuses, "Status de pagamento")

    @staticmethod
    def _canonicalize(value: str, allowed_values: tuple[str, ...], field_name: str) -> str:
        normalized = (value or "").strip()
        if not normalized:
            raise ValueError(f"{field_name} é obrigatório.")
        for allowed in allowed_values:
            if normalized.casefold() == allowed.casefold():
                return allowed
        allowed_text = ", ".join(allowed_values)
        raise ValueError(f"{field_name} inválido: '{value}'. Valores válidos: {allowed_text}.")


class ProductionTotalsCalculator:
    def calculate_total(self, payload: ProductionPayload) -> Decimal:
        total = Decimal("0.0")
        for quantity, unit_value in self._line_items(payload):
            if quantity <= 0:
                continue
            total += (unit_value or Decimal("0.0")) * quantity
        return total

    def build_item_inputs(self, payload: ProductionPayload) -> list[ProductionItemInput]:
        item_specs = (
            ("FOTO", payload.quantidade_fotos, payload.valor_por_foto),
            ("KIT", payload.quantidade_kits, payload.valor_por_kit),
            ("CAPA", payload.quantidade_capas, payload.valor_por_capa),
        )
        items: list[ProductionItemInput] = []
        for tipo_item, quantity_raw, unit_value_raw in item_specs:
            quantity = to_int(quantity_raw, 0)
            if quantity <= 0:
                continue
            unit_value = to_decimal(unit_value_raw)
            items.append(
                ProductionItemInput(
                    tipo_item=tipo_item,
                    quantidade=quantity,
                    valor_unitario=unit_value,
                    valor_total=(unit_value * quantity) if unit_value is not None else None,
                )
            )
        return items

    @staticmethod
    def _line_items(payload: ProductionPayload) -> tuple[tuple[int, Decimal | None], ...]:
        return (
            (to_int(payload.quantidade_fotos, 0), to_decimal(payload.valor_por_foto)),
            (to_int(payload.quantidade_kits, 0), to_decimal(payload.valor_por_kit)),
            (to_int(payload.quantidade_capas, 0), to_decimal(payload.valor_por_capa)),
        )


class ProductionCodeGenerator:
    def __init__(self, *, prefixes: dict[str, str] | None = None) -> None:
        self._prefixes = prefixes or DEFAULT_TIPO_PREFIXOS.copy()

    def sequence_context(
        self,
        tipo_producao: str,
        data_recebimento: date | None,
        *,
        current_year: int | None = None,
    ) -> CodeSequenceContext:
        prefixo = self._prefixes.get(tipo_producao, "PROD")
        year = str(data_recebimento.year) if data_recebimento else str(current_year or datetime.now().year)
        return CodeSequenceContext(prefixo=prefixo, ano=year)

    @staticmethod
    def build_code(context: CodeSequenceContext, last_code: str | None) -> str:
        nova_seq = 1
        if last_code and isinstance(last_code, str):
            try:
                nova_seq = int(last_code.split("-")[-1]) + 1
            except Exception:
                nova_seq = 1
        return f"{context.prefixo}-{context.ano}-{nova_seq:03d}"
