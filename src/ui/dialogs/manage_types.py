# -*- coding: utf-8 -*-
"""
Diálogo para Gerenciar Tipos de Produção - PyQt6
"""
import logging
from typing import List, Callable, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QLineEdit, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt

from ..icons import Icons

logger = logging.getLogger(__name__)


class ManageTypesDialog(QDialog):
    """Diálogo para adicionar e remover tipos de produção"""

    def __init__(
        self,
        parent=None,
        tipos_producao: List[str] = None,
        on_add: Optional[Callable[[str], bool]] = None,
        on_remove: Optional[Callable[[str], bool]] = None
    ):
        """
        Inicializa o diálogo

        Args:
            parent: Widget pai
            tipos_producao: Lista atual de tipos de produção
            on_add: Callback ao adicionar tipo (retorna True se sucesso)
            on_remove: Callback ao remover tipo (retorna True se sucesso)
        """
        super().__init__(parent)

        self.tipos_producao = tipos_producao.copy() if tipos_producao else []
        self.on_add = on_add
        self.on_remove = on_remove

        self._setup_ui()

    def _setup_ui(self):
        """Configura a interface"""
        self.setWindowTitle("Gerenciar Tipos de Serviços")
        self.setMinimumSize(400, 400)

        layout = QVBoxLayout(self)

        # Título
        title = QLabel("Tipos de Serviços Cadastrados")
        title.setObjectName("subtitleLabel")
        layout.addWidget(title)

        # ListWidget para exibir tipos
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self._populate_list()
        layout.addWidget(self.list_widget)

        # Campo de entrada e botões de ação
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

        # Botão Fechar
        btn_close = QPushButton("Fechar")
        btn_close.setObjectName("secondaryButton")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

        # Atalho de teclado Delete
        self.list_widget.installEventFilter(self)

    def _populate_list(self):
        """Preenche a lista com os tipos"""
        self.list_widget.clear()
        for tipo in sorted(self.tipos_producao, key=str.lower):
            self.list_widget.addItem(tipo)

    def _add_tipo(self):
        """Adiciona um novo tipo de produção"""
        novo_tipo = self.entry.text().strip()

        if not novo_tipo:
            QMessageBox.warning(
                self,
                "Inválido",
                "O nome do tipo não pode ser vazio."
            )
            return

        if novo_tipo.lower() in (t.lower() for t in self.tipos_producao):
            QMessageBox.warning(
                self,
                "Duplicado",
                f"O tipo '{novo_tipo}' já existe."
            )
            return

        # Chamar callback se existir
        success = True
        if self.on_add:
            success = self.on_add(novo_tipo)

        if success:
            self.tipos_producao.append(novo_tipo)
            self._populate_list()
            self.entry.clear()
            logger.info(f"Tipo de produção adicionado: {novo_tipo}")

    def _remove_tipo(self):
        """Remove o tipo selecionado"""
        current_item = self.list_widget.currentItem()

        if not current_item:
            QMessageBox.warning(
                self,
                "Nenhuma Seleção",
                "Selecione um tipo na lista para remover."
            )
            return

        tipo_selecionado = current_item.text()

        reply = QMessageBox.question(
            self,
            "Confirmar Remoção",
            f"Tem certeza que deseja remover o tipo '{tipo_selecionado}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Chamar callback se existir
        success = True
        if self.on_remove:
            success = self.on_remove(tipo_selecionado)

        if success:
            try:
                self.tipos_producao.remove(tipo_selecionado)
                self._populate_list()
                logger.info(f"Tipo de produção removido: {tipo_selecionado}")
            except ValueError:
                logger.warning(f"Tipo '{tipo_selecionado}' não encontrado na lista")

    def eventFilter(self, obj, event):
        """Filtro de eventos para detectar Delete key"""
        if obj == self.list_widget:
            if event.type() == event.Type.KeyPress:
                if event.key() == Qt.Key.Key_Delete:
                    self._remove_tipo()
                    return True
        return super().eventFilter(obj, event)

    def get_tipos(self) -> List[str]:
        """Retorna a lista atualizada de tipos"""
        return self.tipos_producao.copy()
