# -*- coding: utf-8 -*-
"""
Gerador de PDF usando ReportLab
Substitui o uso de FPDF por uma biblioteca mais robusta e profissional
"""
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from natsort import os_sorted
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .pix import generate_qr_code_pix
from .styles import create_custom_styles
from .table_layout import apply_line_breaks, calculate_column_widths

logger = logging.getLogger(__name__)

OPEN_REPORT_MONTH_NAMES = (
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)
OPEN_REPORT_EMPTY_DATE_LABEL = "Sem data definida"
OPEN_REPORT_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y")
PAGE_NUMBER_MIN_Y = 0.6 * cm
PAGE_NUMBER_MAX_Y = 1.0 * cm
PAGE_NUMBER_BOTTOM_CLEARANCE = 0.35 * cm


def _parse_open_report_reference_date(data_conclusao: Any) -> date | None:
    if data_conclusao in (None, "", "None", "nan", "N/A"):
        return None

    if isinstance(data_conclusao, datetime):
        return data_conclusao.date()

    if isinstance(data_conclusao, date):
        return data_conclusao

    if isinstance(data_conclusao, str):
        date_part = data_conclusao.split()[0] if " " in data_conclusao else data_conclusao
        logger.debug("  -> Parseando data string: '%s'", date_part)

        for formato in OPEN_REPORT_DATE_FORMATS:
            try:
                return datetime.strptime(date_part, formato).date()
            except ValueError:
                continue

        raise ValueError(f"Nenhum formato de data reconhecido para: {date_part}")

    raise TypeError(f"Tipo de data não suportado: {type(data_conclusao)!r}")


def _build_open_report_month_groups(producoes: List[Dict[str, Any]]) -> list[tuple[str, List[Dict[str, Any]]]]:
    grouped_productions: dict[tuple[int, int], list[Dict[str, Any]]] = {}
    group_labels: dict[tuple[int, int], str] = {}
    undated_productions: list[Dict[str, Any]] = []

    for producao in producoes:
        data_conclusao = producao.get("Data de Conclusão", "")
        nome_producao = producao.get("Nome", "Sem nome")

        logger.debug(
            "Processando produção: %s, Data conclusão: '%s' (tipo: %s)",
            nome_producao,
            data_conclusao,
            type(data_conclusao),
        )

        try:
            reference_date = _parse_open_report_reference_date(data_conclusao)
        except Exception as exc:
            logger.warning("  -> ERRO ao parsear data de '%s': %s", nome_producao, exc)
            undated_productions.append(producao)
            continue

        if reference_date is None:
            logger.debug("  -> Data vazia ou inválida, adicionando a '%s'", OPEN_REPORT_EMPTY_DATE_LABEL)
            undated_productions.append(producao)
            continue

        group_key = (reference_date.year, reference_date.month)
        group_labels[group_key] = f"{OPEN_REPORT_MONTH_NAMES[reference_date.month - 1]} de {reference_date.year}"
        logger.debug("  -> Mês/Ano identificado: %s", group_labels[group_key])
        grouped_productions.setdefault(group_key, []).append(producao)

    ordered_groups = [(group_labels[key], grouped_productions[key]) for key in sorted(grouped_productions)]
    if undated_productions:
        ordered_groups.append((OPEN_REPORT_EMPTY_DATE_LABEL, undated_productions))
    return ordered_groups


def _resolve_page_number_y(bottom_margin: float) -> float:
    return max(
        PAGE_NUMBER_MIN_Y,
        min(PAGE_NUMBER_MAX_Y, bottom_margin - PAGE_NUMBER_BOTTOM_CLEARANCE),
    )


class PDFGenerator:
    """Gerador de PDFs profissionais para relatórios de produção"""

    def __init__(self, empresa: str = ""):
        """
        Inicializa o gerador de PDF com estilos padrão

        Args:
            empresa: Nome da empresa para o cabeçalho (opcional)
        """
        self.empresa = empresa
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()

    def _create_custom_styles(self):
        """Cria estilos personalizados para o PDF."""
        create_custom_styles(self.styles)

    def gerar_relatorio_individual(
        self,
        file_path: Path,
        empresa: str,
        nome_producao: str,
        dados_tabela: List[Dict[str, Any]],
        totais: Dict[str, int]
    ) -> bool:
        """
        Gera um relatório PDF individual para uma produção

        Args:
            file_path: Caminho onde o PDF será salvo
            empresa: Nome da empresa/cliente
            nome_producao: Nome da produção
            dados_tabela: Lista de dicionários com os dados da tabela
            totais: Dicionário com os totais (albuns, fotos, kits, capas)

        Returns:
            True se gerado com sucesso, False caso contrário
        """
        try:
            # Criar o documento
            doc = SimpleDocTemplate(
                str(file_path),
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )

            # Container para os elementos do PDF
            story = []

            # Cabeçalho
            story.append(Paragraph(f"<b>Empresa:</b> {empresa.upper()}", self.styles['CustomTitle']))
            story.append(Paragraph(f"<b>Produção:</b> {nome_producao}", self.styles['CustomSubtitle']))
            story.append(Spacer(1, 15))

            # Tabela de dados
            if dados_tabela:
                # Verificar se há capas nos dados
                tem_capas = any(item.get('Quant. Capas', 0) > 0 for item in dados_tabela)

                # Ordenar dados por curso usando os_sorted (ordenação estilo sistema operacional)
                dados_tabela_ordenados = os_sorted(
                    dados_tabela,
                    key=lambda x: str(x.get('Curso', ''))
                )

                # Cabeçalhos da tabela - incluir Capas apenas se houver
                if tem_capas:
                    headers = ["ID", "Quant. Fotos", "Kits", "Capas", "Curso"]
                else:
                    headers = ["ID", "Quant. Fotos", "Kits", "Curso"]

                # Dados da tabela
                table_data = [headers]
                for item in dados_tabela_ordenados:
                    if tem_capas:
                        row = [
                            str(item.get('ID', '')),
                            str(item.get('Quant. Fotos', 0)),
                            str(item.get('Quant. Kits', 0)),
                            str(item.get('Quant. Capas', 0)),
                            str(item.get('Curso', ''))
                        ]
                    else:
                        row = [
                            str(item.get('ID', '')),
                            str(item.get('Quant. Fotos', 0)),
                            str(item.get('Quant. Kits', 0)),
                            str(item.get('Curso', ''))
                        ]
                    table_data.append(row)

                # Calcular largura disponível
                largura_disponivel = A4[0] - 4*cm  # Margens de 2cm de cada lado

                # Calcular larguras dinâmicas (usando os mesmos font sizes do estilo da tabela)
                col_widths = self._calcular_larguras_colunas(
                    table_data,
                    largura_disponivel,
                    incluir_capas=tem_capas,
                    font_size_header=11,
                    font_size_body=9
                )

                # Aplicar quebra de linha em casos excepcionais
                table_data = self._aplicar_quebra_linha_excepcionais(table_data, col_widths, font_size_body=9)

                # Criar tabela com larguras calculadas
                table = Table(table_data, colWidths=col_widths, repeatRows=1)

                # Estilizar tabela
                table.setStyle(TableStyle([
                    # Cabeçalho
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a4a4a')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 11),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

                    # Corpo da tabela
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),

                    # Bordas
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dddddd')),
                    ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#4a4a4a')),

                    # Padding
                    ('TOPPADDING', (0, 1), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                ]))

                story.append(table)
                story.append(Spacer(1, 20))

            # Seção de totais
            totals_data = []
            totals_data.append(['Total de Álbuns:', str(totais.get('albuns', 0))])
            totals_data.append(['Total de Fotos:', str(totais.get('fotos', 0))])

            if totais.get('kits', 0) > 0:
                totals_data.append(['Total de Kits:', str(totais.get('kits', 0))])

            if totais.get('capas', 0) > 0:
                totals_data.append(['Total de Capas:', str(totais.get('capas', 0))])

            # Tabela de totais
            totals_table = Table(totals_data, colWidths=[8*cm, 8*cm])
            totals_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#1a252f')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#34495e')),
            ]))

            story.append(totals_table)

            # Gerar o PDF
            doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)

            logger.info(f"Relatório PDF individual gerado: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Erro ao gerar relatório PDF: {e}", exc_info=True)
            return False

    def gerar_relatorio_producao(
        self,
        arquivo_saida: str,
        nome_producao: str,
        alunos: List[Dict[str, Any]],
        incluir_capas: bool = True
    ) -> bool:
        """
        Gera relatório de produção em PDF (compatibilidade com código antigo)

        Args:
            arquivo_saida: Caminho do arquivo PDF a ser gerado
            nome_producao: Nome da produção
            alunos: Lista de dicionários com dados dos alunos
                    [{'id': 'ID', 'fotos': int, 'kits': int, 'curso': str}, ...]
            incluir_capas: Se deve incluir coluna de Capas

        Returns:
            True se gerado com sucesso, False caso contrário
        """
        try:
            # Criar documento PDF
            doc = SimpleDocTemplate(
                arquivo_saida,
                pagesize=A4,
                rightMargin=10*mm,
                leftMargin=10*mm,
                topMargin=10*mm,
                bottomMargin=10*mm
            )

            # Container para elementos
            elements = []

            # Estilo para cabeçalho Empresa
            empresa_style = ParagraphStyle(
                'EmpresaStyle',
                parent=self.styles['Normal'],
                fontSize=14,
                textColor=colors.black,
                spaceAfter=6,
                alignment=TA_LEFT,
                fontName='Helvetica-Bold',
                leftIndent=0
            )

            # Estilo para Produção
            producao_style = ParagraphStyle(
                'ProducaoStyle',
                parent=self.styles['Normal'],
                fontSize=14,
                textColor=colors.black,
                spaceAfter=20,
                alignment=TA_LEFT,
                fontName='Helvetica-Bold',
                leftIndent=0
            )

            # Cabeçalho
            if self.empresa:
                elements.append(Paragraph(f"<b>Empresa: {self.empresa}</b>", empresa_style))
            elements.append(Paragraph(f"<b>Produção: {nome_producao}</b>", producao_style))

            # Calcular largura total disponível
            largura_disponivel = A4[0] - 20*mm  # Largura A4 menos margens laterais (10mm cada)

            # Verificar se há capas para incluir na tabela
            tem_capas = any(aluno.get('capas', 0) > 0 for aluno in alunos)

            # Se incluir_capas for True, mas não há capas, desabilitar
            if incluir_capas and not tem_capas:
                incluir_capas = False

            # Preparar dados da tabela
            if incluir_capas:
                headers = ['ID', 'Quant. Fotos', 'Kits', 'Capas', 'Curso']
            else:
                headers = ['ID', 'Quant. Fotos', 'Kits', 'Curso']

            data = [headers]

            # Ordenar alunos por curso usando os_sorted
            alunos_ordenados = os_sorted(
                alunos,
                key=lambda x: str(x.get('curso', ''))
            )

            # Adicionar dados dos alunos
            total_fotos = 0
            total_kits = 0
            total_capas = 0

            for aluno in alunos_ordenados:
                fotos = aluno.get('fotos', 0)
                kits = aluno.get('kits', 0)
                capas = aluno.get('capas', 0)

                total_fotos += fotos
                total_kits += kits
                total_capas += capas

                if incluir_capas:
                    row = [
                        str(aluno.get('id', '')),
                        str(fotos),
                        str(kits),
                        str(capas),
                        aluno.get('curso', '')
                    ]
                else:
                    row = [
                        str(aluno.get('id', '')),
                        str(fotos),
                        str(kits),
                        aluno.get('curso', '')
                    ]

                data.append(row)

            # Calcular larguras dinâmicas baseadas no conteúdo (usando os mesmos font sizes do estilo da tabela)
            col_widths = self._calcular_larguras_colunas(
                data,
                largura_disponivel,
                incluir_capas,
                font_size_header=12,
                font_size_body=11
            )

            # Aplicar quebra de linha em casos excepcionais
            data = self._aplicar_quebra_linha_excepcionais(data, col_widths, font_size_body=11)

            # Criar tabela com larguras calculadas
            table = Table(data, colWidths=col_widths)

            # Estilo da tabela
            table_style = [
                # Cabeçalho
                ('BACKGROUND', (0, 0), (-1, 0), colors.white),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),

                # Corpo da tabela
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 11),
                ('ALIGN', (0, 1), (-1, -1), 'CENTER'),  # Todas as colunas centralizadas
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),

                # Bordas (mais finas)
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

                # Linhas alternadas
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]

            table.setStyle(TableStyle(table_style))
            elements.append(table)

            # Espaço antes do rodapé
            elements.append(Spacer(1, 10*mm))

            # Criar rodapé com fundo preto
            total_alunos = len(alunos)

            rodape_style = ParagraphStyle(
                'RodapeStyle',
                parent=self.styles['Normal'],
                fontSize=12,
                textColor=colors.white,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                leading=18
            )

            # Tabela para o rodapé (para ter fundo preto)
            if incluir_capas:
                rodape_text = f"""
                <para align=center>
                <b>Total de Álbuns: {total_alunos}</b><br/>
                <b>Total de Fotos: {total_fotos}</b><br/>
                <b>Total de Kits: {total_kits}</b><br/>
                <b>Total de Capas: {total_capas}</b>
                </para>
                """
            else:
                rodape_text = f"""
                <para align=center>
                <b>Total de Álbuns: {total_alunos}</b><br/>
                <b>Total de Fotos: {total_fotos}</b><br/>
                <b>Total de Kits: {total_kits}</b>
                </para>
                """

            rodape_para = Paragraph(rodape_text, rodape_style)
            # Usar a mesma largura da tabela principal
            rodape_table = Table([[rodape_para]], colWidths=[largura_disponivel])
            rodape_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.black),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ]))

            elements.append(rodape_table)

            # Construir PDF
            doc.build(elements)

            logger.info(f"PDF gerado com sucesso: {arquivo_saida}")
            return True

        except Exception as e:
            logger.error(f"Erro ao gerar PDF: {e}", exc_info=True)
            return False

    def gerar_relatorio_consolidado(
        self,
        file_path: Path,
        titulo: str,
        producoes: List[Dict[str, Any]],
        incluir_pix: bool = False,
        dados_pix: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Gera um relatório consolidado com múltiplas produções

        Args:
            file_path: Caminho onde o PDF será salvo
            titulo: Título do relatório
            producoes: Lista de produções a incluir
            incluir_pix: Se deve incluir QR Code PIX
            dados_pix: Dados do PIX (chave, nome, cidade)

        Returns:
            True se gerado com sucesso
        """
        try:
            doc = SimpleDocTemplate(
                str(file_path),
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )

            story = []

            # Título
            story.append(Paragraph(titulo, self.styles['CustomTitle']))
            story.append(Paragraph(
                f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
                self.styles['HeaderText']
            ))
            story.append(Spacer(1, 20))

            # Tabela de produções
            headers = ['Cliente', 'Produção', 'Tipo', 'Valor', 'Status']
            table_data = [headers]

            total_geral = 0.0

            for prod in producoes:
                row = [
                    prod.get('Cliente', ''),
                    prod.get('Nome', ''),
                    prod.get('Tipo de Produção', ''),
                    f"R$ {prod.get('Valor Total', 0):.2f}",
                    prod.get('Status', '')
                ]
                table_data.append(row)
                total_geral += prod.get('Valor Total', 0)

            # Linha de total
            table_data.append(['', '', 'TOTAL:', f"R$ {total_geral:.2f}", ''])

            table = Table(table_data, repeatRows=1)
            table.setStyle(TableStyle([
                # Cabeçalho
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),

                # Corpo
                ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -2), 9),
                ('ALIGN', (3, 1), (3, -1), 'RIGHT'),  # Alinhar valores à direita
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f9f9f9')]),

                # Linha de total
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#27ae60')),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 11),
                ('ALIGN', (2, -1), (3, -1), 'CENTER'),

                # Bordas
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#2c3e50')),
            ]))

            story.append(table)

            # Incluir PIX se solicitado
            if incluir_pix and dados_pix:
                story.append(PageBreak())
                story.append(Paragraph("Pagamento via PIX", self.styles['CustomSubtitle']))
                story.append(Spacer(1, 10))

                # Gerar QR Code
                qr_img = self._gerar_qr_code_pix(dados_pix, total_geral)
                if qr_img:
                    story.append(qr_img)
                    story.append(Spacer(1, 10))

                # Informações do PIX
                pix_info = f"""
                <b>Chave PIX:</b> {dados_pix.get('chave_pix', '')}<br/>
                <b>Beneficiário:</b> {dados_pix.get('nome_beneficiario', '')}<br/>
                <b>Cidade:</b> {dados_pix.get('cidade', '')}<br/>
                <b>Valor:</b> R$ {total_geral:.2f}
                """
                story.append(Paragraph(pix_info, self.styles['CustomNormal']))

            # Gerar PDF
            doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)

            logger.info(f"Relatório consolidado gerado: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Erro ao gerar relatório consolidado: {e}", exc_info=True)
            return False

    def _gerar_qr_code_pix(self, dados_pix: Dict[str, str], valor: float) -> Optional[Image]:
        """Gera QR Code PIX delegando para helper especializado."""
        return generate_qr_code_pix(dados_pix, valor, logger)

    def gerar_relatorio_producoes_aberto(
        self,
        file_path: Path,
        cliente: str,
        producoes: List[Dict[str, Any]]
    ) -> bool:
        """
        Gera relatório de produções em aberto por cliente

        Args:
            file_path: Caminho onde o PDF será salvo
            cliente: Nome do cliente
            producoes: Lista de produções em aberto do cliente

        Returns:
            True se gerado com sucesso
        """
        try:
            import locale
            import logging

            # Ativar log DEBUG temporariamente
            current_logger = logging.getLogger(__name__)
            current_logger.setLevel(logging.DEBUG)

            # Tentar configurar locale para português
            try:
                locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")
            except locale.Error:
                try:
                    locale.setlocale(locale.LC_TIME, "Portuguese_Brazil.1252")
                except locale.Error:
                    pass  # Usar locale padrão se não conseguir

            # FORMATO VERTICAL (A4 retrato) com margens reduzidas
            doc = SimpleDocTemplate(
                str(file_path),
                pagesize=A4,
                rightMargin=1*cm,
                leftMargin=1*cm,
                topMargin=1*cm,
                bottomMargin=1.2*cm
            )

            story = []

            # Título principal centralizado
            story.append(Paragraph("Relatório de Produções em Aberto", self.styles['CustomTitle']))
            story.append(Spacer(1, 20))

            # Informações do cabeçalho - inline e em negrito
            header_info = f"""
            <b>Clientes:</b> {cliente} | <b>Data de Geração:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}
            """
            story.append(Paragraph(header_info, self.styles['HeaderText']))
            story.append(Spacer(1, 22))

            # Calcular totais para o resumo
            total_producoes = len(producoes)
            total_alunos = sum(p.get('Quant. Alunos', 0) for p in producoes)
            total_fotos = sum(p.get('Quant. Fotos', 0) for p in producoes)

            # BOX DE RESUMO GERAL
            resumo_data = [
                ['RESUMO GERAL'],
                [f'Escolas: {total_producoes} | Alunos: {total_alunos:,}'.replace(',', '.') +
                 f' | Fotos: {total_fotos:,}'.replace(',', '.')]
            ]

            largura_resumo = A4[0] - 2*cm
            resumo_table = Table(resumo_data, colWidths=[largura_resumo])
            resumo_table.setStyle(TableStyle([
                # Título do resumo
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),

                # Dados do resumo
                ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#ecf0f1')),
                ('TEXTCOLOR', (0, 1), (-1, 1), colors.black),
                ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 1), (-1, 1), 10),
                ('TOPPADDING', (0, 1), (-1, 1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, 1), 8),

                # Bordas
                ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#2c3e50')),
            ]))

            story.append(resumo_table)
            story.append(Spacer(1, 25))

            producoes_agrupadas = _build_open_report_month_groups(producoes)

            total_geral = 0.0

            # Para cada mês, criar uma tabela
            for index, (mes_ano, producoes_mes) in enumerate(producoes_agrupadas):

                # Criar elementos do mês para manter juntos
                mes_elements = []

                # Título do mês (alinhado à esquerda)
                mes_elements.append(Paragraph(
                    f"<b>Mês Referência (Conclusão): {mes_ano}</b>",
                    self.styles['CustomSubtitle']
                ))
                mes_elements.append(Spacer(1, 10))

                # Cabeçalhos da tabela (sem Capas, com abreviações)
                headers = [
                    'Nome', 'Alunos', 'Fotos', 'Kits',
                    'V. Foto', 'V. Kit', 'Total'
                ]

                table_data = [headers]
                total_mes = 0.0

                # Adicionar dados das produções
                for producao in producoes_mes:
                    valor_total_formatado = (
                        f"R$ {producao.get('Valor Total', 0):,.2f}"
                        .replace(",", "X")
                        .replace(".", ",")
                        .replace("X", ".")
                    )
                    row = [
                        str(producao.get('Nome', '')),
                        str(producao.get('Quant. Alunos', 0)),
                        str(producao.get('Quant. Fotos', 0)),
                        str(producao.get('Quant. Kits', 0)),
                        f"R$ {producao.get('Valor por Foto', 0):.2f}".replace('.', ','),
                        f"R$ {producao.get('Valor por Kit', 0):.2f}".replace('.', ','),
                        valor_total_formatado,
                    ]
                    table_data.append(row)
                    total_mes += producao.get('Valor Total', 0)

                # Linha de total do mês
                total_row = ['', '', '', '', '', 'Total:',
                           f"R$ {total_mes:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')]
                table_data.append(total_row)

                # Calcular largura disponível (A4 vertical - margens)
                largura_disponivel = A4[0] - 2*cm  # 2cm total de margens (1cm + 1cm)

                # Larguras otimizadas para formato vertical
                col_widths = [
                    5.5*cm,  # Nome
                    1.4*cm,  # Alunos
                    1.4*cm,  # Fotos
                    1.2*cm,  # Kits
                    1.6*cm,  # V. Foto
                    1.6*cm,  # V. Kit
                    2.3*cm,  # Total
                ]

                # Ajustar proporcionalmente se necessário
                largura_usada = sum(col_widths)
                if largura_usada < largura_disponivel:
                    fator = largura_disponivel / largura_usada
                    col_widths = [w * fator for w in col_widths]

                # Criar tabela com larguras definidas
                table = Table(table_data, colWidths=col_widths, repeatRows=1)

                # Estilizar tabela com zebra striping
                table.setStyle(TableStyle([
                    # Cabeçalho
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a4a4a')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),  # Reduzido para formato vertical
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                    ('TOPPADDING', (0, 0), (-1, 0), 10),

                    # Corpo da tabela - ZEBRA STRIPING
                    ('BACKGROUND', (0, 1), (-1, -2), colors.white),
                    ('TEXTCOLOR', (0, 1), (-1, -2), colors.black),
                    ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -2), 8),  # Reduzido para formato vertical
                    ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f5f5f5')]),
                    ('ALIGN', (1, 1), (-1, -1), 'CENTER'),  # Números centralizados
                    ('ALIGN', (0, 1), (0, -1), 'LEFT'),  # Nome à esquerda
                    ('VALIGN', (0, 1), (-1, -2), 'MIDDLE'),
                    ('TOPPADDING', (0, 1), (-1, -2), 8),
                    ('BOTTOMPADDING', (0, 1), (-1, -2), 8),
                    ('LEFTPADDING', (0, 1), (-1, -2), 6),
                    ('RIGHTPADDING', (0, 1), (-1, -2), 6),

                    # Linha de total do mês
                    ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#4a4a4a')),
                    ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, -1), (-1, -1), 10),
                    ('ALIGN', (0, -1), (-1, -1), 'RIGHT'),
                    ('VALIGN', (0, -1), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, -1), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, -1), (-1, -1), 10),

                    # Bordas internas do corpo (cinza claro)
                    ('INNERGRID', (0, 1), (-1, -2), 1, colors.HexColor('#dddddd')),

                    # Bordas do cabeçalho
                    ('INNERGRID', (0, 0), (-1, 0), 1, colors.HexColor('#4a4a4a')),
                    ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#4a4a4a')),

                    # Bordas da linha de total
                    ('INNERGRID', (0, -1), (-1, -1), 1, colors.HexColor('#4a4a4a')),
                    ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#4a4a4a')),

                    # Borda externa
                    ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#4a4a4a')),
                ]))

                # Adicionar tabela aos elementos do mês
                mes_elements.append(table)

                # Usar KeepTogether para manter título e tabela na mesma página
                story.append(KeepTogether(mes_elements))
                if index < len(producoes_agrupadas) - 1:
                    story.append(Spacer(1, 25))

                total_geral += total_mes

            # Total geral (alinhado à direita)
            total_geral_text = (
                f'<para align="right" fontSize="13">'
                f"<b>Valor Total Geral em Aberto: R$ {total_geral:,.2f}</b>"
                f"</para>"
            ).replace(",", "X").replace(".", ",").replace("X", ".")

            story.append(Spacer(1, 8))
            story.append(Paragraph(total_geral_text, self.styles["CustomNormal"]))

            # Gerar PDF
            doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)

            logger.info(f"Relatório de produções em aberto gerado: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Erro ao gerar relatório de produções em aberto: {e}", exc_info=True)
            return False

    def _aplicar_quebra_linha_excepcionais(
        self,
        data: List[List],
        col_widths: List[float],
        font_size_body: int = 11
    ) -> List[List]:
        """Aplica quebra de linha delegando para helper de layout de tabela."""
        return apply_line_breaks(data, col_widths, self.styles, font_size_body)

    def _calcular_larguras_colunas(
        self,
        data: List[List[str]],
        largura_disponivel: float,
        incluir_capas: bool = True,
        font_size_header: int = 12,
        font_size_body: int = 11
    ) -> List[float]:
        """Calcula larguras dinâmicas delegando para helper de layout."""
        return calculate_column_widths(
            data,
            largura_disponivel,
            incluir_capas,
            font_size_header,
            font_size_body,
        )

    def _add_page_number(self, canvas_obj, doc):
        """
        Adiciona número de página ao rodapé

        Args:
            canvas_obj: Canvas do ReportLab
            doc: Documento
        """
        canvas_obj.saveState()
        canvas_obj.setFont('Helvetica', 9)
        page_number_text = f"Página {doc.page}"
        page_number_y = _resolve_page_number_y(doc.bottomMargin)
        # Usar a largura da página atual do documento
        canvas_obj.drawCentredString(
            doc.pagesize[0] / 2,
            page_number_y,
            page_number_text
        )
        canvas_obj.restoreState()


class NumberedCanvas(canvas.Canvas):
    """Canvas customizado com numeração de páginas"""

    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.setFont("Helvetica", 9)
        page_number_y = _resolve_page_number_y(2 * cm)
        self.drawRightString(
            A4[0] - 2 * cm,
            page_number_y,
            f"Página {self._pageNumber} de {page_count}"
        )
