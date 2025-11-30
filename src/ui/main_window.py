# -*- coding: utf-8 -*-
"""
Janela Principal do Gerenciador de Produções - PyQt6
"""
import logging
from typing import List, Dict, Any
from datetime import datetime
import time

from PyQt6.QtWidgets import (
    QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout,
    QWidget, QHeaderView, QMessageBox, QMenu, QToolBar, QStatusBar,
    QPushButton, QLabel, QComboBox, QGroupBox, QFrame, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence, QCursor

from .icons import Icons
from .dialogs.production_form import ProductionFormDialog
from .dialogs.settings import SettingsDialog
from .dialogs.manage_types import ManageTypesDialog
from .dialogs.pix_config import PixConfigDialog
from .dialogs.column_visibility import ColumnVisibilityDialog
from .dialogs.relatorio_aberto_dialog import RelatorioAbertoDialog
from .dialogs.financial_summary import FinancialSummaryDialog

from ..core.database import DatabaseManager
from ..core.pdf_generator import PDFGenerator
from ..config.constants import ALL_COLUMNS, DATE_COLUMNS, DEFAULT_VISIBLE_COLUMNS, DATA_DIR

logger = logging.getLogger(__name__)

# Colunas de valores monetários
MONEY_COLUMNS = ["Valor por Foto", "Valor por Kit", "Valor por Capa", "Valor Total"]


class NumericTableWidgetItem(QTableWidgetItem):
    """Item customizado para ordenação numérica correta"""

    def __init__(self, text, sort_value=None):
        super().__init__(text)
        self._sort_value = sort_value if sort_value is not None else text

    def __lt__(self, other):
        """Comparação para ordenação"""
        try:
            # Se ambos têm valores de ordenação, comparar eles
            if hasattr(self, '_sort_value') and hasattr(other, '_sort_value'):
                # Tentar converter para float para comparação numérica
                if isinstance(self._sort_value, (int, float)) and isinstance(other._sort_value, (int, float)):
                    return float(self._sort_value) < float(other._sort_value)
                # Senão, comparar como string
                return str(self._sort_value) < str(other._sort_value)
            # Fallback para comparação padrão
            return super().__lt__(other)
        except:
            return super().__lt__(other)


class MainWindow(QMainWindow):
    """Janela principal do aplicativo"""

    def __init__(self):
        super().__init__()

        # Banco de dados
        self.db = DatabaseManager()

        # Dados
        self.producoes: List[Dict[str, Any]] = []
        self.tipos_producao: List[str] = []
        self.clientes_list: List[str] = []

        # Widgets
        self.table: QTableWidget = None
        self.filter_widgets = {}  # Armazena widgets de filtro

        # Configuração de colunas visíveis
        self.visible_columns: List[str] = DEFAULT_VISIBLE_COLUMNS.copy()

        # Dados filtrados
        self.filtered_producoes: List[Dict[str, Any]] = []

        self._load_initial_data()
        self._setup_ui()
        self._apply_initial_column_visibility()
        self._load_table_data()

    def _load_initial_data(self):
        """Carrega dados iniciais do banco"""
        try:
            self.tipos_producao = self.db.listar_tipos_producao()
            if not self.tipos_producao:
                for tipo in ['Formatura', 'Newborn', 'Casamento']:
                    self.db.adicionar_tipo_producao(tipo)
                self.tipos_producao = self.db.listar_tipos_producao()

            self.clientes_list = self.db.obter_clientes_unicos()
            logger.info("Dados iniciais carregados com sucesso")
        except Exception as e:
            logger.error(f"Erro ao carregar dados iniciais: {e}", exc_info=True)

    def _setup_ui(self):
        """Configura a interface principal"""
        self.setWindowTitle("Gerenciador de Produções")
        self.setMinimumSize(1400, 750)

        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Área de filtros
        filter_group = self._create_filter_group()
        layout.addWidget(filter_group)

        # Botões de ação principais
        action_buttons = self._create_action_buttons()
        layout.addLayout(action_buttons)

        # Botão de resumo financeiro
        summary_button_layout = QHBoxLayout()
        btn_summary = QPushButton("Exibir Resumo Financeiro")
        btn_summary.setObjectName("secondaryButton")
        btn_summary.setIcon(Icons.money())
        btn_summary.clicked.connect(self._show_financial_summary)
        btn_summary.setMaximumWidth(200)
        summary_button_layout.addWidget(btn_summary)
        summary_button_layout.addStretch()
        layout.addLayout(summary_button_layout)

        # Tabela
        self.table = QTableWidget()
        self.table.setColumnCount(len(ALL_COLUMNS))
        self.table.setHorizontalHeaderLabels(ALL_COLUMNS)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Ajustar colunas para ocupar toda a largura
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)  # Última coluna visível estica para preencher espaço
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)  # Centralizar cabeçalhos

        # Configurar redimensionamento de colunas
        for i, column_name in enumerate(ALL_COLUMNS):
            # Colunas principais que devem ter mais espaço
            if column_name in ['Nome', 'Cliente']:
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            # Outras colunas ajustam ao conteúdo
            else:
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        # Habilitar ordenação clicando nos cabeçalhos
        self.table.setSortingEnabled(True)

        # Menu de contexto no header (cabeçalho)
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self._show_header_context_menu)

        # Double-click para editar
        self.table.doubleClicked.connect(self._edit_selected_production)

        # Menu de contexto na tabela
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self.table)

        # Criar menus
        self._create_menus()
        self._create_statusbar()

    def _create_filter_group(self) -> QGroupBox:
        """Cria o grupo de filtros"""
        group = QGroupBox("Filtros")
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # Filtro por Cliente
        label_cliente = QLabel("Cliente:")
        layout.addWidget(label_cliente)

        filter_cliente = QComboBox()
        filter_cliente.addItem("Todos")
        filter_cliente.setMinimumWidth(150)
        filter_cliente.currentTextChanged.connect(self._apply_filters)
        self.filter_widgets['cliente'] = filter_cliente
        layout.addWidget(filter_cliente)

        # Filtro por Tipo de Produção
        label_tipo = QLabel("Tipo:")
        layout.addWidget(label_tipo)

        filter_tipo = QComboBox()
        filter_tipo.addItem("Todos")
        filter_tipo.setMinimumWidth(120)
        filter_tipo.currentTextChanged.connect(self._apply_filters)
        self.filter_widgets['tipo'] = filter_tipo
        layout.addWidget(filter_tipo)

        # Filtro por Status de Pagamento
        label_status_pag = QLabel("Pagamento:")
        layout.addWidget(label_status_pag)

        filter_status_pag = QComboBox()
        filter_status_pag.addItems(["Todos", "Em aberto", "Pago"])
        filter_status_pag.setMinimumWidth(120)
        filter_status_pag.currentTextChanged.connect(self._apply_filters)
        self.filter_widgets['status_pagamento'] = filter_status_pag
        layout.addWidget(filter_status_pag)

        layout.addStretch()

        # Botão limpar filtros
        btn_clear_filters = QPushButton("Limpar Filtros")
        btn_clear_filters.setObjectName("secondaryButton")
        btn_clear_filters.setIcon(Icons.delete(Icons.COLOR_SECONDARY))
        btn_clear_filters.clicked.connect(self._clear_filters)
        layout.addWidget(btn_clear_filters)

        group.setLayout(layout)
        return group

    def _create_action_buttons(self) -> QHBoxLayout:
        """Cria os botões de ação principais"""
        layout = QHBoxLayout()

        # Botão Adicionar Produção (Verde)
        btn_add = QPushButton("Adicionar Produção")
        btn_add.setObjectName("successButton")
        btn_add.setIcon(Icons.add())
        btn_add.setMinimumWidth(200)
        btn_add.setMinimumHeight(40)
        btn_add.clicked.connect(self._add_production)
        layout.addWidget(btn_add)

        # Botão Gerar PDF (Azul)
        btn_pdf = QPushButton("Gerar PDF (Em Aberto)")
        btn_pdf.setObjectName("blueActionButton")
        btn_pdf.setIcon(Icons.pdf())
        btn_pdf.setMinimumWidth(200)
        btn_pdf.setMinimumHeight(40)
        btn_pdf.clicked.connect(self._generate_pdf)
        layout.addWidget(btn_pdf)

        layout.addStretch()

        return layout

    def _create_menus(self):
        """Cria a barra de menus"""
        menubar = self.menuBar()

        # Menu Arquivo
        menu_file = menubar.addMenu("&Arquivo")

        action_exit = QAction("Sair", self)
        action_exit.setShortcut(QKeySequence.StandardKey.Quit)
        action_exit.setIcon(Icons.close())
        action_exit.triggered.connect(self.close)
        menu_file.addAction(action_exit)

        # Menu Produção
        menu_production = menubar.addMenu("&Produção")

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
        action_refresh.triggered.connect(self._load_table_data)
        menu_production.addAction(action_refresh)

        # Menu Relatórios
        menu_reports = menubar.addMenu("&Relatórios")

        action_pdf = QAction("Gerar PDF", self)
        action_pdf.setIcon(Icons.pdf(Icons.COLOR_SECONDARY))
        action_pdf.triggered.connect(self._generate_pdf)
        menu_reports.addAction(action_pdf)

        action_summary = QAction("Resumo Financeiro", self)
        action_summary.setShortcut(QKeySequence("Ctrl+R"))
        action_summary.setIcon(Icons.money(Icons.COLOR_SECONDARY))
        action_summary.triggered.connect(self._show_financial_summary)
        menu_reports.addAction(action_summary)

        # Menu Configurações
        menu_settings = menubar.addMenu("&Configurações")

        action_settings = QAction("Configurações Gerais", self)
        action_settings.setShortcut(QKeySequence("Ctrl+G"))
        action_settings.setIcon(Icons.settings(Icons.COLOR_SECONDARY))
        action_settings.triggered.connect(self._open_settings)
        menu_settings.addAction(action_settings)

    def _create_statusbar(self):
        """Cria a barra de status"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self._update_statusbar()

    def _update_statusbar(self):
        """Atualiza a barra de status"""
        total = len(self.producoes)
        self.statusbar.showMessage(f"Total de produções: {total}")

    def _show_context_menu(self, position):
        """Exibe menu de contexto na tabela"""
        menu = QMenu()

        action_edit = menu.addAction("Editar")
        action_edit.setIcon(Icons.edit(Icons.COLOR_SECONDARY))
        action_edit.triggered.connect(self._edit_selected_production)

        action_delete = menu.addAction("Remover")
        action_delete.setIcon(Icons.delete(Icons.COLOR_SECONDARY))
        action_delete.triggered.connect(self._delete_selected_productions)

        menu.exec(self.table.viewport().mapToGlobal(position))

    def _show_header_context_menu(self, position):
        """Exibe menu de contexto no cabeçalho da tabela"""
        menu = QMenu()

        action_manage_columns = menu.addAction("Gerenciar Colunas Visíveis")
        action_manage_columns.setIcon(Icons.settings(Icons.COLOR_SECONDARY))
        action_manage_columns.triggered.connect(self._open_column_visibility_dialog)

        # Executar menu na posição do header
        header = self.table.horizontalHeader()
        menu.exec(header.mapToGlobal(position))

    def _open_column_visibility_dialog(self):
        """Abre o diálogo de gerenciamento de colunas"""
        dialog = ColumnVisibilityDialog(
            self,
            all_columns=ALL_COLUMNS,
            visible_columns=self.visible_columns,
            on_save=self._apply_column_visibility
        )
        dialog.exec()

    def _apply_column_visibility(self, visible_columns: List[str]):
        """Aplica a visibilidade das colunas selecionadas"""
        try:
            self.visible_columns = visible_columns

            # Ocultar todas as colunas primeiro
            for i, column_name in enumerate(ALL_COLUMNS):
                if column_name not in visible_columns:
                    self.table.setColumnHidden(i, True)
                else:
                    self.table.setColumnHidden(i, False)

            logger.info(f"Visibilidade de colunas atualizada: {len(visible_columns)} visíveis")

            # Opcional: salvar preferências em arquivo ou banco
            # TODO: Implementar salvamento de preferências

        except Exception as e:
            logger.error(f"Erro ao aplicar visibilidade de colunas: {e}", exc_info=True)
            QMessageBox.warning(self, "Erro", f"Erro ao aplicar visibilidade: {e}")

    def _apply_initial_column_visibility(self):
        """Aplica a visibilidade inicial das colunas"""
        for i, column_name in enumerate(ALL_COLUMNS):
            if column_name not in self.visible_columns:
                self.table.setColumnHidden(i, True)

    def _update_filter_options(self):
        """Atualiza as opções dos filtros baseado nos dados"""
        # Atualizar filtro de clientes
        filter_cliente = self.filter_widgets.get('cliente')
        if filter_cliente:
            current = filter_cliente.currentText()
            filter_cliente.blockSignals(True)
            filter_cliente.clear()
            filter_cliente.addItem("Todos")
            filter_cliente.addItems(sorted(self.clientes_list))
            # Restaurar seleção anterior se possível
            index = filter_cliente.findText(current)
            if index >= 0:
                filter_cliente.setCurrentIndex(index)
            filter_cliente.blockSignals(False)

        # Atualizar filtro de tipos
        filter_tipo = self.filter_widgets.get('tipo')
        if filter_tipo:
            current = filter_tipo.currentText()
            filter_tipo.blockSignals(True)
            filter_tipo.clear()
            filter_tipo.addItem("Todos")
            filter_tipo.addItems(sorted(self.tipos_producao))
            # Restaurar seleção anterior se possível
            index = filter_tipo.findText(current)
            if index >= 0:
                filter_tipo.setCurrentIndex(index)
            filter_tipo.blockSignals(False)

    def _apply_filters(self, refresh_display=True):
        """
        Aplica os filtros selecionados à tabela

        Args:
            refresh_display: Se True, atualiza a visualização da tabela (padrão: True)
                            Se False, apenas atualiza self.filtered_producoes sem redesenhar
        """
        try:
            # Obter valores dos filtros
            cliente_filter = self.filter_widgets.get('cliente').currentText()
            tipo_filter = self.filter_widgets.get('tipo').currentText()
            status_pag_filter = self.filter_widgets.get('status_pagamento').currentText()

            # Filtrar produções
            self.filtered_producoes = []
            for producao in self.producoes:
                # Verificar filtro de cliente
                if cliente_filter != "Todos" and producao.get('Cliente', '') != cliente_filter:
                    continue

                # Verificar filtro de tipo
                if tipo_filter != "Todos" and producao.get('Tipo de Produção', '') != tipo_filter:
                    continue

                # Verificar filtro de status de pagamento
                if status_pag_filter != "Todos" and producao.get('Status Pagamento', '') != status_pag_filter:
                    continue

                self.filtered_producoes.append(producao)

            # Atualizar tabela com dados filtrados (se solicitado)
            if refresh_display:
                self._refresh_table_display()

            logger.info(f"Filtros aplicados: {len(self.filtered_producoes)} de {len(self.producoes)} produções")

        except Exception as e:
            logger.error(f"Erro ao aplicar filtros: {e}", exc_info=True)

    def _clear_filters(self):
        """Limpa todos os filtros"""
        try:
            self.filter_widgets.get('cliente').setCurrentIndex(0)
            self.filter_widgets.get('tipo').setCurrentIndex(0)
            self.filter_widgets.get('status_pagamento').setCurrentIndex(0)
            logger.info("Filtros limpos")
        except Exception as e:
            logger.error(f"Erro ao limpar filtros: {e}", exc_info=True)

    def _load_table_data(self):
        """Carrega dados da tabela do banco"""
        try:
            # PERFORMANCE LOG - Início
            start_total = time.time()

            # Carregar dados do banco
            start_db = time.time()
            self.producoes = self.db.listar_producoes()
            self.filtered_producoes = self.producoes.copy()
            logger.info(f"[PERFORMANCE] Consulta SQL: {(time.time() - start_db)*1000:.2f}ms")

            # Atualizar opções dos filtros
            start_filters = time.time()
            self._update_filter_options()
            logger.info(f"[PERFORMANCE] Atualizar filtros: {(time.time() - start_filters)*1000:.2f}ms")

            # Atualizar visualização da tabela
            start_display = time.time()
            self._refresh_table_display()
            logger.info(f"[PERFORMANCE] Atualizar display: {(time.time() - start_display)*1000:.2f}ms")

            logger.info(f"[PERFORMANCE] Tempo total _load_table_data: {(time.time() - start_total)*1000:.2f}ms")
            logger.info(f"Dados carregados: {len(self.producoes)} produções")

        except Exception as e:
            logger.error(f"Erro ao carregar dados da tabela: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao carregar dados: {e}")

    def _refresh_table_display(self):
        """Atualiza a visualização da tabela com os dados filtrados"""
        try:
            # PERFORMANCE LOG
            start_total = time.time()

            # OTIMIZAÇÃO 3: Bloquear atualizações da interface e viewport durante carregamento
            self.table.setUpdatesEnabled(False)
            self.table.viewport().setUpdatesEnabled(False)  # ✅ OTIMIZAÇÃO 3: Viewport também
            self.table.setSortingEnabled(False)

            start_setup = time.time()
            self.table.setRowCount(len(self.filtered_producoes))
            logger.info(f"[PERFORMANCE] setRowCount: {(time.time() - start_setup)*1000:.2f}ms")

            # OTIMIZAÇÃO 2: Cache de formatação
            money_cache = {}  # Cache para valores monetários
            date_cache = {}   # Cache para datas

            start_items = time.time()
            for row, producao in enumerate(self.filtered_producoes):
                producao_id = producao.get('ID')

                for col, column_name in enumerate(ALL_COLUMNS):
                    value = producao.get(column_name, '')
                    item = None

                    # Formatar valores monetários
                    if column_name in MONEY_COLUMNS:
                        if value and value not in (None, '', 'None', 'nan'):
                            try:
                                numeric_value = float(value)
                                # OTIMIZAÇÃO 2: Usar cache para formatação monetária
                                if numeric_value not in money_cache:
                                    money_cache[numeric_value] = f"R$ {numeric_value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                                display_value = money_cache[numeric_value]
                                item = NumericTableWidgetItem(display_value, numeric_value)
                            except (ValueError, TypeError):
                                item = NumericTableWidgetItem("R$ 0,00", 0.0)
                        else:
                            item = NumericTableWidgetItem("R$ 0,00", 0.0)

                    # Formatar datas
                    elif column_name in DATE_COLUMNS:
                        if value and value not in (None, '', 'None', 'nan'):
                            try:
                                if isinstance(value, str):
                                    date_part = value.split()[0] if ' ' in value else value
                                    # OTIMIZAÇÃO 2: Usar cache para formatação de datas
                                    if date_part not in date_cache:
                                        date_obj = datetime.strptime(date_part, '%Y-%m-%d')
                                        date_cache[date_part] = (date_obj.strftime('%d/%m/%Y'), date_obj.timestamp())
                                    display_value, timestamp = date_cache[date_part]
                                    item = NumericTableWidgetItem(display_value, timestamp)
                                else:
                                    display_value = value.strftime('%d/%m/%Y') if hasattr(value, 'strftime') else str(value)
                                    sort_val = value.timestamp() if hasattr(value, 'timestamp') else float('inf')
                                    item = NumericTableWidgetItem(display_value, sort_val)
                            except (ValueError, TypeError, AttributeError):
                                # Datas inválidas aparecem no final ao ordenar
                                item = NumericTableWidgetItem(str(value) if value else '', float('inf'))
                        else:
                            # Datas vazias aparecem no final ao ordenar
                            item = NumericTableWidgetItem('', float('inf'))

                    # Colunas de quantidade
                    elif column_name.startswith("Quant."):
                        if value and value not in (None, '', 'None', 'nan'):
                            try:
                                numeric_val = int(value)
                                item = NumericTableWidgetItem(str(numeric_val), numeric_val)
                            except (ValueError, TypeError):
                                item = NumericTableWidgetItem('0', 0)
                        else:
                            item = NumericTableWidgetItem('0', 0)

                    # Outros valores (texto)
                    else:
                        display_value = str(value) if value not in (None, '', 'None', 'nan') else ''
                        item = QTableWidgetItem(display_value)

                    # OTIMIZAÇÃO 1: Armazenar ID apenas na primeira coluna
                    if col == 0:
                        item.setData(Qt.ItemDataRole.UserRole, producao_id)

                    # Centralizar conteúdo da célula
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    self.table.setItem(row, col, item)

            logger.info(f"[PERFORMANCE] Criar items da tabela: {(time.time() - start_items)*1000:.2f}ms")

            # OTIMIZAÇÃO 3: Reabilitar atualizações de viewport e tabela
            start_redraw = time.time()
            self.table.setSortingEnabled(True)
            self.table.viewport().setUpdatesEnabled(True)
            self.table.setUpdatesEnabled(True)
            logger.info(f"[PERFORMANCE] Reabilitar updates: {(time.time() - start_redraw)*1000:.2f}ms")

            self._update_statusbar()

            logger.info(f"[PERFORMANCE] Tempo total _refresh_table_display: {(time.time() - start_total)*1000:.2f}ms")

        except Exception as e:
            logger.error(f"Erro ao atualizar visualização da tabela: {e}", exc_info=True)
            # Garantir que as atualizações sejam reativadas mesmo em caso de erro
            self.table.viewport().setUpdatesEnabled(True)
            self.table.setUpdatesEnabled(True)

    def _update_single_row(self, row_index: int, producao: Dict[str, Any]):
        """
        OTIMIZAÇÃO 4: Atualiza apenas uma linha específica da tabela.
        Muito mais rápido que recriar toda a tabela (17 células vs 4,000+ células).

        Args:
            row_index: Índice da linha na tabela filtrada
            producao: Dicionário com os dados da produção
        """
        try:
            producao_id = producao.get('ID')

            # Cache de formatação (otimização 2 aplicada aqui também)
            money_cache = {}
            date_cache = {}

            for col, column_name in enumerate(ALL_COLUMNS):
                value = producao.get(column_name, '')
                item = None

                # Formatar valores monetários
                if column_name in MONEY_COLUMNS:
                    if value and value not in (None, '', 'None', 'nan'):
                        try:
                            numeric_value = float(value)
                            if numeric_value not in money_cache:
                                money_cache[numeric_value] = f"R$ {numeric_value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                            display_value = money_cache[numeric_value]
                            item = NumericTableWidgetItem(display_value, numeric_value)
                        except (ValueError, TypeError):
                            item = NumericTableWidgetItem("R$ 0,00", 0.0)
                    else:
                        item = NumericTableWidgetItem("R$ 0,00", 0.0)

                # Formatar datas
                elif column_name in DATE_COLUMNS:
                    if value and value not in (None, '', 'None', 'nan'):
                        try:
                            if isinstance(value, str):
                                date_part = value.split()[0] if ' ' in value else value
                                if date_part not in date_cache:
                                    date_obj = datetime.strptime(date_part, '%Y-%m-%d')
                                    date_cache[date_part] = (date_obj.strftime('%d/%m/%Y'), date_obj.timestamp())
                                display_value, timestamp = date_cache[date_part]
                                item = NumericTableWidgetItem(display_value, timestamp)
                            else:
                                display_value = value.strftime('%d/%m/%Y') if hasattr(value, 'strftime') else str(value)
                                sort_val = value.timestamp() if hasattr(value, 'timestamp') else float('inf')
                                item = NumericTableWidgetItem(display_value, sort_val)
                        except (ValueError, TypeError, AttributeError):
                            item = NumericTableWidgetItem(str(value) if value else '', float('inf'))
                    else:
                        item = NumericTableWidgetItem('', float('inf'))

                # Colunas de quantidade
                elif column_name.startswith("Quant."):
                    if value and value not in (None, '', 'None', 'nan'):
                        try:
                            numeric_val = int(value)
                            item = NumericTableWidgetItem(str(numeric_val), numeric_val)
                        except (ValueError, TypeError):
                            item = NumericTableWidgetItem('0', 0)
                    else:
                        item = NumericTableWidgetItem('0', 0)

                # Outros valores (texto)
                else:
                    display_value = str(value) if value not in (None, '', 'None', 'nan') else ''
                    item = QTableWidgetItem(display_value)

                # OTIMIZAÇÃO 1: Armazenar ID apenas na primeira coluna
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, producao_id)

                # Centralizar conteúdo da célula
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                self.table.setItem(row_index, col, item)

            logger.debug(f"Linha {row_index} atualizada (ID: {producao_id})")

        except Exception as e:
            logger.error(f"Erro ao atualizar linha {row_index}: {e}", exc_info=True)

    def _add_production(self):
        """Abre diálogo para adicionar produção"""
        dialog = ProductionFormDialog(
            self,
            mode='add',
            tipos_producao=self.tipos_producao,
            clientes_list=self.clientes_list,
            on_save=self._save_new_production
        )
        dialog.exec()

    def _save_new_production(self, dados: Dict[str, Any]):
        """Salva nova produção no banco"""
        try:
            # Mostrar cursor de espera
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))

            db_data = {
                'cliente': dados.get('Cliente', ''),
                'nome': dados.get('Nome', ''),
                'tipo_producao': dados.get('Tipo de Produção', ''),
                'data_recebimento': dados.get('Data de Recebimento', ''),
                'data_conclusao': dados.get('Data de Conclusão'),
                'status': dados.get('Status', 'Parado'),
                'status_pagamento': dados.get('Status Pagamento', 'Em aberto'),
                'quantidade_alunos': dados.get('Quant. Alunos', 0),
                'quantidade_fotos': dados.get('Quant. Fotos', 0),
                'quantidade_kits': dados.get('Quant. Kits', 0),
                'quantidade_capas': dados.get('Quant. Capas', 0),
                'valor_por_foto': dados.get('Valor por Foto', 0.0),
                'valor_por_kit': dados.get('Valor por Kit', 0.0),
                'valor_por_capa': dados.get('Valor por Capa', 0.0),
                'pasta_producao': dados.get('pasta_producao', ''),
            }

            producao_id = self.db.adicionar_producao(db_data)

            # OTIMIZAÇÃO 5: Preservar filtros ao adicionar nova produção
            # Buscar produção recém-criada do banco
            producao_nova = self.db.obter_producao(producao_id)

            if producao_nova:
                # Adicionar à lista completa
                self.producoes.append(producao_nova)

                # Verificar se passa pelos filtros atuais
                cliente_filter = self.filter_widgets.get('cliente').currentText()
                tipo_filter = self.filter_widgets.get('tipo').currentText()
                status_pag_filter = self.filter_widgets.get('status_pagamento').currentText()

                passa_filtros = True
                if cliente_filter != "Todos" and producao_nova.get('Cliente', '') != cliente_filter:
                    passa_filtros = False
                if tipo_filter != "Todos" and producao_nova.get('Tipo de Produção', '') != tipo_filter:
                    passa_filtros = False
                if status_pag_filter != "Todos" and producao_nova.get('Status Pagamento', '') != status_pag_filter:
                    passa_filtros = False

                # Adicionar à visualização apenas se passar pelos filtros
                if passa_filtros:
                    self.filtered_producoes.append(producao_nova)
                    # Adicionar nova linha na tabela
                    row_index = len(self.filtered_producoes) - 1
                    self.table.setRowCount(len(self.filtered_producoes))
                    self._update_single_row(row_index, producao_nova)

                # Atualizar lista de clientes se necessário
                cliente_novo = producao_nova.get('Cliente', '')
                if cliente_novo and cliente_novo not in self.clientes_list:
                    self.clientes_list.append(cliente_novo)
                    self._update_filter_options()

                # Atualizar status bar
                self._update_statusbar()

            # Restaurar cursor normal antes de mostrar mensagem
            QApplication.restoreOverrideCursor()
            QMessageBox.information(self, "Sucesso", f"Produção adicionada com ID: {producao_id}")

        except Exception as e:
            QApplication.restoreOverrideCursor()
            logger.error(f"Erro ao adicionar produção: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao adicionar produção: {e}")

    def _edit_selected_production(self):
        """Edita a produção selecionada"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Nenhuma Seleção", "Selecione uma produção para editar.")
            return

        if len(selected_rows) > 1:
            QMessageBox.warning(self, "Múltiplas Seleções", "Selecione apenas uma produção para editar.")
            return

        # Recuperar o ID da produção armazenado na célula (independente da ordenação)
        row = selected_rows[0].row()
        item = self.table.item(row, 0)  # Pegar qualquer item da linha (coluna 0)
        producao_id = item.data(Qt.ItemDataRole.UserRole)

        # Buscar a produção completa pelo ID
        producao = self.db.obter_producao(producao_id)
        if not producao:
            QMessageBox.warning(self, "Erro", "Produção não encontrada no banco de dados.")
            return

        dialog = ProductionFormDialog(
            self,
            mode='edit',
            initial_data=producao,
            tipos_producao=self.tipos_producao,
            clientes_list=self.clientes_list,
            on_save=lambda dados: self._save_edited_production(producao_id, dados)
        )
        dialog.exec()

    def _save_edited_production(self, producao_id: int, dados: Dict[str, Any]):
        """Salva produção editada"""
        try:
            # PERFORMANCE LOG - Início
            start_total = time.time()
            logger.info(f"[PERFORMANCE] Iniciando salvamento da produção {producao_id}")

            # Mostrar cursor de espera
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))

            # PERFORMANCE LOG - Preparar dados
            start_prep = time.time()
            db_data = {
                'cliente': dados.get('Cliente', ''),
                'nome': dados.get('Nome', ''),
                'tipo_producao': dados.get('Tipo de Produção', ''),
                'data_recebimento': dados.get('Data de Recebimento', ''),
                'data_conclusao': dados.get('Data de Conclusão'),
                'status': dados.get('Status', 'Parado'),
                'status_pagamento': dados.get('Status Pagamento', 'Em aberto'),
                'quantidade_alunos': dados.get('Quant. Alunos', 0),
                'quantidade_fotos': dados.get('Quant. Fotos', 0),
                'quantidade_kits': dados.get('Quant. Kits', 0),
                'quantidade_capas': dados.get('Quant. Capas', 0),
                'valor_por_foto': dados.get('Valor por Foto', 0.0),
                'valor_por_kit': dados.get('Valor por Kit', 0.0),
                'valor_por_capa': dados.get('Valor por Capa', 0.0),
                'pasta_producao': dados.get('pasta_producao', ''),
            }
            logger.info(f"[PERFORMANCE] Preparação de dados: {(time.time() - start_prep)*1000:.2f}ms")

            # PERFORMANCE LOG - Atualizar banco
            start_db = time.time()
            self.db.atualizar_producao(producao_id, db_data)
            logger.info(f"[PERFORMANCE] Atualização no banco: {(time.time() - start_db)*1000:.2f}ms")

            # OTIMIZAÇÃO 5: Atualizar apenas a linha editada, preservando filtros
            # Em vez de recarregar TODA a tabela (5000ms), atualizar apenas 1 linha (~1ms)
            start_update = time.time()

            # Buscar produção atualizada do banco
            producao_atualizada = self.db.obter_producao(producao_id)

            if producao_atualizada:
                # 1. Atualizar na lista completa
                for i, prod in enumerate(self.producoes):
                    if prod.get('ID') == producao_id:
                        self.producoes[i] = producao_atualizada
                        break

                # 2. Verificar se a produção passa pelos filtros atuais
                cliente_filter = self.filter_widgets.get('cliente').currentText()
                tipo_filter = self.filter_widgets.get('tipo').currentText()
                status_pag_filter = self.filter_widgets.get('status_pagamento').currentText()

                passa_filtros = True
                if cliente_filter != "Todos" and producao_atualizada.get('Cliente', '') != cliente_filter:
                    passa_filtros = False
                if tipo_filter != "Todos" and producao_atualizada.get('Tipo de Produção', '') != tipo_filter:
                    passa_filtros = False
                if status_pag_filter != "Todos" and producao_atualizada.get('Status Pagamento', '') != status_pag_filter:
                    passa_filtros = False

                # 3. Encontrar produção na lista filtrada
                row_index = None
                for i, prod in enumerate(self.filtered_producoes):
                    if prod.get('ID') == producao_id:
                        row_index = i
                        break

                # 4. Atualizar visualização baseado no estado
                if row_index is not None:
                    # Produção já estava visível
                    if passa_filtros:
                        # Ainda passa pelos filtros: apenas atualizar a linha
                        self.filtered_producoes[row_index] = producao_atualizada
                        self._update_single_row(row_index, producao_atualizada)
                    else:
                        # Não passa mais: remover da visualização
                        self.filtered_producoes.pop(row_index)
                        self.table.removeRow(row_index)
                else:
                    # Produção não estava visível
                    if passa_filtros:
                        # Agora passa pelos filtros: adicionar à visualização
                        self.filtered_producoes.append(producao_atualizada)
                        row_index = len(self.filtered_producoes) - 1
                        self.table.setRowCount(len(self.filtered_producoes))
                        self._update_single_row(row_index, producao_atualizada)
                    # Se não passa, não fazer nada (continua oculta)

                # 5. Atualizar lista de clientes se necessário
                cliente_novo = producao_atualizada.get('Cliente', '')
                if cliente_novo and cliente_novo not in self.clientes_list:
                    self.clientes_list.append(cliente_novo)
                    self._update_filter_options()

                # 6. Atualizar status bar
                self._update_statusbar()

            logger.info(f"[PERFORMANCE] Atualização de linha única (OTIMIZAÇÃO 5): {(time.time() - start_update)*1000:.2f}ms")

            # Restaurar cursor normal antes de mostrar mensagem
            QApplication.restoreOverrideCursor()

            logger.info(f"[PERFORMANCE] Tempo total de salvamento: {(time.time() - start_total)*1000:.2f}ms")
            logger.info(f"Produção {producao_id} atualizada com sucesso")

            QMessageBox.information(self, "Sucesso", "Produção atualizada com sucesso!")

        except Exception as e:
            QApplication.restoreOverrideCursor()
            logger.error(f"Erro ao editar produção: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao editar produção: {e}")

    def _delete_selected_productions(self):
        """Remove as produções selecionadas"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Nenhuma Seleção", "Selecione uma ou mais produções para remover.")
            return

        reply = QMessageBox.question(
            self,
            "Confirmar Remoção",
            f"Tem certeza que deseja remover {len(selected_rows)} produção(ões)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            # Mostrar cursor de espera
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))

            ids_to_remove = []
            for selected_row in selected_rows:
                row = selected_row.row()
                # Recuperar o ID da produção armazenado na célula (independente da ordenação)
                item = self.table.item(row, 0)  # Pegar qualquer item da linha (coluna 0)
                producao_id = item.data(Qt.ItemDataRole.UserRole)
                ids_to_remove.append(producao_id)

            removed = self.db.remover_producoes(ids_to_remove)
            self._load_table_data()

            # Restaurar cursor normal antes de mostrar mensagem
            QApplication.restoreOverrideCursor()
            QMessageBox.information(self, "Sucesso", f"{removed} produção(ões) removida(s) com sucesso!")

        except Exception as e:
            QApplication.restoreOverrideCursor()
            logger.error(f"Erro ao remover produções: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao remover produções: {e}")

    def _generate_pdf(self):
        """Gera relatório PDF de produções em aberto"""
        try:
            # Abrir diálogo de seleção
            dialog = RelatorioAbertoDialog(
                self,
                db_manager=self.db,
                on_generate=self._gerar_pdf_aberto
            )
            dialog.exec()

        except Exception as e:
            logger.error(f"Erro ao abrir diálogo de relatório: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao abrir diálogo: {e}")

    def _gerar_pdf_aberto(self, cliente: str, producoes: List[Dict[str, Any]]):
        """
        Gera o PDF de produções em aberto

        Args:
            cliente: Nome do cliente
            producoes: Lista de produções selecionadas
        """
        try:
            from PyQt6.QtWidgets import QFileDialog
            from pathlib import Path

            # Criar nome do arquivo sugerido
            data_atual = datetime.now().strftime('%Y-%m-%d')
            nome_arquivo = f"Relatorio Aberto - {data_atual} - {cliente}.pdf"

            # Diálogo para salvar arquivo
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Salvar Relatório PDF",
                str(DATA_DIR / nome_arquivo),
                "PDF Files (*.pdf)"
            )

            if not file_path:
                return  # Usuário cancelou

            # Mostrar cursor de espera
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))

            # Gerar PDF
            pdf_generator = PDFGenerator()
            sucesso = pdf_generator.gerar_relatorio_producoes_aberto(
                file_path=Path(file_path),
                cliente=cliente,
                producoes=producoes
            )

            # Restaurar cursor
            QApplication.restoreOverrideCursor()

            if sucesso:
                reply = QMessageBox.question(
                    self,
                    "Sucesso",
                    f"Relatório PDF gerado com sucesso!\n\nDeseja abrir o arquivo?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )

                if reply == QMessageBox.StandardButton.Yes:
                    # Abrir PDF com aplicativo padrão
                    import os
                    import platform
                    import subprocess

                    if platform.system() == 'Windows':
                        os.startfile(file_path)
                    elif platform.system() == 'Darwin':  # macOS
                        subprocess.run(['open', file_path])
                    else:  # Linux
                        subprocess.run(['xdg-open', file_path])
            else:
                QMessageBox.warning(self, "Erro", "Erro ao gerar relatório PDF. Verifique os logs.")

        except Exception as e:
            QApplication.restoreOverrideCursor()
            logger.error(f"Erro ao gerar PDF: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao gerar PDF: {e}")

    def _show_financial_summary(self):
        """Exibe resumo financeiro com gráfico"""
        try:
            dialog = FinancialSummaryDialog(self, self.db)
            dialog.exec()
        except Exception as e:
            logger.error(f"Erro ao abrir resumo financeiro: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao abrir resumo financeiro: {e}")

    def _open_settings(self):
        """Abre diálogo de configurações"""
        dialog = SettingsDialog(
            self,
            on_manage_types=self._manage_types,
            on_configure_pix=self._configure_pix,
            on_configure_columns=lambda: QMessageBox.information(self, "Em Desenvolvimento", "Em breve!")
        )
        dialog.exec()

    def _manage_types(self):
        """Abre diálogo de gerenciar tipos"""
        dialog = ManageTypesDialog(
            self,
            tipos_producao=self.tipos_producao,
            on_add=self.db.adicionar_tipo_producao,
            on_remove=self.db.remover_tipo_producao
        )
        dialog.exec()
        self.tipos_producao = dialog.get_tipos()

    def _configure_pix(self):
        """Abre diálogo de configurar PIX"""
        def save_pix_config(config):
            logger.info(f"Configuração PIX: {config}")

        dialog = PixConfigDialog(
            self,
            current_config={},
            on_save=save_pix_config
        )
        dialog.exec()
