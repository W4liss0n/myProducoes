from __future__ import annotations

from typing import List

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics


def apply_line_breaks(data: List[List], col_widths: List[float], styles, font_size_body: int = 11) -> List[List]:
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=font_size_body,
        textColor=colors.black,
        fontName='Helvetica',
        alignment=TA_CENTER,
        leading=font_size_body * 1.2,
    )

    processed_data = []
    for row_idx, row in enumerate(data):
        processed_row = []
        for col_idx, cell in enumerate(row):
            if row_idx == 0:
                processed_row.append(cell)
                continue

            value = '' if cell is None else str(cell)
            cell_width = col_widths[col_idx]
            text_width = pdfmetrics.stringWidth(value, 'Helvetica', font_size_body)
            if text_width > (cell_width * 0.90):
                processed_row.append(Paragraph(value, cell_style))
            else:
                processed_row.append(cell)
        processed_data.append(processed_row)
    return processed_data


def calculate_column_widths(
    data: List[List[str]],
    largura_disponivel: float,
    incluir_capas: bool = True,
    font_size_header: int = 12,
    font_size_body: int = 11,
) -> List[float]:
    if incluir_capas:
        min_widths = [20 * mm, 28 * mm, 15 * mm, 15 * mm, 40 * mm]
    else:
        min_widths = [20 * mm, 28 * mm, 15 * mm, 40 * mm]

    num_cols = len(data[0])
    max_widths = [0] * num_cols

    for row_idx, row in enumerate(data):
        for col_idx, cell in enumerate(row):
            cell_text = '' if cell is None else str(cell)
            font_size = font_size_header if row_idx == 0 else font_size_body
            font_name_used = 'Helvetica-Bold' if row_idx == 0 else 'Helvetica'
            text_width = pdfmetrics.stringWidth(cell_text, font_name_used, font_size) + 12 * mm
            if text_width > max_widths[col_idx]:
                max_widths[col_idx] = text_width

    for i in range(num_cols):
        if max_widths[i] < min_widths[i]:
            max_widths[i] = min_widths[i]

    if incluir_capas:
        max_widths[1] = min(max_widths[1], min_widths[1] * 1.2)
        max_widths[2] = min(max_widths[2], min_widths[2] * 1.2)
        max_widths[3] = min(max_widths[3], min_widths[3] * 1.2)
        fixed_widths = max_widths[1] + max_widths[2] + max_widths[3]
        remaining = largura_disponivel - fixed_widths
        id_needed = max_widths[0]
        curso_needed = max_widths[4]
        total_needed = id_needed + curso_needed
        if total_needed > 0:
            ratio_id = id_needed / total_needed
            ratio_curso = curso_needed / total_needed
        else:
            ratio_id = 0.25
            ratio_curso = 0.75
        max_widths[0] = remaining * ratio_id
        max_widths[4] = remaining * ratio_curso
    else:
        max_widths[1] = min(max_widths[1], min_widths[1] * 1.2)
        max_widths[2] = min(max_widths[2], min_widths[2] * 1.2)
        fixed_widths = max_widths[1] + max_widths[2]
        remaining = largura_disponivel - fixed_widths
        id_needed = max_widths[0]
        curso_needed = max_widths[3]
        total_needed = id_needed + curso_needed
        if total_needed > 0:
            ratio_id = id_needed / total_needed
            ratio_curso = curso_needed / total_needed
        else:
            ratio_id = 0.25
            ratio_curso = 0.75
        max_widths[0] = remaining * ratio_id
        max_widths[3] = remaining * ratio_curso

    return max_widths
