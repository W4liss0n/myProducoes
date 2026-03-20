# -*- coding: utf-8 -*-
"""
Diálogo principal de configurações.
"""

from typing import Callable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout


class SettingsDialog(QDialog):
    def __init__(
        self,
        parent=None,
        on_manage_types=None,
        on_configure_pix=None,
        on_configure_columns=None,
        on_manual_backup: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)
        self.on_manage_types = on_manage_types
        self.on_configure_pix = on_configure_pix
        self.on_configure_columns = on_configure_columns
        self.on_manual_backup = on_manual_backup
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Configurações Gerais")
        self.setFixedSize(480, 280)

        layout = QVBoxLayout(self)
        title = QLabel("Configurações do Sistema")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addSpacing(20)

        for text, callback in (
            ("Gerenciar Tipos de Serviços", self.on_manage_types),
            ("Configurar PIX", self.on_configure_pix),
            ("Configurar Colunas Visíveis", self.on_configure_columns),
            ("Criar Backup Manual do Banco", self.on_manual_backup),
        ):
            button = QPushButton(text)
            button.setObjectName("secondaryButton")
            button.clicked.connect(lambda _=False, cb=callback: cb() if cb else None)
            layout.addWidget(button)

        layout.addStretch()
        btn_close = QPushButton("Fechar")
        btn_close.setObjectName("primaryButton")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)
