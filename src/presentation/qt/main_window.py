from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QCursor, QKeySequence
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ...config.constants import ALL_COLUMNS, DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS
from ...domain.models import ProductionFilters
from .contracts import MainWindowCoordinatorProtocol, MainWindowViewModelProtocol
from .dialogs.column_visibility import ColumnVisibilityDialog
from .dialogs.manage_types import ManageTypesDialog
from .dialogs.pix_config import PixConfigDialog
from .dialogs.settings import SettingsDialog
from .icons import Icons
from .mappers import ProductionPresentationMapper
from .table_model import ProductionTableModel
from .viewmodels import MainWindowState


class MainWindow(QMainWindow):
    def __init__(
        self,
        *,
        view_model: MainWindowViewModelProtocol,
        coordinator: MainWindowCoordinatorProtocol,
    ) -> None:
        super().__init__()
        self.view_model = view_model
        self.coordinator = coordinator
        self.state = self.view_model.load_initial_state()

        self.filter_widgets: dict[str, QComboBox] = {}
        self.page_size_combo: QComboBox | None = None
        self.page_indicator: QLabel | None = None
        self.statusbar: QStatusBar | None = None
        self.table = QTableView()
        self.table_model = ProductionTableModel(ALL_COLUMNS)

        self._setup_ui()
        self._sync_state_to_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Gerenciador de Produções")
        self.setMinimumSize(1400, 750)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        layout.addWidget(self._create_filter_group())
        layout.addLayout(self._create_action_buttons())

        summary_button_layout = QHBoxLayout()
        btn_clients = QPushButton("Clientes")
        btn_clients.setObjectName("secondaryButton")
        btn_clients.setIcon(Icons.user())
        btn_clients.clicked.connect(self._open_clients_overview)
        btn_clients.setMaximumWidth(140)
        summary_button_layout.addWidget(btn_clients)

        btn_summary = QPushButton("Exibir Resumo Financeiro")
        btn_summary.setObjectName("secondaryButton")
        btn_summary.setIcon(Icons.money())
        btn_summary.clicked.connect(self._show_financial_summary)
        btn_summary.setMaximumWidth(200)
        summary_button_layout.addWidget(btn_summary)
        summary_button_layout.addStretch()
        layout.addLayout(summary_button_layout)

        layout.addLayout(self._create_pagination_bar())

        self.table.setModel(self.table_model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)

        header = self.table.horizontalHeader()
        if header is None:
            raise RuntimeError("A tabela principal não retornou cabeçalho horizontal.")
        header.setStretchLastSection(True)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        for index, column_name in enumerate(ALL_COLUMNS):
            mode = (
                QHeaderView.ResizeMode.Stretch
                if column_name in {"Nome", "Cliente"}
                else QHeaderView.ResizeMode.ResizeToContents
            )
            header.setSectionResizeMode(index, mode)

        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self._show_header_context_menu)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._edit_selected_production)

        layout.addWidget(self.table)
        self._create_menus()
        self._create_statusbar()

    def _create_filter_group(self) -> QGroupBox:
        group = QGroupBox("Filtros")
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        for label_text, key, width in (
            ("Cliente:", "cliente", 150),
            ("Tipo:", "tipo", 120),
            ("Ano:", "ano", 90),
            ("Mês:", "mes", 90),
            ("Pagamento:", "status_pagamento", 120),
        ):
            layout.addWidget(QLabel(label_text))
            combo = QComboBox()
            combo.addItem("Todos")
            combo.setMinimumWidth(width)
            combo.currentTextChanged.connect(self._apply_filters)
            self.filter_widgets[key] = combo
            layout.addWidget(combo)

        for mes in range(1, 13):
            self.filter_widgets["mes"].addItem(f"{mes:02d}")
        self.filter_widgets["status_pagamento"].addItems(["Todos", "Em aberto", "Parcial", "Pago"])

        layout.addStretch()

        btn_clear_filters = QPushButton("Limpar Filtros")
        btn_clear_filters.setObjectName("secondaryButton")
        btn_clear_filters.setIcon(Icons.delete(Icons.COLOR_SECONDARY))
        btn_clear_filters.clicked.connect(self._clear_filters)
        layout.addWidget(btn_clear_filters)

        group.setLayout(layout)
        return group

    def _create_pagination_bar(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        self.page_size_combo = QComboBox()
        for option in PAGE_SIZE_OPTIONS:
            self.page_size_combo.addItem(str(option), option)
        idx = self.page_size_combo.findData(self.state.page_size or DEFAULT_PAGE_SIZE)
        self.page_size_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.page_size_combo.currentIndexChanged.connect(self._on_page_size_changed)
        layout.addWidget(QLabel("Itens por página:"))
        layout.addWidget(self.page_size_combo)

        btn_prev = QPushButton("Página anterior")
        btn_prev.setObjectName("secondaryButton")
        btn_prev.clicked.connect(self._go_prev_page)
        layout.addWidget(btn_prev)

        self.page_indicator = QLabel("Página 1/1")
        self.page_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.page_indicator)

        btn_next = QPushButton("Próxima página")
        btn_next.setObjectName("secondaryButton")
        btn_next.clicked.connect(self._go_next_page)
        layout.addWidget(btn_next)

        layout.addStretch()
        return layout

    def _create_action_buttons(self) -> QHBoxLayout:
        layout = QHBoxLayout()

        btn_add = QPushButton("Adicionar Produção")
        btn_add.setObjectName("successButton")
        btn_add.setIcon(Icons.add())
        btn_add.setMinimumWidth(200)
        btn_add.setMinimumHeight(40)
        btn_add.clicked.connect(self._add_production)
        layout.addWidget(btn_add)

        btn_pdf = QPushButton("Gerar PDF (Em Aberto)")
        btn_pdf.setObjectName("blueActionButton")
        btn_pdf.setIcon(Icons.pdf())
        btn_pdf.setMinimumWidth(200)
        btn_pdf.setMinimumHeight(40)
        btn_pdf.clicked.connect(self._generate_pdf)
        layout.addWidget(btn_pdf)

        layout.addStretch()
        return layout

    def _create_menus(self) -> None:
        menubar = self.menuBar()
        if menubar is None:
            raise RuntimeError("A janela principal não retornou menu bar.")

        menu_file = menubar.addMenu("&Arquivo")
        if menu_file is None:
            raise RuntimeError("Não foi possível criar o menu Arquivo.")
        action_exit = QAction("Sair", self)
        action_exit.setShortcut(QKeySequence.StandardKey.Quit)
        action_exit.setIcon(Icons.close())
        action_exit.triggered.connect(self.close)
        menu_file.addAction(action_exit)

        menu_production = menubar.addMenu("&Produção")
        if menu_production is None:
            raise RuntimeError("Não foi possível criar o menu Produção.")
        action_add = QAction("Nova Produção", self)
        action_add.setShortcut(QKeySequence("Ctrl+N"))
        action_add.setIcon(Icons.add(Icons.COLOR_SECONDARY))
        action_add.triggered.connect(self._add_production)
        menu_production.addAction(action_add)

        action_edit = QAction("Editar", self)
        action_edit.setShortcut(QKeySequence("Return"))
        action_edit.setIcon(Icons.edit(Icons.COLOR_SECONDARY))
        action_edit.triggered.connect(self._edit_selected_production)
        menu_production.addAction(action_edit)

        action_delete = QAction("Remover", self)
        action_delete.setShortcut(QKeySequence.StandardKey.Delete)
        action_delete.setIcon(Icons.delete(Icons.COLOR_SECONDARY))
        action_delete.triggered.connect(self._delete_selected_productions)
        menu_production.addAction(action_delete)
        menu_production.addSeparator()

        action_refresh = QAction("Atualizar", self)
        action_refresh.setShortcut(QKeySequence("F5"))
        action_refresh.setIcon(Icons.refresh(Icons.COLOR_SECONDARY))
        action_refresh.triggered.connect(self._reload_state)
        menu_production.addAction(action_refresh)

        menu_reports = menubar.addMenu("&Relatórios")
        if menu_reports is None:
            raise RuntimeError("Não foi possível criar o menu Relatórios.")
        action_pdf = QAction("Gerar PDF", self)
        action_pdf.setIcon(Icons.pdf(Icons.COLOR_SECONDARY))
        action_pdf.triggered.connect(self._generate_pdf)
        menu_reports.addAction(action_pdf)

        action_summary = QAction("Resumo Financeiro", self)
        action_summary.setShortcut(QKeySequence("Ctrl+R"))
        action_summary.setIcon(Icons.money(Icons.COLOR_SECONDARY))
        action_summary.triggered.connect(self._show_financial_summary)
        menu_reports.addAction(action_summary)

        menu_clients = menubar.addMenu("&Clientes")
        if menu_clients is None:
            raise RuntimeError("Não foi possível criar o menu Clientes.")
        action_clients = QAction("Painel de Clientes", self)
        action_clients.setShortcut(QKeySequence("Ctrl+L"))
        action_clients.setIcon(Icons.user(Icons.COLOR_SECONDARY))
        action_clients.triggered.connect(self._open_clients_overview)
        menu_clients.addAction(action_clients)

        menu_settings = menubar.addMenu("&Configurações")
        if menu_settings is None:
            raise RuntimeError("Não foi possível criar o menu Configurações.")
        action_settings = QAction("Configurações Gerais", self)
        action_settings.setShortcut(QKeySequence("Ctrl+G"))
        action_settings.setIcon(Icons.settings(Icons.COLOR_SECONDARY))
        action_settings.triggered.connect(self._open_settings)
        menu_settings.addAction(action_settings)

    def _create_statusbar(self) -> None:
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self._update_statusbar()

    def _update_statusbar(self) -> None:
        if self.statusbar is None:
            return
        inicio = 0 if not self.state.total_items else ((self.state.current_page - 1) * self.state.page_size) + 1
        fim = min(self.state.current_page * self.state.page_size, self.state.total_items)
        self.statusbar.showMessage(
            f"Mostrando {inicio}-{fim} de {self.state.total_items} produções | "
            f"Página {self.state.current_page}/{self.state.total_pages}"
        )

    def _sync_state_to_ui(self) -> None:
        self._sync_table_rows()
        self._update_filter_options()
        self._update_pagination_widgets()
        self._apply_column_visibility(self.state.visible_columns, persist=False)
        self._update_statusbar()

    def _sync_table_rows(self) -> None:
        self.table_model.set_items(ProductionPresentationMapper.to_table_rows(self.state.producoes))

    def _update_filter_options(self) -> None:
        self._update_combo("cliente", self.state.clientes_list)
        self._update_combo("tipo", self.state.tipos_producao)
        self._update_combo("ano", [str(ano) for ano in self.state.anos_disponiveis])

    def _update_combo(self, key: str, values: list[str]) -> None:
        combo = self.filter_widgets.get(key)
        if combo is None:
            return
        current = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Todos")
        combo.addItems(sorted(values))
        index = combo.findText(current)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

    def _collect_filters(self) -> ProductionFilters:
        cliente = self.filter_widgets["cliente"].currentText()
        tipo = self.filter_widgets["tipo"].currentText()
        status_pag = self.filter_widgets["status_pagamento"].currentText()
        ano = self.filter_widgets["ano"].currentText()
        mes = self.filter_widgets["mes"].currentText()
        return ProductionFilters(
            cliente=cliente if cliente != "Todos" else None,
            tipo_producao=tipo if tipo != "Todos" else None,
            status_pagamento=status_pag if status_pag != "Todos" else None,
            ano=int(ano) if ano and ano != "Todos" else None,
            mes=int(mes) if mes and mes != "Todos" else None,
        )

    def _update_state(self, loader: Callable[[], MainWindowState]) -> None:
        self.state = loader()
        self._sync_state_to_ui()

    def _reload_state(self) -> None:
        self._update_state(self.view_model.load_page)

    def _apply_filters(self, *_args) -> None:
        self._update_state(lambda: self.view_model.set_filters(self._collect_filters()))

    def _reset_filter_widgets(self) -> None:
        for key in ("cliente", "tipo", "status_pagamento", "ano", "mes"):
            widget = self.filter_widgets.get(key)
            if widget is None:
                continue
            widget.blockSignals(True)
            widget.setCurrentIndex(0)
            widget.blockSignals(False)

    def _clear_filters(self) -> None:
        self._reset_filter_widgets()
        self._update_state(self.view_model.clear_filters)

    def _on_page_size_changed(self, *_args) -> None:
        if self.page_size_combo is None:
            return
        page_size = int(self.page_size_combo.currentData() or self.page_size_combo.currentText())
        self._update_state(lambda: self.view_model.set_page_size(page_size))

    def _go_prev_page(self) -> None:
        self._update_state(self.view_model.previous_page)

    def _go_next_page(self) -> None:
        self._update_state(self.view_model.next_page)

    def _update_pagination_widgets(self) -> None:
        if self.page_indicator is not None:
            self.page_indicator.setText(f"Página {self.state.current_page}/{self.state.total_pages}")

    def _show_context_menu(self, position) -> None:
        menu = QMenu()
        action_edit = menu.addAction("Editar")
        if action_edit is not None:
            action_edit.setIcon(Icons.edit(Icons.COLOR_SECONDARY))
            action_edit.triggered.connect(self._edit_selected_production)

        action_delete = menu.addAction("Remover")
        if action_delete is not None:
            action_delete.setIcon(Icons.delete(Icons.COLOR_SECONDARY))
            action_delete.triggered.connect(self._delete_selected_productions)

        viewport = self.table.viewport()
        if viewport is not None:
            menu.exec(viewport.mapToGlobal(position))

    def _show_header_context_menu(self, position) -> None:
        menu = QMenu()
        action_manage_columns = menu.addAction("Gerenciar Colunas Visíveis")
        if action_manage_columns is not None:
            action_manage_columns.setIcon(Icons.settings(Icons.COLOR_SECONDARY))
            action_manage_columns.triggered.connect(self._open_column_visibility_dialog)
        header = self.table.horizontalHeader()
        if header is not None:
            menu.exec(header.mapToGlobal(position))

    def _open_column_visibility_dialog(self) -> None:
        dialog = ColumnVisibilityDialog(
            self,
            all_columns=ALL_COLUMNS,
            visible_columns=self.state.visible_columns,
            on_save=self._on_visible_columns_changed,
        )
        dialog.exec()

    def _on_visible_columns_changed(self, visible_columns: list[str]) -> None:
        self.view_model.save_visible_columns(visible_columns)
        self.state.visible_columns = visible_columns
        self._apply_column_visibility(visible_columns, persist=False)

    def _apply_column_visibility(self, visible_columns: list[str], *, persist: bool) -> None:
        if persist:
            self.view_model.save_visible_columns(visible_columns)
        self.state.visible_columns = visible_columns
        for index, column_name in enumerate(ALL_COLUMNS):
            self.table.setColumnHidden(index, column_name not in visible_columns)

    def _selected_production_ids(self) -> list[int]:
        ids: list[int] = []
        selection_model = self.table.selectionModel()
        if selection_model is None:
            return ids
        for index in selection_model.selectedRows():
            row = self.table_model.row_at(index.row())
            if row is not None:
                ids.append(row.production_id)
        return ids

    def _selected_single_production_id(self) -> int | None:
        ids = self._selected_production_ids()
        if len(ids) != 1:
            return None
        return ids[0]

    def _add_production(self) -> None:
        if self.coordinator.open_add_production(self, self.state.tipos_producao, self.state.clientes_list):
            self._reload_state()

    def _edit_selected_production(self) -> None:
        ids = self._selected_production_ids()
        if not ids:
            QMessageBox.warning(self, "Nenhuma Seleção", "Selecione uma produção para editar.")
            return
        if len(ids) > 1:
            QMessageBox.warning(self, "Múltiplas Seleções", "Selecione apenas uma produção para editar.")
            return
        production_id = self._selected_single_production_id()
        if production_id is None:
            return
        if self.coordinator.open_edit_production(
            self,
            production_id,
            self.state.tipos_producao,
            self.state.clientes_list,
        ):
            self._reload_state()

    def _delete_selected_productions(self) -> None:
        ids = self._selected_production_ids()
        if not ids:
            QMessageBox.warning(self, "Nenhuma Seleção", "Selecione uma ou mais produções para remover.")
            return

        reply = QMessageBox.question(
            self,
            "Confirmar Remoção",
            f"Tem certeza que deseja remover {len(ids)} produção(ões)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        try:
            result = self.view_model.delete(ids)
        finally:
            QApplication.restoreOverrideCursor()

        self._reload_state()
        if result.success:
            QMessageBox.information(self, "Sucesso", f"{result.data or 0} produção(ões) removida(s) com sucesso!")
        else:
            QMessageBox.critical(self, "Erro", result.message)

    def _generate_pdf(self) -> None:
        if self.coordinator.open_open_report_dialog(self):
            self._reload_state()

    def _show_financial_summary(self) -> None:
        self.coordinator.open_financial_summary(self)

    def _open_clients_overview(self) -> None:
        if self.coordinator.open_clients_dialog(self):
            self._reload_state()

    def _open_settings(self) -> None:
        dialog = SettingsDialog(
            self,
            on_manage_types=self._manage_types,
            on_configure_pix=self._configure_pix,
            on_configure_columns=self._open_column_visibility_dialog,
            on_manual_backup=self._create_manual_backup,
        )
        dialog.exec()

    def _manage_types(self) -> None:
        dialog = ManageTypesDialog(
            self,
            tipos_producao=self.state.tipos_producao,
            on_add=lambda nome: self.view_model.add_type(nome).success,
            on_remove=lambda nome: self.view_model.remove_type(nome).success,
        )
        dialog.exec()
        self.state.tipos_producao = dialog.get_tipos()
        self._update_filter_options()

    def _configure_pix(self) -> None:
        pix_settings = self.coordinator.load_pix_settings()
        dialog = PixConfigDialog(
            self,
            current_config=pix_settings.to_dict(),
            on_save=self.coordinator.save_pix_settings,
        )
        dialog.exec()

    def _create_manual_backup(self) -> None:
        result = self.view_model.create_manual_backup()
        if result.success and result.output_path:
            QMessageBox.information(self, "Backup", f"Backup criado com sucesso:\n{result.output_path}")
            return
        QMessageBox.warning(self, "Backup", result.message)
