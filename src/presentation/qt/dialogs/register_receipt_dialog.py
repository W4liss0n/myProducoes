from __future__ import annotations

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from ....domain.models import ClientDetail, ReceiptAllocationRequest
from ..contracts import ClientsOverviewViewModelProtocol
from ..icons import Icons


class RegisterReceiptDialog(QDialog):
    def __init__(
        self,
        *,
        view_model: ClientsOverviewViewModelProtocol,
        client_detail: ClientDetail,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.view_model = view_model
        self.client_detail = client_detail
        self.saved = False
        self._allocation_inputs: dict[int, QDoubleSpinBox] = {}
        self._balance_by_production: dict[int, float] = {
            balance.production_id: float(balance.saldo or 0.0) for balance in client_detail.open_balances
        }
        self.value_input = QDoubleSpinBox()
        self.date_input = QDateEdit()
        self.method_input = QComboBox()
        self.mode_input = QComboBox()
        self.observation_input = QTextEdit()
        self.allocations_table = QTableWidget()
        self.total_label = QLabel("R$ 0,00")
        self.allocated_label = QLabel("R$ 0,00")
        self.remaining_label = QLabel("R$ 0,00")

        self._setup_ui()
        self._populate_allocations_table()
        self._apply_auto_suggestions()
        self._update_totals()

    def _setup_ui(self) -> None:
        self.setWindowTitle(f"Registrar Pagamento - {self.client_detail.summary.cliente}")
        self.setMinimumSize(900, 650)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        info_group = QGroupBox("Recebimento")
        info_layout = QFormLayout(info_group)

        self.value_input.setDecimals(2)
        self.value_input.setMaximum(999999999.99)
        self.value_input.setValue(max(float(self.client_detail.summary.saldo or 0.0), 0.0))
        self.value_input.valueChanged.connect(self._on_value_changed)
        info_layout.addRow("Valor recebido*", self.value_input)

        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("dd/MM/yyyy")
        self.date_input.setDate(QDate.currentDate())
        info_layout.addRow("Data", self.date_input)

        self.method_input.setEditable(True)
        self.method_input.addItems(["PIX", "Dinheiro", "Cartão", "Transferência", "Boleto"])
        info_layout.addRow("Forma de pagamento", self.method_input)

        self.mode_input.addItems(["Automático (FIFO)", "Manual"])
        self.mode_input.currentTextChanged.connect(self._on_mode_changed)
        info_layout.addRow("Modo de alocação", self.mode_input)

        self.observation_input.setPlaceholderText("Observação opcional")
        self.observation_input.setMaximumHeight(90)
        info_layout.addRow("Observação", self.observation_input)
        main_layout.addWidget(info_group)

        allocations_group = QGroupBox("Alocação por produção")
        allocations_layout = QVBoxLayout(allocations_group)
        allocations_layout.addWidget(self.allocations_table)
        main_layout.addWidget(allocations_group, 1)

        totals_group = QGroupBox("Resumo")
        totals_layout = QGridLayout(totals_group)
        totals_layout.addWidget(QLabel("Recebimento"), 0, 0)
        totals_layout.addWidget(self.total_label, 0, 1)
        totals_layout.addWidget(QLabel("Alocado"), 1, 0)
        totals_layout.addWidget(self.allocated_label, 1, 1)
        totals_layout.addWidget(QLabel("Remanescente"), 2, 0)
        totals_layout.addWidget(self.remaining_label, 2, 1)
        main_layout.addWidget(totals_group)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        cancel_button = QPushButton("Cancelar")
        cancel_button.setObjectName("secondaryButton")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)

        save_button = QPushButton("Registrar")
        save_button.setObjectName("successButton")
        save_button.setIcon(Icons.save())
        save_button.clicked.connect(self._save)
        buttons_layout.addWidget(save_button)
        main_layout.addLayout(buttons_layout)

    def _populate_allocations_table(self) -> None:
        headers = ["Código", "Produção", "Data", "Saldo", "Valor a alocar"]
        self.allocations_table.setColumnCount(len(headers))
        self.allocations_table.setHorizontalHeaderLabels(headers)
        self.allocations_table.setRowCount(len(self.client_detail.open_balances))
        self.allocations_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        vertical_header = self.allocations_table.verticalHeader()
        if vertical_header is not None:
            vertical_header.setVisible(False)

        for row_index, balance in enumerate(self.client_detail.open_balances):
            self.allocations_table.setItem(row_index, 0, QTableWidgetItem(balance.codigo or "-"))
            self.allocations_table.setItem(row_index, 1, QTableWidgetItem(balance.nome))
            data_text = balance.data_recebimento.isoformat() if balance.data_recebimento else ""
            self.allocations_table.setItem(row_index, 2, QTableWidgetItem(data_text))
            self.allocations_table.setItem(row_index, 3, QTableWidgetItem(self.view_model.format_money(balance.saldo)))

            allocation_input = QDoubleSpinBox()
            allocation_input.setDecimals(2)
            allocation_input.setMaximum(max(float(balance.saldo or 0.0), 0.0))
            allocation_input.valueChanged.connect(self._update_totals)
            self._allocation_inputs[balance.production_id] = allocation_input
            self.allocations_table.setCellWidget(row_index, 4, allocation_input)

        header = self.allocations_table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
        self._set_manual_mode_enabled(False)

    def _on_mode_changed(self, _mode: str) -> None:
        manual_mode = self._is_manual_mode()
        self._set_manual_mode_enabled(manual_mode)
        if not manual_mode:
            self._apply_auto_suggestions()
        self._update_totals()

    def _on_value_changed(self, _value: float) -> None:
        if not self._is_manual_mode():
            self._apply_auto_suggestions()
        self._update_totals()

    def _is_manual_mode(self) -> bool:
        return self.mode_input.currentText() == "Manual"

    def _set_manual_mode_enabled(self, enabled: bool) -> None:
        self.allocations_table.setEnabled(enabled and bool(self.client_detail.open_balances))
        for input_widget in self._allocation_inputs.values():
            input_widget.setEnabled(enabled)

    def _apply_auto_suggestions(self) -> None:
        for input_widget in self._allocation_inputs.values():
            input_widget.blockSignals(True)
            input_widget.setValue(0.0)
            input_widget.blockSignals(False)

        suggestions = self.view_model.suggest_allocations(
            self.client_detail.summary.client_id,
            float(self.value_input.value()),
        )
        for suggestion in suggestions:
            if suggestion.production_id not in self._allocation_inputs:
                continue
            input_widget = self._allocation_inputs[suggestion.production_id]
            input_widget.blockSignals(True)
            input_widget.setValue(float(suggestion.valor_alocado or 0.0))
            input_widget.blockSignals(False)

    def _manual_allocations(self) -> list[ReceiptAllocationRequest]:
        allocations: list[ReceiptAllocationRequest] = []
        for production_id, input_widget in self._allocation_inputs.items():
            value = float(input_widget.value())
            if value <= 0:
                continue
            allocations.append(
                ReceiptAllocationRequest(
                    production_id=production_id,
                    valor_alocado=value,
                )
            )
        return allocations

    def _allocated_total(self) -> float:
        return sum(float(item.valor_alocado) for item in self._manual_allocations())

    def _update_totals(self) -> None:
        total = float(self.value_input.value())
        allocated = self._allocated_total()
        remaining = max(total - allocated, 0.0)
        self.total_label.setText(self.view_model.format_money(total))
        self.allocated_label.setText(self.view_model.format_money(allocated))
        self.remaining_label.setText(self.view_model.format_money(remaining))

    def _save(self) -> None:
        valor_total = float(self.value_input.value())
        if valor_total <= 0:
            QMessageBox.warning(self, "Valor inválido", "Informe um valor maior que zero.")
            return

        allocations = self._manual_allocations() if self._is_manual_mode() else []
        result = self.view_model.register_receipt(
            client_id=self.client_detail.summary.client_id,
            data_recebimento=self.date_input.date().toString("yyyy-MM-dd"),
            valor_total=valor_total,
            forma_pagamento=self.method_input.currentText().strip(),
            observacao=self.observation_input.toPlainText().strip(),
            auto_allocate=not self._is_manual_mode(),
            allocations=allocations,
        )
        if not result.success:
            QMessageBox.warning(self, "Erro", result.message)
            return

        self.saved = True
        QMessageBox.information(self, "Recebimento", "Pagamento registrado com sucesso.")
        self.accept()
