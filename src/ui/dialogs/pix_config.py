# -*- coding: utf-8 -*-
"""
Diálogo para Configurar Dados do PIX - PyQt6
"""
import logging
from typing import Dict, Callable, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QMessageBox, QLabel, QHBoxLayout
)
from PyQt6.QtCore import Qt

from ..icons import Icons

logger = logging.getLogger(__name__)


class PixConfigDialog(QDialog):
    """Diálogo para configurar dados do PIX"""

    def __init__(
        self,
        parent=None,
        current_config: Optional[Dict[str, str]] = None,
        on_save: Optional[Callable[[Dict[str, str]], None]] = None
    ):
        """
        Inicializa o diálogo

        Args:
            parent: Widget pai
            current_config: Configuração atual do PIX
            on_save: Callback ao salvar (recebe dicionário com configurações)
        """
        super().__init__(parent)

        self.current_config = current_config or {}
        self.on_save_callback = on_save

        self.entries = {}

        self._setup_ui()

    def _setup_ui(self):
        """Configura a interface"""
        self.setWindowTitle("Configurar Dados PIX")
        self.setFixedSize(500, 280)

        layout = QVBoxLayout(self)

        # Título
        title = QLabel("Configuração PIX para Pagamentos")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(10)

        # Formulário
        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        # Campos
        campos = [
            ("Nome do Beneficiário*:", "nome_beneficiario", "Ex: João da Silva"),
            ("Chave PIX (UUID)*:", "chave_pix", "UUID de 36 caracteres"),
            ("Cidade*:", "cidade", "Ex: São Paulo")
        ]

        for label_text, key, placeholder in campos:
            entry = QLineEdit()
            entry.setPlaceholderText(placeholder)

            # Preencher com valor atual
            current_value = self.current_config.get(key, '')
            if current_value:
                entry.setText(current_value)

            # Limitar tamanho da chave PIX
            if key == "chave_pix":
                entry.setMaxLength(36)

            form_layout.addRow(label_text, entry)
            self.entries[key] = entry

        layout.addLayout(form_layout)
        layout.addSpacing(10)

        # Botões
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

    def _save_config(self):
        """Valida e salva a configuração"""
        try:
            # Coletar dados
            config = {}
            for key, entry in self.entries.items():
                value = entry.text().strip()
                config[key] = value

            # Validações
            if not config.get('nome_beneficiario'):
                QMessageBox.warning(
                    self,
                    "Campo Obrigatório",
                    "O nome do beneficiário é obrigatório!"
                )
                return

            if not config.get('chave_pix'):
                QMessageBox.warning(
                    self,
                    "Campo Obrigatório",
                    "A chave PIX é obrigatória!"
                )
                return

            if not config.get('cidade'):
                QMessageBox.warning(
                    self,
                    "Campo Obrigatório",
                    "A cidade é obrigatória!"
                )
                return

            # Validação do tamanho da chave PIX (UUID tem 36 caracteres)
            if len(config['chave_pix']) != 36:
                QMessageBox.warning(
                    self,
                    "Chave PIX Inválida",
                    "A chave PIX deve ter exatamente 36 caracteres (formato UUID)."
                )
                return

            # Chamar callback
            if self.on_save_callback:
                self.on_save_callback(config)

            QMessageBox.information(
                self,
                "Sucesso",
                "Configurações do PIX salvas com sucesso!"
            )

            logger.info("Configuração PIX salva com sucesso")
            self.accept()

        except Exception as e:
            logger.error(f"Erro ao salvar configuração PIX: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Erro",
                f"Ocorreu um erro ao salvar as configurações: {e}"
            )
