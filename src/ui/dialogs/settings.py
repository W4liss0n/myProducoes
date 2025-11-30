# -*- coding: utf-8 -*-
"""
Diálogo de Configurações Gerais - PyQt6
"""
import logging
from typing import Callable, Optional

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt

from ..icons import Icons

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Diálogo principal de configurações"""

    def __init__(self, parent=None, on_manage_types=None, on_configure_pix=None, on_configure_columns=None):
        super().__init__(parent)
        self.on_manage_types = on_manage_types
        self.on_configure_pix = on_configure_pix
        self.on_configure_columns = on_configure_columns
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Configurações Gerais")
        self.setFixedSize(480, 220)

        layout = QVBoxLayout(self)

        # Título
        title = QLabel("Configurações do Sistema")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(20)

        # Botões
        btn_types = QPushButton("Gerenciar Tipos de Serviços")
        btn_types.setObjectName("secondaryButton")
        btn_types.clicked.connect(lambda: self.on_manage_types() if self.on_manage_types else None)
        layout.addWidget(btn_types)

        btn_pix = QPushButton("Configurar PIX")
        btn_pix.setObjectName("secondaryButton")
        btn_pix.clicked.connect(lambda: self.on_configure_pix() if self.on_configure_pix else None)
        layout.addWidget(btn_pix)

        btn_cols = QPushButton("Configurar Colunas Visíveis")
        btn_cols.setObjectName("secondaryButton")
        btn_cols.clicked.connect(lambda: self.on_configure_columns() if self.on_configure_columns else None)
        layout.addWidget(btn_cols)

        layout.addStretch()

        # Botão Fechar
        btn_close = QPushButton("Fechar")
        btn_close.setObjectName("primaryButton")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)
