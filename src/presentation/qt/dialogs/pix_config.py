# -*- coding: utf-8 -*-
"""
Diálogo para configurar dados do PIX.
"""

import logging
from typing import Callable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ..icons import Icons

logger = logging.getLogger(__name__)


class PixConfigDialog(QDialog):
    def __init__(
        self,
        parent=None,
        current_config: Optional[dict[str, str]] = None,
        on_save: Optional[Callable[[dict[str, str]], None]] = None,
    ):
        super().__init__(parent)
        self.current_config = current_config or {}
        self.on_save_callback = on_save
        self.entries: dict[str, QLineEdit] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Configurar Dados PIX")
        self.setFixedSize(500, 280)
        layout = QVBoxLayout(self)

        title = QLabel("Configuração PIX para Pagamentos")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addSpacing(10)

        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        for label_text, key, placeholder in (
            ("Nome do Beneficiário*:", "nome_beneficiario", "Ex: João da Silva"),
            ("Chave PIX (UUID)*:", "chave_pix", "UUID de 36 caracteres"),
            ("Cidade*:", "cidade", "Ex: São Paulo"),
        ):
            entry = QLineEdit()
            entry.setPlaceholderText(placeholder)
            current_value = self.current_config.get(key, "")
            if current_value:
                entry.setText(current_value)
            if key == "chave_pix":
                entry.setMaxLength(36)
            form_layout.addRow(label_text, entry)
            self.entries[key] = entry

        layout.addLayout(form_layout)
        layout.addSpacing(10)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        btn_save = QPushButton("Salvar")
        btn_save.setObjectName("primaryButton")
        btn_save.setIcon(Icons.save())
        btn_save.clicked.connect(self._save_config)
        button_layout.addWidget(btn_save)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("secondaryButton")
        btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancel)
        layout.addLayout(button_layout)

    def _save_config(self) -> None:
        try:
            config = {key: entry.text().strip() for key, entry in self.entries.items()}

            if not config.get("nome_beneficiario"):
                QMessageBox.warning(self, "Campo Obrigatório", "O nome do beneficiário é obrigatório!")
                return

            if not config.get("chave_pix"):
                QMessageBox.warning(self, "Campo Obrigatório", "A chave PIX é obrigatória!")
                return

            if not config.get("cidade"):
                QMessageBox.warning(self, "Campo Obrigatório", "A cidade é obrigatória!")
                return

            if len(config["chave_pix"]) != 36:
                QMessageBox.warning(
                    self,
                    "Chave PIX Inválida",
                    "A chave PIX deve ter exatamente 36 caracteres (formato UUID).",
                )
                return

            if self.on_save_callback:
                self.on_save_callback(config)

            QMessageBox.information(self, "Sucesso", "Configurações do PIX salvas com sucesso!")
            logger.info("Configuração PIX salva com sucesso")
            self.accept()
        except Exception as exc:
            logger.error("Erro ao salvar configuração PIX: %s", exc, exc_info=True)
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro ao salvar as configurações: {exc}")
