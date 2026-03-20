from __future__ import annotations

from datetime import date

from ...domain.models import Production, ProductionPayload
from .types import ProductionFormData, ProductionTableRow


class ProductionPresentationMapper:
    @staticmethod
    def production_to_table_row(producao: Production) -> ProductionTableRow:
        return ProductionTableRow(
            production_id=producao.id,
            values={
                "ID": producao.id,
                "Código": producao.codigo or "",
                "Cliente": producao.cliente,
                "Data de Recebimento": ProductionPresentationMapper._fmt_date(producao.data_recebimento),
                "Nome": producao.nome,
                "Tipo de Produção": producao.tipo_producao,
                "Quant. Alunos": producao.quantidade_alunos,
                "Quant. Fotos": producao.quantidade_fotos,
                "Quant. Kits": producao.quantidade_kits,
                "Quant. Capas": producao.quantidade_capas,
                "Valor por Foto": float(producao.valor_por_foto or 0.0),
                "Valor por Kit": float(producao.valor_por_kit or 0.0),
                "Valor por Capa": float(producao.valor_por_capa or 0.0),
                "Valor Total": float(producao.valor_total or 0.0),
                "Data de Conclusão": ProductionPresentationMapper._fmt_date(producao.data_conclusao),
                "Status Pagamento": producao.status_pagamento,
                "Status": producao.status,
                "Relatório": producao.relatorio,
                "Pasta Produção": producao.pasta_producao,
            },
        )

    @staticmethod
    def production_to_form_data(producao: Production) -> ProductionFormData:
        return ProductionFormData(
            cliente=producao.cliente,
            nome=producao.nome,
            tipo_producao=producao.tipo_producao,
            data_recebimento=ProductionPresentationMapper._fmt_date(producao.data_recebimento),
            data_conclusao=ProductionPresentationMapper._fmt_date(producao.data_conclusao),
            status=producao.status,
            status_pagamento=producao.status_pagamento,
            quantidade_alunos=producao.quantidade_alunos,
            quantidade_fotos=producao.quantidade_fotos,
            quantidade_kits=producao.quantidade_kits,
            quantidade_capas=producao.quantidade_capas,
            valor_por_foto=float(producao.valor_por_foto or 0.0),
            valor_por_kit=float(producao.valor_por_kit or 0.0),
            valor_por_capa=float(producao.valor_por_capa or 0.0),
            valor_recebido=float(producao.valor_recebido or 0.0),
            saldo=float(producao.saldo or 0.0),
            pasta_producao=producao.pasta_producao,
            relatorio=producao.relatorio,
            codigo=producao.codigo or "",
        )

    @staticmethod
    def form_to_payload(dados: ProductionFormData) -> ProductionPayload:
        return ProductionPayload(
            cliente=dados.cliente,
            nome=dados.nome,
            tipo_producao=dados.tipo_producao,
            data_recebimento=ProductionPresentationMapper._normalize_date_input(dados.data_recebimento),
            data_conclusao=ProductionPresentationMapper._normalize_date_input(dados.data_conclusao),
            status=dados.status or "Parado",
            status_pagamento=dados.status_pagamento or "Em aberto",
            quantidade_alunos=ProductionPresentationMapper._to_int(dados.quantidade_alunos),
            quantidade_fotos=ProductionPresentationMapper._to_int(dados.quantidade_fotos),
            quantidade_kits=ProductionPresentationMapper._to_int(dados.quantidade_kits),
            quantidade_capas=ProductionPresentationMapper._to_int(dados.quantidade_capas),
            valor_por_foto=ProductionPresentationMapper._to_float(dados.valor_por_foto),
            valor_por_kit=ProductionPresentationMapper._to_float(dados.valor_por_kit),
            valor_por_capa=ProductionPresentationMapper._to_float(dados.valor_por_capa),
            pasta_producao=dados.pasta_producao,
            relatorio=dados.relatorio,
            codigo=dados.codigo,
        )

    @staticmethod
    def to_table_rows(producoes: list[Production]) -> list[ProductionTableRow]:
        return [ProductionPresentationMapper.production_to_table_row(producao) for producao in producoes]

    @staticmethod
    def open_report_label(producao: Production) -> str:
        data_conclusao = ProductionPresentationMapper._fmt_date(producao.data_conclusao) or "N/A"
        texto = (
            f"{producao.nome or 'Sem nome'} - "
            f"R$ {float(producao.valor_total or 0.0):,.2f} - "
            f"Conclusão: {data_conclusao}"
        )
        return texto.replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def sort_value_for_column(producao: Production, column_name: str):
        mapping = {
            "Código": producao.codigo or "",
            "Cliente": producao.cliente or "",
            "Data de Recebimento": producao.data_recebimento or date.max,
            "Nome": producao.nome or "",
            "Tipo de Produção": producao.tipo_producao or "",
            "Quant. Alunos": producao.quantidade_alunos,
            "Quant. Fotos": producao.quantidade_fotos,
            "Quant. Kits": producao.quantidade_kits,
            "Quant. Capas": producao.quantidade_capas,
            "Valor por Foto": producao.valor_por_foto,
            "Valor por Kit": producao.valor_por_kit,
            "Valor por Capa": producao.valor_por_capa,
            "Valor Total": producao.valor_total,
            "Data de Conclusão": producao.data_conclusao or date.max,
            "Status Pagamento": producao.status_pagamento or "",
            "Status": producao.status or "",
            "Relatório": producao.relatorio or "",
        }
        return mapping.get(column_name, "")

    @staticmethod
    def _fmt_date(value: date | None) -> str:
        return value.isoformat() if value else ""

    @staticmethod
    def _normalize_date_input(value: object) -> str | None:
        if value in (None, "", "None"):
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _to_int(value: object) -> int:
        try:
            if isinstance(value, bool):
                return int(value)
            if isinstance(value, (int, float, str)):
                return int(value)
            return 0
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _to_float(value: object) -> float:
        try:
            if isinstance(value, bool):
                return float(value)
            if isinstance(value, (int, float, str)):
                return float(value)
            return 0.0
        except (TypeError, ValueError):
            return 0.0
