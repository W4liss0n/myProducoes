from __future__ import annotations

from pathlib import Path

from ...core.pdf_generator import PDFGenerator
from ...core.services.production_folder_analyzer import ProductionFolderAnalyzer
from ...core.services.production_report_service import ProductionReportService
from ...domain.models import FolderInspection, Production, StudentReportRow


class FileSystemFolderInspectionGateway:
    def __init__(self, analyzer: ProductionFolderAnalyzer | None = None) -> None:
        self._service = analyzer or ProductionFolderAnalyzer()

    def inspect(self, folder_path: str) -> FolderInspection:
        total_fotos, total_alunos, total_kits = self._service.calculate_totals(folder_path)
        return FolderInspection(total_fotos=total_fotos, total_alunos=total_alunos, total_kits=total_kits)

    def extract_students(self, folder_path: str) -> list[StudentReportRow]:
        rows = self._service.extract_students(folder_path)
        return [
            StudentReportRow(
                id=row["id"],
                fotos=row["fotos"],
                kits=row["kits"],
                capas=row.get("capas", 0),
                curso=row.get("curso", ""),
            )
            for row in rows
        ]


class ReportLabReportGenerationGateway:
    def __init__(self) -> None:
        self._service = ProductionReportService()

    @staticmethod
    def _open_report_amount(producao: Production) -> float:
        saldo = float(producao.saldo or 0.0)
        if saldo > 0:
            return saldo

        valor_total = float(producao.valor_total or 0.0)
        valor_recebido = float(producao.valor_recebido or 0.0)
        return max(valor_total - valor_recebido, 0.0)

    def generate_production_report(
        self,
        *,
        folder_path: str,
        output_path: Path,
        production_name: str,
        company: str,
        include_covers: bool = True,
    ) -> bool:
        ok, _ = self._service.generate_from_folder(
            pasta_producao=folder_path,
            arquivo_pdf=output_path,
            nome_producao=production_name,
            empresa=company,
            incluir_capas=include_covers,
        )
        return ok

    def generate_open_productions_report(
        self,
        *,
        output_path: Path,
        cliente: str,
        producoes: list[Production],
    ) -> bool:
        pdf_generator = PDFGenerator()
        legacy_rows = [
            {
                "Código": producao.codigo or "",
                "Cliente": producao.cliente,
                "Data de Recebimento": producao.data_recebimento.isoformat() if producao.data_recebimento else "",
                "Nome": producao.nome,
                "Tipo de Produção": producao.tipo_producao,
                "Quant. Alunos": producao.quantidade_alunos,
                "Quant. Fotos": producao.quantidade_fotos,
                "Quant. Kits": producao.quantidade_kits,
                "Quant. Capas": producao.quantidade_capas,
                "Valor por Foto": float(producao.valor_por_foto or 0.0),
                "Valor por Kit": float(producao.valor_por_kit or 0.0),
                "Valor por Capa": float(producao.valor_por_capa or 0.0),
                "Valor Total": self._open_report_amount(producao),
                "Data de Conclusão": producao.data_conclusao.isoformat() if producao.data_conclusao else "",
                "Status Pagamento": producao.status_pagamento,
                "Status": producao.status,
                "Relatório": producao.relatorio,
                "Pasta Produção": producao.pasta_producao,
            }
            for producao in producoes
        ]
        return pdf_generator.gerar_relatorio_producoes_aberto(
            file_path=output_path,
            cliente=cliente,
            producoes=legacy_rows,
        )
