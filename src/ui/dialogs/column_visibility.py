# -*- coding: utf-8 -*-
"""
Diálogo para gerenciar visibilidade de colunas
"""
from typing import Dict, List, Callable
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QCheckBox,
    QPushButton, QLabel, QScrollArea, QWidget, QGroupBox
)
from PyQt6.QtCore import Qt

from ..icons import Icons


class ColumnVisibilityDialog(QDialog):
    """Diálogo para selecionar quais colunas devem ser visíveis"""

    def __init__(self, parent, all_columns: List[str], visible_columns: List[str],
                 on_save: Callable[[List[str]], None]):
        super().__init__(parent)
        self.all_columns = all_columns
        self.visible_columns = visible_columns.copy()
        self.on_save_callback = on_save
        self.checkboxes: Dict[str, QCheckBox] = {}

        self._setup_ui()

    def _setup_ui(self):
        """Configura a interface do diálogo"""
        self.setWindowTitle("Gerenciar Visibilidade de Colunas")
        self.setMinimumWidth(500)
        self.setMinimumHeight(600)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Título
        title_label = QLabel("Selecione as colunas que deseja exibir:")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)

        # Botões de seleção rápida
        quick_buttons_layout = QHBoxLayout()

        btn_select_all = QPushButton("Selecionar Todas")
        btn_select_all.setIcon(Icons.add(Icons.COLOR_SECONDARY))
        btn_select_all.clicked.connect(self._select_all)
        quick_buttons_layout.addWidget(btn_select_all)

        btn_deselect_all = QPushButton("Desmarcar Todas")
        btn_deselect_all.setIcon(Icons.delete(Icons.COLOR_SECONDARY))
        btn_deselect_all.clicked.connect(self._deselect_all)
        quick_buttons_layout.addWidget(btn_deselect_all)

        quick_buttons_layout.addStretch()
        layout.addLayout(quick_buttons_layout)

        # Área de scroll para os checkboxes
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(400)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(8)

        # Criar checkboxes para cada coluna
        for column in self.all_columns:
            checkbox = QCheckBox(column)
            checkbox.setChecked(column in self.visible_columns)
            checkbox.setStyleSheet("padding: 5px;")
            self.checkboxes[column] = checkbox
            scroll_layout.addWidget(checkbox)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

        # Aviso
        warning_label = QLabel("⚠️ Pelo menos uma coluna deve estar visível")
        warning_label.setStyleSheet("color: #856404; background-color: #fff3cd; padding: 10px; border-radius: 5px;")
        layout.addWidget(warning_label)

        # Botões de ação
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("secondaryButton")
        btn_cancel.setMinimumWidth(120)
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Aplicar")
        btn_save.setObjectName("successButton")
        btn_save.setIcon(Icons.save())
        btn_save.setMinimumWidth(120)
        btn_save.clicked.connect(self._save)
        buttons_layout.addWidget(btn_save)

        layout.addLayout(buttons_layout)

    def _select_all(self):
        """Seleciona todas as colunas"""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(True)

    def _deselect_all(self):
        """Desmarca todas as colunas"""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)

    def _save(self):
        """Salva as seleções"""
        selected_columns = [
            column for column, checkbox in self.checkboxes.items()
            if checkbox.isChecked()
        ]

        # Validar que pelo menos uma coluna está selecionada
        if not selected_columns:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Nenhuma Coluna Selecionada",
                "Você deve selecionar pelo menos uma coluna para exibir."
            )
            return

        # Chamar callback com as colunas selecionadas
        if self.on_save_callback:
            self.on_save_callback(selected_columns)

        self.accept()

    def get_visible_columns(self) -> List[str]:
        """Retorna lista de colunas visíveis"""
        return [
            column for column, checkbox in self.checkboxes.items()
            if checkbox.isChecked()
        ]
