from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ....domain.models import ClientDetail, ClientSummary
from ..contracts import ClientsOverviewViewModelProtocol
from ..icons import Icons
from .register_receipt_dialog import RegisterReceiptDialog


class ClientsDialog(QDialog):
    def __init__(self, *, view_model: ClientsOverviewViewModelProtocol, parent=None) -> None:
        super().__init__(parent)
        self.view_model = view_model
        self.changed = False
        self.clients_table = QTableWidget()
        self.productions_table = QTableWidget()
        self.receipts_table = QTableWidget()
        self.summary_labels: dict[str, QLabel] = {}
        self.current_detail: ClientDetail | None = None
        self._setup_ui()
        self._load_state()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Painel de Clientes")
        self.setMinimumSize(1380, 860)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        toolbar = QHBoxLayout()
        refresh_button = QPushButton("Atualizar")
        refresh_button.setObjectName("secondaryButton")
        refresh_button.setIcon(Icons.refresh())
        refresh_button.clicked.connect(self._reload_current_client)
        toolbar.addWidget(refresh_button)

        register_button = QPushButton("Registrar Pagamento")
        register_button.setObjectName("successButton")
        register_button.setIcon(Icons.money())
        register_button.clicked.connect(self._open_register_receipt_dialog)
        toolbar.addWidget(register_button)
        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)
        content_layout.addWidget(self._create_clients_panel(), 2)
        content_layout.addWidget(self._create_detail_panel(), 3)
        main_layout.addLayout(content_layout, 1)

        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_button = QPushButton("Fechar")
        close_button.setObjectName("secondaryButton")
        close_button.clicked.connect(self.accept)
        close_layout.addWidget(close_button)
        main_layout.addLayout(close_layout)

    def _create_clients_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(QLabel("Clientes"))

        self.clients_table.setColumnCount(8)
        self.clients_table.setHorizontalHeaderLabels(
            ["Cliente", "Produções", "Abertas", "Andamento", "Contratado", "Recebido", "Saldo", "Crédito"]
        )
        self.clients_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.clients_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.clients_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.clients_table.itemSelectionChanged.connect(self._on_client_selection_changed)
        header = self.clients_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.clients_table, 1)
        return container

    def _create_detail_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self._create_summary_group())

        productions_group = QGroupBox("Produções")
        productions_layout = QVBoxLayout(productions_group)
        self.productions_table.setColumnCount(7)
        self.productions_table.setHorizontalHeaderLabels(
            ["Código", "Produção", "Recebimento", "Total", "Recebido", "Saldo", "Status"]
        )
        self.productions_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.productions_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        productions_header = self.productions_table.horizontalHeader()
        if productions_header is not None:
            productions_header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        productions_layout.addWidget(self.productions_table)
        layout.addWidget(productions_group, 1)

        receipts_group = QGroupBox("Recebimentos")
        receipts_layout = QVBoxLayout(receipts_group)
        self.receipts_table.setColumnCount(6)
        self.receipts_table.setHorizontalHeaderLabels(
            ["Data", "Valor", "Não alocado", "Forma", "Origem", "Observação"]
        )
        self.receipts_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.receipts_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        receipts_header = self.receipts_table.horizontalHeader()
        if receipts_header is not None:
            receipts_header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        receipts_layout.addWidget(self.receipts_table)
        layout.addWidget(receipts_group, 1)
        return container

    def _create_summary_group(self) -> QGroupBox:
        group = QGroupBox("Resumo do Cliente")
        layout = QGridLayout(group)
        summary_items = [
            ("Cliente", "cliente"),
            ("Total de produções", "total_productions"),
            ("Produções em aberto", "open_productions"),
            ("Em andamento", "in_progress_productions"),
            ("Valor contratado", "valor_contratado"),
            ("Valor recebido", "valor_recebido"),
            ("Saldo", "saldo"),
            ("Crédito", "credito"),
        ]
        for index, (label_text, key) in enumerate(summary_items):
            title = QLabel(label_text)
            value = QLabel("-")
            value.setStyleSheet("font-weight: bold;")
            self.summary_labels[key] = value
            row = index // 2
            base_col = (index % 2) * 2
            layout.addWidget(title, row, base_col)
            layout.addWidget(value, row, base_col + 1)
        return group

    def _load_state(self) -> None:
        state = self.view_model.load_initial_state()
        self._populate_clients_table(state.clients)
        if state.selected_client is not None:
            self._set_current_detail(state.selected_client)

    def _populate_clients_table(self, clients: list[ClientSummary]) -> None:
        self.clients_table.setRowCount(len(clients))
        for row_index, client in enumerate(clients):
            items = [
                client.cliente,
                str(client.total_productions),
                str(client.open_productions),
                str(client.in_progress_productions),
                self.view_model.format_money(client.valor_contratado),
                self.view_model.format_money(client.valor_recebido),
                self.view_model.format_money(client.saldo),
                self.view_model.format_money(client.credito),
            ]
            for col_index, value in enumerate(items):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, client.client_id)
                self.clients_table.setItem(row_index, col_index, item)

        if clients and self.clients_table.currentRow() < 0:
            self.clients_table.selectRow(0)

    def _on_client_selection_changed(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            return
        detail = self.view_model.load_client_detail(client_id)
        if detail is None:
            QMessageBox.warning(self, "Cliente", "Não foi possível carregar os dados do cliente.")
            return
        self._set_current_detail(detail)

    def _selected_client_id(self) -> int | None:
        row = self.clients_table.currentRow()
        if row < 0:
            return None
        item = self.clients_table.item(row, 0)
        if item is None:
            return None
        client_id = item.data(Qt.ItemDataRole.UserRole)
        return int(client_id) if client_id is not None else None

    def _set_current_detail(self, detail: ClientDetail) -> None:
        self.current_detail = detail
        summary = detail.summary
        self.summary_labels["cliente"].setText(summary.cliente)
        self.summary_labels["total_productions"].setText(str(summary.total_productions))
        self.summary_labels["open_productions"].setText(str(summary.open_productions))
        self.summary_labels["in_progress_productions"].setText(str(summary.in_progress_productions))
        self.summary_labels["valor_contratado"].setText(self.view_model.format_money(summary.valor_contratado))
        self.summary_labels["valor_recebido"].setText(self.view_model.format_money(summary.valor_recebido))
        self.summary_labels["saldo"].setText(self.view_model.format_money(summary.saldo))
        self.summary_labels["credito"].setText(self.view_model.format_money(summary.credito))
        self._populate_productions_table(detail)
        self._populate_receipts_table(detail)

    def _populate_productions_table(self, detail: ClientDetail) -> None:
        self.productions_table.setRowCount(len(detail.productions))
        for row_index, production in enumerate(detail.productions):
            data_text = production.data_recebimento.isoformat() if production.data_recebimento else ""
            status_text = f"{production.status_pagamento} / {production.status}"
            values = [
                production.codigo or "-",
                production.nome,
                data_text,
                self.view_model.format_money(production.valor_total),
                self.view_model.format_money(production.valor_recebido),
                self.view_model.format_money(production.saldo),
                status_text,
            ]
            for col_index, value in enumerate(values):
                self.productions_table.setItem(row_index, col_index, QTableWidgetItem(value))

    def _populate_receipts_table(self, detail: ClientDetail) -> None:
        self.receipts_table.setRowCount(len(detail.receipts))
        for row_index, receipt in enumerate(detail.receipts):
            values = [
                receipt.data_recebimento.isoformat() if receipt.data_recebimento else "",
                self.view_model.format_money(receipt.valor_total),
                self.view_model.format_money(receipt.valor_nao_alocado),
                receipt.forma_pagamento,
                receipt.origem,
                receipt.observacao,
            ]
            for col_index, value in enumerate(values):
                self.receipts_table.setItem(row_index, col_index, QTableWidgetItem(value))

    def _open_register_receipt_dialog(self) -> None:
        if self.current_detail is None:
            QMessageBox.warning(self, "Clientes", "Selecione um cliente antes de registrar um pagamento.")
            return
        dialog = RegisterReceiptDialog(
            view_model=self.view_model,
            client_detail=self.current_detail,
            parent=self,
        )
        dialog.exec()
        if dialog.saved:
            self.changed = True
            self._reload_current_client()

    def _reload_current_client(self) -> None:
        selected_client_id = self._selected_client_id()
        state = self.view_model.load_initial_state()
        self._populate_clients_table(state.clients)

        target_client_id = selected_client_id
        if target_client_id is None and state.selected_client is not None:
            target_client_id = state.selected_client.summary.client_id
        if target_client_id is None:
            return

        self._select_client_row(target_client_id)
        detail = self.view_model.load_client_detail(target_client_id)
        if detail is not None:
            self._set_current_detail(detail)

    def _select_client_row(self, client_id: int) -> None:
        for row_index in range(self.clients_table.rowCount()):
            item = self.clients_table.item(row_index, 0)
            if item is None:
                continue
            if int(item.data(Qt.ItemDataRole.UserRole) or 0) == client_id:
                self.clients_table.selectRow(row_index)
                return
