# -*- coding: utf-8 -*-
"""
Diálogo para gerenciar tipos de produção.
"""

import logging
from typing import Callable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ..icons import Icons

logger = logging.getLogger(__name__)


class ManageTypesDialog(QDialog):
    def __init__(
        self,
        parent=None,
        tipos_producao: list[str] | None = None,
        on_add: Optional[Callable[[str], bool]] = None,
        on_remove: Optional[Callable[[str], bool]] = None,
    ):
        super().__init__(parent)
        self.tipos_producao = tipos_producao.copy() if tipos_producao else []
        self.on_add = on_add
        self.on_remove = on_remove
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Gerenciar Tipos de Serviços")
        self.setMinimumSize(400, 400)
        layout = QVBoxLayout(self)

        title = QLabel("Tipos de Serviços Cadastrados")
        title.setObjectName("subtitleLabel")
        layout.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self._populate_list()
        layout.addWidget(self.list_widget)

        input_layout = QHBoxLayout()
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Digite o novo tipo de serviço...")
        self.entry.returnPressed.connect(self._add_tipo)
        input_layout.addWidget(self.entry)

        btn_add = QPushButton("Adicionar")
        btn_add.setObjectName("successButton")
        btn_add.setIcon(Icons.add())
        btn_add.clicked.connect(self._add_tipo)
        input_layout.addWidget(btn_add)

        btn_remove = QPushButton("Remover")
        btn_remove.setObjectName("dangerButton")
        btn_remove.setIcon(Icons.delete())
        btn_remove.clicked.connect(self._remove_tipo)
        input_layout.addWidget(btn_remove)
        layout.addLayout(input_layout)

        btn_close = QPushButton("Fechar")
        btn_close.setObjectName("secondaryButton")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)
        self.list_widget.installEventFilter(self)

    def _populate_list(self) -> None:
        self.list_widget.clear()
        for tipo in sorted(self.tipos_producao, key=str.lower):
            self.list_widget.addItem(tipo)

    def _add_tipo(self) -> None:
        novo_tipo = self.entry.text().strip()
        if not novo_tipo:
            QMessageBox.warning(self, "Inválido", "O nome do tipo não pode ser vazio.")
            return

        if novo_tipo.lower() in (t.lower() for t in self.tipos_producao):
            QMessageBox.warning(self, "Duplicado", f"O tipo '{novo_tipo}' já existe.")
            return

        success = self.on_add(novo_tipo) if self.on_add else True
        if success:
            self.tipos_producao.append(novo_tipo)
            self._populate_list()
            self.entry.clear()
            logger.info("Tipo de produção adicionado: %s", novo_tipo)

    def _remove_tipo(self) -> None:
        current_item = self.list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Nenhuma Seleção", "Selecione um tipo na lista para remover.")
            return

        tipo_selecionado = current_item.text()
        reply = QMessageBox.question(
            self,
            "Confirmar Remoção",
            f"Tem certeza que deseja remover o tipo '{tipo_selecionado}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        success = self.on_remove(tipo_selecionado) if self.on_remove else True
        if success:
            try:
                self.tipos_producao.remove(tipo_selecionado)
                self._populate_list()
                logger.info("Tipo de produção removido: %s", tipo_selecionado)
            except ValueError:
                logger.warning("Tipo '%s' não encontrado na lista", tipo_selecionado)

    def eventFilter(self, obj, event):
        if obj == self.list_widget and event.type() == event.Type.KeyPress and event.key() == Qt.Key.Key_Delete:
            self._remove_tipo()
            return True
        return super().eventFilter(obj, event)

    def get_tipos(self) -> list[str]:
        return self.tipos_producao.copy()
