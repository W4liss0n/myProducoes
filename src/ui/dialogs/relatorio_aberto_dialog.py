# -*- coding: utf-8 -*-
"""
Diálogo para gerar relatório de produções em aberto
"""
from typing import Dict, List, Callable, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QCheckBox,
    QPushButton, QLabel, QScrollArea, QWidget, QGroupBox,
    QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt

from ..icons import Icons


class RelatorioAbertoDialog(QDialog):
    """Diálogo para selecionar cliente e produções para relatório em aberto"""

    def __init__(self, parent, db_manager, on_generate: Callable[[str, List[Dict[str, Any]]], None]):
        super().__init__(parent)
        self.db = db_manager
        self.on_generate_callback = on_generate
        self.checkboxes: Dict[int, QCheckBox] = {}  # ID da produção -> checkbox
        self.producoes_em_aberto: List[Dict[str, Any]] = []

        # Ativar logging em nível DEBUG para este diálogo
        import logging
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        self._setup_ui()
        self._load_clientes()

    def _setup_ui(self):
        """Configura a interface do diálogo"""
        self.setWindowTitle("Gerar Relatório de Produções em Aberto")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Título
        title_label = QLabel("Relatório de Produções em Aberto")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)

        # Seleção de cliente
        cliente_group = QGroupBox("Selecione o Cliente")
        cliente_layout = QHBoxLayout()

        label_cliente = QLabel("Cliente:")
        cliente_layout.addWidget(label_cliente)

        self.combo_cliente = QComboBox()
        self.combo_cliente.setMinimumWidth(300)
        self.combo_cliente.currentTextChanged.connect(self._on_cliente_changed)
        cliente_layout.addWidget(self.combo_cliente)

        cliente_layout.addStretch()
        cliente_group.setLayout(cliente_layout)
        layout.addWidget(cliente_group)

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

        # Área de scroll para as produções
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

        # Label de informação
        self.info_label = QLabel("Selecione um cliente para ver as produções em aberto")
        self.info_label.setStyleSheet("color: #666; font-style: italic; padding: 10px;")
        layout.addWidget(self.info_label)

        # Botões de ação
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

    def _load_clientes(self):
        """Carrega lista de clientes únicos"""
        try:
            clientes = self.db.obter_clientes_unicos()
            self.combo_cliente.addItem("-- Selecione um cliente --")
            self.combo_cliente.addItems(sorted(clientes))
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar clientes: {e}")

    def _on_cliente_changed(self, cliente: str):
        """Chamado quando o cliente é alterado"""
        if not cliente or cliente == "-- Selecione um cliente --":
            self._clear_producoes()
            self.info_label.setText("Selecione um cliente para ver as produções em aberto")
            return

        self._load_producoes_em_aberto(cliente)

    def _load_producoes_em_aberto(self, cliente: str):
        """Carrega produções em aberto do cliente selecionado"""
        try:
            import logging
            logger = logging.getLogger(__name__)

            # Limpar checkboxes antigos primeiro
            self._clear_producoes()

            # Limpar lista de produções
            self.producoes_em_aberto = []

            # Buscar produções em aberto do cliente
            filtros = {
                'cliente': cliente,
                'status_pagamento': 'Em aberto'
            }

            logger.info(f"Buscando produções com filtros: {filtros}")
            self.producoes_em_aberto = self.db.listar_producoes(filtros)
            logger.info(f"Encontradas {len(self.producoes_em_aberto)} produções em aberto para {cliente}")

            if not self.producoes_em_aberto:
                self.info_label.setText(f"Nenhuma produção em aberto encontrada para {cliente}")
                return

            # Criar checkboxes para cada produção
            logger.info(f"Iniciando criação de {len(self.producoes_em_aberto)} checkboxes")

            for idx, producao in enumerate(self.producoes_em_aberto):
                producao_id = producao.get('ID')
                nome = producao.get('Nome', 'Sem nome')
                valor_total = producao.get('Valor Total', 0)
                data_conclusao = producao.get('Data de Conclusão', 'N/A')

                # Formatar data se for string de data válida
                if data_conclusao and data_conclusao not in ('N/A', '', None, 'None', 'nan'):
                    try:
                        from datetime import datetime
                        if isinstance(data_conclusao, str):
                            date_part = data_conclusao.split()[0] if ' ' in data_conclusao else data_conclusao
                            date_obj = datetime.strptime(date_part, '%Y-%m-%d')
                            data_conclusao_formatada = date_obj.strftime('%d/%m/%Y')
                        else:
                            data_conclusao_formatada = data_conclusao.strftime('%d/%m/%Y') if hasattr(data_conclusao, 'strftime') else str(data_conclusao)
                    except:
                        data_conclusao_formatada = str(data_conclusao)
                else:
                    data_conclusao_formatada = 'N/A'

                # Formatar o texto do checkbox
                texto = f"{nome} - R$ {valor_total:,.2f} - Conclusão: {data_conclusao_formatada}".replace(',', 'X').replace('.', ',').replace('X', '.')

                checkbox = QCheckBox(texto, self.scroll_widget)
                checkbox.setChecked(True)  # Marcar por padrão
                checkbox.setStyleSheet("padding: 5px;")
                checkbox.setVisible(True)  # Garantir que está visível
                self.checkboxes[producao_id] = checkbox

                self.scroll_layout.addWidget(checkbox)
                logger.info(f"[{idx+1}/{len(self.producoes_em_aberto)}] Checkbox adicionado - ID: {producao_id}, Texto: {texto[:50]}...")

            # Adicionar stretch no final
            self.scroll_layout.addStretch()
            logger.info(f"Total de checkboxes no dict: {len(self.checkboxes)}")
            logger.info(f"Total de itens no layout: {self.scroll_layout.count()}")

            # Forçar atualização do widget
            self.scroll_widget.adjustSize()
            self.scroll_widget.updateGeometry()
            self.scroll_area.setWidget(self.scroll_widget)  # Re-set o widget

            # Atualizar label de informação
            self.info_label.setText(f"{len(self.producoes_em_aberto)} produção(ões) em aberto encontrada(s)")

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao carregar produções em aberto: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao carregar produções: {e}")

    def _clear_producoes(self):
        """Limpa apenas os checkboxes da interface (não limpa self.producoes_em_aberto)"""
        import logging
        logger = logging.getLogger(__name__)

        logger.debug(f"Limpando {len(self.checkboxes)} checkboxes e {self.scroll_layout.count()} itens do layout")

        # Remover todos os checkboxes
        for checkbox in self.checkboxes.values():
            self.scroll_layout.removeWidget(checkbox)
            checkbox.setParent(None)
            checkbox.deleteLater()

        # Remover todos os itens restantes do layout (incluindo stretches e spacers)
        while self.scroll_layout.count() > 0:
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()
            elif item.spacerItem():
                # É um spacer/stretch, apenas remover
                pass

        self.checkboxes.clear()
        # NÃO limpar self.producoes_em_aberto aqui, pois isso é chamado antes de popular os checkboxes

        logger.debug(f"Layout limpo. Itens restantes: {self.scroll_layout.count()}")

    def _select_all(self):
        """Seleciona todas as produções"""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(True)

    def _deselect_all(self):
        """Desmarca todas as produções"""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)

    def _generate_pdf(self):
        """Gera o relatório PDF"""
        try:
            # Validar que um cliente foi selecionado
            cliente = self.combo_cliente.currentText()
            if not cliente or cliente == "-- Selecione um cliente --":
                QMessageBox.warning(
                    self,
                    "Cliente não selecionado",
                    "Por favor, selecione um cliente antes de gerar o relatório."
                )
                return

            # Pegar produções selecionadas
            producoes_selecionadas = []
            for producao_id, checkbox in self.checkboxes.items():
                if checkbox.isChecked():
                    # Encontrar a produção completa
                    producao = next((p for p in self.producoes_em_aberto if p.get('ID') == producao_id), None)
                    if producao:
                        producoes_selecionadas.append(producao)

            # Validar que pelo menos uma produção foi selecionada
            if not producoes_selecionadas:
                QMessageBox.warning(
                    self,
                    "Nenhuma Produção Selecionada",
                    "Você deve selecionar pelo menos uma produção para gerar o relatório."
                )
                return

            # Chamar callback com os dados
            if self.on_generate_callback:
                self.on_generate_callback(cliente, producoes_selecionadas)

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao gerar PDF: {e}")
