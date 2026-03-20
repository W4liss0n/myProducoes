# -*- coding: utf-8 -*-
"""
Diálogo para gerenciar visibilidade de colunas.
"""

from typing import Callable

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..icons import Icons


class ColumnVisibilityDialog(QDialog):
    def __init__(
        self,
        parent,
        all_columns: list[str],
        visible_columns: list[str],
        on_save: Callable[[list[str]], None],
    ):
        super().__init__(parent)
        self.all_columns = all_columns
        self.visible_columns = visible_columns.copy()
        self.on_save_callback = on_save
        self.checkboxes: dict[str, QCheckBox] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Gerenciar Visibilidade de Colunas")
        self.setMinimumWidth(500)
        self.setMinimumHeight(600)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        title_label = QLabel("Selecione as colunas que deseja exibir:")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)

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

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(400)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(8)

        for column in self.all_columns:
            checkbox = QCheckBox(column)
            checkbox.setChecked(column in self.visible_columns)
            checkbox.setStyleSheet("padding: 5px;")
            self.checkboxes[column] = checkbox
            scroll_layout.addWidget(checkbox)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

        warning_label = QLabel("Pelo menos uma coluna deve estar visível")
        warning_label.setStyleSheet("color: #856404; background-color: #fff3cd; padding: 10px; border-radius: 5px;")
        layout.addWidget(warning_label)

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

    def _select_all(self) -> None:
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(True)

    def _deselect_all(self) -> None:
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)

    def _save(self) -> None:
        selected_columns = [column for column, checkbox in self.checkboxes.items() if checkbox.isChecked()]
        if not selected_columns:
            QMessageBox.warning(
                self,
                "Nenhuma Coluna Selecionada",
                "Você deve selecionar pelo menos uma coluna para exibir.",
            )
            return

        self.on_save_callback(selected_columns)
        self.accept()

    def get_visible_columns(self) -> list[str]:
        return [column for column, checkbox in self.checkboxes.items() if checkbox.isChecked()]
