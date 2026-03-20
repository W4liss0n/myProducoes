from __future__ import annotations

from pathlib import Path
from typing import Callable, Tuple

from ..pdf_generator import PDFGenerator
from .production_folder_analyzer import ProductionFolderAnalyzer


class ProductionReportService:
    """Orquestra extração de dados de pasta da produção e geração de PDF."""

    def __init__(
        self,
        analyzer: ProductionFolderAnalyzer | None = None,
        pdf_generator_factory: Callable[[str], PDFGenerator] | None = None,
    ) -> None:
        self.analyzer = analyzer or ProductionFolderAnalyzer()
        self._pdf_generator_factory = pdf_generator_factory or (lambda empresa: PDFGenerator(empresa=empresa))

    def calculate_totals(self, pasta_producao: str) -> tuple[int, int, int]:
        return self.analyzer.calculate_totals(pasta_producao)

    def extract_students(self, pasta_producao: str):
        return self.analyzer.extract_students(pasta_producao)

    def generate_from_folder(
        self,
        *,
        pasta_producao: str,
        arquivo_pdf: str | Path,
        nome_producao: str,
        empresa: str,
        incluir_capas: bool = True,
    ) -> Tuple[bool, int]:
        alunos = self.analyzer.extract_students(pasta_producao)
        if not alunos:
            return False, 0

        generator = self._pdf_generator_factory(empresa)
        ok = generator.gerar_relatorio_producao(
            arquivo_saida=str(arquivo_pdf),
            nome_producao=nome_producao,
            alunos=alunos,
            incluir_capas=incluir_capas,
        )
        return ok, len(alunos)
