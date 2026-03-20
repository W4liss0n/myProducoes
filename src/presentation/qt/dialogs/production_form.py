from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

import qtawesome as qta
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ....config.constants import DEFAULT_STATUS_OPTIONS, DEFAULT_STATUS_PAGAMENTO_OPTIONS
from ..contracts import ProductionFormViewModelProtocol
from ..types import ProductionFormData
from ..widgets import AutocompleteLineEdit, MoneyLineEdit
from .production_form_support import ProductionFormFields, ProductionFormValidator

logger = logging.getLogger(__name__)


class ProductionFormDialog(QDialog):
    def __init__(
        self,
        *,
        view_model: ProductionFormViewModelProtocol,
        parent=None,
        mode: str = "add",
        initial_data: ProductionFormData | None = None,
        tipos_producao: list[str] | None = None,
        clientes_list: list[str] | None = None,
        on_save: Callable[[ProductionFormData], None] | None = None,
    ):
        super().__init__(parent)
        self.view_model = view_model
        self.mode = mode
        self.initial_data = initial_data or ProductionFormData(
            status=DEFAULT_STATUS_OPTIONS[0],
            status_pagamento=DEFAULT_STATUS_PAGAMENTO_OPTIONS[0],
        )
        self.tipos_producao = tipos_producao or []
        self.clientes_list = clientes_list or []
        self.on_save_callback = on_save
        self.validator = ProductionFormValidator()
        self.pasta_producao = self.initial_data.pasta_producao or ""
        self.result_data: ProductionFormData | None = None
        self.label_valor_total: QLabel | None = None
        self.label_valor_recebido: QLabel | None = None
        self.label_saldo: QLabel | None = None
        self.fields = self._build_fields()
        self.widgets = self.fields.as_widget_map()

        self._setup_ui()
        self.validator.populate(self.fields, self.initial_data)
        self._connect_signals()
        self._calculate_total()

    def _setup_ui(self) -> None:
        title = (
            "Adicionar Produção"
            if self.mode == "add"
            else f"Editar Produção - {self.initial_data.cliente}"
        )
        self.setWindowTitle(title)
        self.setFixedSize(1000, 580)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)
        content_layout.addWidget(self._create_info_group(), stretch=1)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)
        right_layout.addWidget(self._create_quantities_group())
        right_layout.addWidget(self._create_values_group())
        right_layout.addWidget(self._create_reports_group())
        content_layout.addLayout(right_layout, stretch=1)

        main_layout.addLayout(content_layout, stretch=1)
        main_layout.addStretch()
        main_layout.addLayout(self._create_button_layout())

    def _build_fields(self) -> ProductionFormFields:
        tipo_input = QComboBox()
        tipo_input.addItems(self.tipos_producao)

        data_receb_input = QDateEdit()
        data_receb_input.setCalendarPopup(True)
        data_receb_input.setDisplayFormat("dd/MM/yyyy")

        data_conc_input = QDateEdit()
        data_conc_input.setCalendarPopup(True)
        data_conc_input.setDisplayFormat("dd/MM/yyyy")

        status_input = QComboBox()
        status_input.addItems(DEFAULT_STATUS_OPTIONS)
        status_pag_input = QComboBox()
        status_pag_input.addItems(DEFAULT_STATUS_PAGAMENTO_OPTIONS)
        status_pag_input.setEnabled(False)

        return ProductionFormFields(
            cliente=AutocompleteLineEdit(self.clientes_list),
            nome=QLineEdit(),
            tipo_producao=tipo_input,
            data_recebimento=data_receb_input,
            data_conclusao=data_conc_input,
            status=status_input,
            status_pagamento=status_pag_input,
            quantidade_alunos=self._build_quantity_field(),
            quantidade_fotos=self._build_quantity_field(),
            quantidade_kits=self._build_quantity_field(),
            quantidade_capas=self._build_quantity_field(),
            valor_por_foto=self._build_money_field(),
            valor_por_kit=self._build_money_field(),
            valor_por_capa=self._build_money_field(),
        )

    @staticmethod
    def _build_quantity_field() -> QLineEdit:
        widget = QLineEdit()
        widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        widget.setMaximumWidth(100)
        return widget

    @staticmethod
    def _build_money_field() -> MoneyLineEdit:
        widget = MoneyLineEdit()
        widget.setMaximumWidth(120)
        return widget

    def _create_info_group(self) -> QGroupBox:
        group = QGroupBox("Informações Gerais")
        main_layout = QVBoxLayout(group)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self._add_icon_label(main_layout, "fa5s.user", "Cliente*")
        main_layout.addWidget(self.fields.cliente)

        self._add_icon_label(main_layout, "fa5s.file-alt", "Nome*")
        main_layout.addWidget(self.fields.nome)

        self._add_icon_label(main_layout, "fa5s.tag", "Tipo Serviço*")
        main_layout.addWidget(self.fields.tipo_producao)

        self._add_icon_label(main_layout, "fa5s.calendar-alt", "Data Recebimento*")
        main_layout.addWidget(self.fields.data_recebimento)

        self._add_icon_label(main_layout, "fa5s.calendar-check", "Data Conclusão")
        main_layout.addWidget(self.fields.data_conclusao)

        labels_layout = QHBoxLayout()
        labels_layout.setSpacing(10)
        labels_layout.addLayout(self._build_inline_label("fa5s.tasks", "Status*"))
        labels_layout.addLayout(self._build_inline_label("fa5s.money-bill-wave", "Status Pagamento*"))
        main_layout.addLayout(labels_layout)

        inputs_layout = QHBoxLayout()
        inputs_layout.addWidget(self.fields.status)
        inputs_layout.addWidget(self.fields.status_pagamento)
        main_layout.addLayout(inputs_layout)
        return group

    def _create_quantities_group(self) -> QGroupBox:
        group = QGroupBox("Quantidades")
        layout = QGridLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        quantities = [
            ("fa5s.users", "Alunos", self.fields.quantidade_alunos),
            ("fa5s.camera", "Fotos", self.fields.quantidade_fotos),
            ("fa5s.box", "Kits", self.fields.quantidade_kits),
            ("fa5s.book", "Capas", self.fields.quantidade_capas),
        ]
        for col, (icon_name, label_text, widget) in enumerate(quantities):
            header_widget = QWidget()
            header_layout = QHBoxLayout(header_widget)
            header_layout.setSpacing(4)
            header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label = QLabel()
            icon_label.setPixmap(qta.icon(icon_name, color="#555").pixmap(14, 14))
            header_layout.addWidget(icon_label)
            header_layout.addWidget(QLabel(label_text))
            layout.addWidget(header_widget, 0, col, Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(widget, 1, col, Qt.AlignmentFlag.AlignCenter)
        return group

    def _create_values_group(self) -> QGroupBox:
        group = QGroupBox("Valores Unitários")
        layout = QGridLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        values = [
            ("fa5s.dollar-sign", "R$/Foto", self.fields.valor_por_foto),
            ("fa5s.dollar-sign", "R$/Kit", self.fields.valor_por_kit),
            ("fa5s.dollar-sign", "R$/Capa", self.fields.valor_por_capa),
        ]
        for col, (icon_name, label_text, widget) in enumerate(values):
            header_widget = QWidget()
            header_layout = QHBoxLayout(header_widget)
            header_layout.setSpacing(4)
            header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label = QLabel()
            icon_label.setPixmap(qta.icon(icon_name, color="#28a745").pixmap(14, 14))
            header_layout.addWidget(icon_label)
            header_layout.addWidget(QLabel(label_text))
            layout.addWidget(header_widget, 0, col, Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(widget, 1, col, Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(QLabel(""), 2, 0, 1, 3)
        total_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon("fa5s.coins", color="#28a745").pixmap(18, 18))
        total_layout.addWidget(icon_label)
        total_layout.addWidget(QLabel("Valor Total:"))
        self.label_valor_total = QLabel("R$ 0,00")
        self.label_valor_total.setStyleSheet("font-weight: bold; color: #28a745; font-size: 14px;")
        total_layout.addWidget(self.label_valor_total)
        total_layout.addWidget(QLabel("(calculado automaticamente)"))
        total_layout.addStretch()
        total_widget = QWidget()
        total_widget.setLayout(total_layout)
        layout.addWidget(total_widget, 3, 0, 1, 3)

        recebido_layout = QHBoxLayout()
        recebido_layout.addWidget(QLabel("Valor Recebido:"))
        self.label_valor_recebido = QLabel(self._format_money(self.initial_data.valor_recebido))
        self.label_valor_recebido.setStyleSheet("font-weight: bold; color: #2196F3;")
        recebido_layout.addWidget(self.label_valor_recebido)
        recebido_layout.addSpacing(20)
        recebido_layout.addWidget(QLabel("Saldo:"))
        self.label_saldo = QLabel(self._format_money(self.initial_data.saldo))
        self.label_saldo.setStyleSheet("font-weight: bold; color: #dc3545;")
        recebido_layout.addWidget(self.label_saldo)
        recebido_layout.addStretch()
        recebido_widget = QWidget()
        recebido_widget.setLayout(recebido_layout)
        layout.addWidget(recebido_widget, 4, 0, 1, 3)
        return group

    def _create_reports_group(self) -> QGroupBox:
        group = QGroupBox("Relatórios")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        btn_gerar_pdf = QPushButton("Gerar Relatório PDF")
        btn_gerar_pdf.setIcon(qta.icon("fa5s.file-pdf", color="#dc3545"))
        btn_gerar_pdf.clicked.connect(self._gerar_relatorio_pdf)
        btn_gerar_pdf.setMinimumHeight(40)
        layout.addWidget(btn_gerar_pdf)
        info_label = QLabel("Gera relatório detalhado dos alunos\ncom fotos e kits por aluno")
        info_label.setStyleSheet("color: #666; font-size: 11px;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)
        return group

    def _create_button_layout(self) -> QHBoxLayout:
        button_layout = QHBoxLayout()
        btn_folder = QPushButton("Selecionar Pasta da Produção")
        btn_folder.setObjectName("secondaryButton")
        btn_folder.setIcon(qta.icon("fa5s.folder", color="#666"))
        btn_folder.clicked.connect(self._select_folder)
        btn_folder.setMinimumWidth(180)
        button_layout.addWidget(btn_folder)
        button_layout.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("secondaryButton")
        btn_cancel.setIcon(qta.icon("fa5s.times", color="#666"))
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setMinimumWidth(120)
        button_layout.addWidget(btn_cancel)

        save_text = "Salvar Alterações" if self.mode == "edit" else "Adicionar Produção"
        btn_save = QPushButton(save_text)
        btn_save.setObjectName("successButton" if self.mode == "add" else "primaryButton")
        btn_save.setIcon(qta.icon("fa5s.save", color="white"))
        btn_save.clicked.connect(self._on_save)
        btn_save.setMinimumWidth(150)
        button_layout.addWidget(btn_save)
        return button_layout

    def _add_icon_label(self, layout: QVBoxLayout, icon_name: str, text: str) -> None:
        layout.addLayout(self._build_inline_label(icon_name, text))

    @staticmethod
    def _build_inline_label(icon_name: str, text: str) -> QHBoxLayout:
        label_layout = QHBoxLayout()
        label_layout.setSpacing(5)
        label_layout.addWidget(qta.IconWidget(icon_name, color="#555"))
        label_layout.addWidget(QLabel(text))
        label_layout.addStretch()
        return label_layout

    def _connect_signals(self) -> None:
        for widget in (
            self.fields.quantidade_fotos,
            self.fields.quantidade_kits,
            self.fields.quantidade_capas,
        ):
            widget.textChanged.connect(self._calculate_total)
        for widget in (
            self.fields.valor_por_foto,
            self.fields.valor_por_kit,
            self.fields.valor_por_capa,
        ):
            widget.value_changed.connect(self._calculate_total)

    def _calculate_total(self) -> None:
        try:
            total = self.validator.calculate_total(self.fields)
            if self.label_valor_total:
                self.label_valor_total.setText(self._format_money(total))
            self._refresh_financial_projection(total)
        except Exception:
            if self.label_valor_total:
                self.label_valor_total.setText("R$ 0,00")
            self._refresh_financial_projection(0.0)

    def _select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta da Produção")
        if not folder:
            return
        self.pasta_producao = folder
        self.validator.apply_folder_name(self.fields, Path(folder).name)

        try:
            inspection = self.view_model.inspect_folder(folder)
            self.validator.apply_folder_inspection(self.fields, inspection)
        except Exception as exc:
            logger.error("Erro ao calcular quantidades: %s", exc, exc_info=True)
            QMessageBox.warning(
                self,
                "Aviso",
                f"Não foi possível calcular as quantidades automaticamente.\nErro: {exc}",
            )

    def _ensure_folder_selected(self) -> Path | None:
        if not self.pasta_producao:
            reply = QMessageBox.question(
                self,
                "Pasta não selecionada",
                "Nenhuma pasta da produção está selecionada.\nDeseja selecionar uma pasta agora?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return None
            folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta da Produção")
            if not folder:
                return None
            self.pasta_producao = folder
        folder_path = Path(self.pasta_producao)
        if folder_path.exists():
            return folder_path
        QMessageBox.warning(
            self,
            "Pasta não encontrada",
            (
                f"A pasta da produção não foi encontrada:\n{self.pasta_producao}\n\n"
                "Por favor, selecione a pasta novamente."
            ),
        )
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta da Produção")
        if not folder:
            return None
        self.pasta_producao = folder
        return Path(folder)

    def _gerar_relatorio_pdf(self) -> None:
        folder_path = self._ensure_folder_selected()
        if folder_path is None:
            return
        nome_producao = self.fields.nome.text() or folder_path.name
        nome_producao = nome_producao or folder_path.name
        arquivo_pdf, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Relatório PDF",
            f"{nome_producao}.pdf",
            "PDF Files (*.pdf)",
        )
        if not arquivo_pdf:
            return
        empresa = self.fields.cliente.text()
        result = self.view_model.generate_report(
            folder_path=str(folder_path),
            output_path=Path(arquivo_pdf),
            production_name=nome_producao,
            company=empresa,
        )
        if not result.success:
            QMessageBox.warning(self, "Erro", result.message)
            return
        reply = QMessageBox.question(
            self,
            "PDF Gerado",
            f"Relatório gerado com sucesso!\n\n{arquivo_pdf}\n\nDeseja abrir o arquivo?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(arquivo_pdf).resolve())))

    def _on_save(self) -> None:
        try:
            dados = self.validator.collect(
                self.fields,
                initial_data=self.initial_data,
                pasta_producao=self.pasta_producao,
            )
            validation_error = self.validator.validate_required(dados)
            if validation_error:
                QMessageBox.warning(self, "Campos Obrigatórios", validation_error)
                return
            if self.on_save_callback:
                self.on_save_callback(dados)
            self.result_data = dados
            self.accept()
        except ValueError as exc:
            QMessageBox.critical(self, "Erro de Validação", f"Valor inválido em um dos campos numéricos: {exc}")
        except Exception as exc:
            logger.error("Erro ao salvar formulário: %s", exc, exc_info=True)
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro ao processar o formulário: {exc}")

    def get_data(self) -> ProductionFormData | None:
        return self.result_data

    def _refresh_financial_projection(self, valor_total: float) -> None:
        valor_recebido = float(self.initial_data.valor_recebido or 0.0)
        saldo = max(float(valor_total or 0.0) - valor_recebido, 0.0)
        status = "Pago"
        if valor_recebido <= 0 and valor_total > 0:
            status = "Em aberto"
        elif 0 < valor_recebido < valor_total:
            status = "Parcial"

        index = self.fields.status_pagamento.findText(status)
        if index >= 0:
            self.fields.status_pagamento.setCurrentIndex(index)
        if self.label_valor_recebido is not None:
            self.label_valor_recebido.setText(self._format_money(valor_recebido))
        if self.label_saldo is not None:
            self.label_saldo.setText(self._format_money(saldo))

    @staticmethod
    def _format_money(value: float) -> str:
        return f"R$ {float(value or 0.0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
