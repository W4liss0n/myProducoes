"""Fachada pública para geração de relatórios PDF.

As implementações foram movidas para ``src.core.pdf`` para reduzir acoplamento.
"""
from __future__ import annotations

from .pdf.reports import NumberedCanvas, PDFGenerator

__all__ = ["PDFGenerator", "NumberedCanvas"]
