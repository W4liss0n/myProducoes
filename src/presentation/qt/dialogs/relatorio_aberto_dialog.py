from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ....domain.models import Production
from ..contracts import OpenReportSelectionViewModelProtocol
from ..icons import Icons
from ..mappers import ProductionPresentationMapper

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _OpenReportSelectionState:
    cliente_atual: str | None = None
    producoes_em_aberto: list[Production] = field(default_factory=list)

    def selected_ids(self, checkboxes: dict[int, QCheckBox]) -> list[int]:
        return [production_id for production_id, checkbox in checkboxes.items() if checkbox.isChecked()]


class RelatorioAbertoDialog(QDialog):
    def __init__(
        self,
        *,
        view_model: OpenReportSelectionViewModelProtocol,
        parent=None,
        on_generate: Callable[[str, list[int]], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.view_model = view_model
        self.on_generate_callback = on_generate
        self.checkboxes: dict[int, QCheckBox] = {}
        self._state = _OpenReportSelectionState()
        self._setup_ui()
        self._load_clientes()

    @property
    def producoes_em_aberto(self) -> list[Production]:
        return self._state.producoes_em_aberto

    def _setup_ui(self) -> None:
        self.setWindowTitle("Gerar Relatório de Produções em Aberto")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        title_label = QLabel("Relatório de Produções em Aberto")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)

        cliente_group = QGroupBox("Selecione o Cliente")
        cliente_layout = QHBoxLayout()
        cliente_layout.addWidget(QLabel("Cliente:"))
        self.combo_cliente = QComboBox()
        self.combo_cliente.setMinimumWidth(300)
        self.combo_cliente.currentTextChanged.connect(self._on_cliente_changed)
        cliente_layout.addWidget(self.combo_cliente)
        cliente_layout.addStretch()
        cliente_group.setLayout(cliente_layout)
        layout.addWidget(cliente_group)

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

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(350)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.scroll_widget)
        layout.addWidget(self.scroll_area)

        self.info_label = QLabel("Selecione um cliente para ver as produções em aberto")
        self.info_label.setStyleSheet("color: #666; font-style: italic; padding: 10px;")
        layout.addWidget(self.info_label)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("secondaryButton")
        btn_cancel.setMinimumWidth(120)
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)
        btn_generate = QPushButton("Gerar PDF")
        btn_generate.setObjectName("successButton")
        btn_generate.setIcon(Icons.pdf())
        btn_generate.setMinimumWidth(120)
        btn_generate.clicked.connect(self._generate_pdf)
        buttons_layout.addWidget(btn_generate)
        layout.addLayout(buttons_layout)

    def _load_clientes(self) -> None:
        try:
            self.combo_cliente.addItem("-- Selecione um cliente --")
            self.combo_cliente.addItems(sorted(self.view_model.list_clients()))
        except Exception as exc:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar clientes: {exc}")

    def _on_cliente_changed(self, cliente: str) -> None:
        if not cliente or cliente == "-- Selecione um cliente --":
            self._state.cliente_atual = None
            self._clear_producoes()
            self.info_label.setText("Selecione um cliente para ver as produções em aberto")
            return
        self._state.cliente_atual = cliente
        self._load_producoes_em_aberto(cliente)

    def _load_producoes_em_aberto(self, cliente: str) -> None:
        try:
            self._clear_producoes()
            self._state.producoes_em_aberto = self.view_model.list_open_by_client(cliente)
            if not self._state.producoes_em_aberto:
                self.info_label.setText(f"Nenhuma produção em aberto encontrada para {cliente}")
                return

            for producao in self._state.producoes_em_aberto:
                checkbox = QCheckBox(ProductionPresentationMapper.open_report_label(producao), self.scroll_widget)
                checkbox.setChecked(True)
                checkbox.setStyleSheet("padding: 5px;")
                self.checkboxes[producao.id] = checkbox
                self.scroll_layout.addWidget(checkbox)
            self.scroll_layout.addStretch()
            self.info_label.setText(f"{len(self._state.producoes_em_aberto)} produção(ões) em aberto encontrada(s)")
        except Exception as exc:
            logger.error("Erro ao carregar produções em aberto: %s", exc, exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao carregar produções: {exc}")

    def _clear_producoes(self) -> None:
        while self.scroll_layout.count() > 0:
            item = self.scroll_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.checkboxes.clear()
        self._state.producoes_em_aberto = []

    def _select_all(self) -> None:
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(True)

    def _deselect_all(self) -> None:
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)

    def _generate_pdf(self) -> None:
        cliente = self.combo_cliente.currentText()
        if not cliente or cliente == "-- Selecione um cliente --":
            QMessageBox.warning(
                self,
                "Cliente não selecionado",
                "Por favor, selecione um cliente antes de gerar o relatório.",
            )
            return

        selected_ids = self._state.selected_ids(self.checkboxes)
        if not selected_ids:
            QMessageBox.warning(
                self,
                "Nenhuma Produção Selecionada",
                "Você deve selecionar pelo menos uma produção para gerar o relatório.",
            )
            return

        if self.on_generate_callback:
            self.on_generate_callback(cliente, selected_ids)
        self.accept()
