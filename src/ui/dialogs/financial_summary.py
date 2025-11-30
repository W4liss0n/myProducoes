# -*- coding: utf-8 -*-
"""
Diálogo de Resumo Financeiro - Design 1: Dashboard Cards
Layout com cards grandes, gráfico central e painel lateral de análise
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QGroupBox, QPushButton, QWidget,
    QSizePolicy, QMessageBox, QFrame, QScrollArea,
    QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Matplotlib para gráficos
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime as dt

from ..icons import Icons

logger = logging.getLogger(__name__)


class MplCanvas(FigureCanvasQTAgg):
    """Canvas do Matplotlib para integração com PyQt6"""

    def __init__(self, parent=None, width=10, height=6, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi, facecolor='white')
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)
        self.setParent(parent)

        FigureCanvasQTAgg.setSizePolicy(
            self,
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        FigureCanvasQTAgg.updateGeometry(self)

        # Anotação para tooltip
        self.annot = None
        self.hover_enabled = False


class FinancialSummaryDialog(QDialog):
    """Diálogo de resumo financeiro - Design 1: Dashboard Cards"""

    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db = db_manager

        # Widgets
        self.canvas = None
        self.filter_widgets = {}
        self.stats_labels = {}
        self.detail_labels = []
        self.chart_mode_combo = None

        # Dados
        self.dados_financeiros = []
        self.clientes_list = []
        self.tipos_producao = []
        self.anos_disponiveis = []

        self._setup_ui()
        self._load_initial_data()
        self._update_chart()

    def _setup_ui(self):
        """Configura a interface do diálogo - Design 1"""
        self.setWindowTitle("Dashboard Cards")
        self.setMinimumSize(1400, 900)

        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Cabeçalho removido conforme solicitação

        # Filtros compactos
        filters_frame = self._create_compact_filters()
        main_layout.addWidget(filters_frame)

        # Cards de métricas (4 cards horizontais)
        cards_layout = self._create_metric_cards()
        main_layout.addLayout(cards_layout)

        # Layout horizontal: Gráfico + Painel lateral
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Gráfico principal (esquerda - ocupa mais espaço)
        chart_widget = self._create_chart_widget()
        content_layout.addWidget(chart_widget, 3)  # stretch factor 3

        # Painel lateral de detalhes (direita)
        details_panel = self._create_details_panel()
        content_layout.addWidget(details_panel, 1)  # stretch factor 1

        main_layout.addLayout(content_layout, 1)  # stretch factor 1

        # Botões de ação
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        btn_refresh = QPushButton("Atualizar Dados")
        btn_refresh.setObjectName("primaryButton")
        btn_refresh.setIcon(Icons.refresh())
        btn_refresh.setMinimumWidth(150)
        btn_refresh.clicked.connect(self._update_chart)
        buttons_layout.addWidget(btn_refresh)

        btn_close = QPushButton("Fechar")
        btn_close.setObjectName("secondaryButton")
        btn_close.setMinimumWidth(120)
        btn_close.clicked.connect(self.close)
        buttons_layout.addWidget(btn_close)

        main_layout.addLayout(buttons_layout)

    def _create_header(self) -> QWidget:
        """Cria o cabeçalho com título e borda"""
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 3px solid #2196F3;
                border-radius: 8px;
                padding: 15px;
            }
        """)

        layout = QVBoxLayout(header_frame)
        layout.setContentsMargins(20, 10, 20, 10)

        title = QLabel("Dashboard Cards")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2196F3; border: none;")
        layout.addWidget(title)

        return header_frame

    def _create_compact_filters(self) -> QFrame:
        """Cria os filtros em layout compacto"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #FAFAFA;
                border: 2px solid #666666;
                border-radius: 8px;
                padding: 10px;
            }
        """)

        layout = QHBoxLayout(frame)
        layout.setSpacing(15)

        # Filtros inline
        filters = [
            ("Cliente", "cliente", 200),
            ("Ano", "ano", 120),
            ("Mês", "mes", 150),
            ("Tipo", "tipo", 180),
            ("Status", "status_pagamento", 140)
        ]

        for label_text, key, width in filters:
            label = QLabel(f"{label_text}:")
            label.setStyleSheet("border: none; color: #333; font-weight: bold;")
            layout.addWidget(label)

            combo = QComboBox()
            combo.setMinimumWidth(width)
            combo.addItem("Todos")
            combo.currentTextChanged.connect(self._on_filter_changed)
            self.filter_widgets[key] = combo
            layout.addWidget(combo)

        layout.addStretch()

        # Botão limpar filtros
        btn_clear = QPushButton("Limpar Filtros")
        btn_clear.setObjectName("secondaryButton")
        btn_clear.setIcon(Icons.delete(Icons.COLOR_SECONDARY))
        btn_clear.setMinimumWidth(140)
        btn_clear.clicked.connect(self._clear_filters)
        layout.addWidget(btn_clear)

        return frame

    def _create_metric_cards(self) -> QHBoxLayout:
        """Cria os 4 cards de métricas principais"""
        layout = QHBoxLayout()
        layout.setSpacing(20)

        # Definir os cards: título, key, cor, ícone
        cards_config = [
            ("Receita Total", "receita", "#4CAF50", "fa5s.dollar-sign"),
            ("Total Produções", "producoes", "#2196F3", "fa5s.box"),
            ("Ticket Médio", "ticket", "#FF9800", "fa5s.chart-line"),
            ("Crescimento", "crescimento", "#9C27B0", "fa5s.arrow-up")
        ]

        for title, key, color, icon_name in cards_config:
            card = self._create_metric_card(title, "R$ 0,00" if key != "producoes" else "0", color, icon_name, key)
            layout.addWidget(card)

        return layout

    def _create_metric_card(self, title: str, initial_value: str, color: str, icon_name: str, key: str) -> QFrame:
        """Cria um card de métrica individual"""
        import qtawesome as qta

        card = QFrame()
        card.setMinimumHeight(120)
        card.setMaximumHeight(140)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 3px solid {color};
                border-radius: 10px;
                padding: 10px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(10)

        # Título
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: #666; font-size: 10pt; border: none; font-weight: normal;")
        layout.addWidget(title_label)

        # Container para valor e ícone
        value_container = QHBoxLayout()

        # Valor
        value_label = QLabel(initial_value)
        value_label.setStyleSheet(f"color: {color}; font-size: 16pt; font-weight: bold; border: none;")
        value_container.addWidget(value_label)
        value_container.addStretch()

        # Ícone circular
        icon_label = QLabel()
        icon_pixmap = qta.icon(icon_name, color=color).pixmap(40, 40)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setStyleSheet("border: none;")
        value_container.addWidget(icon_label)

        layout.addLayout(value_container)

        # Armazenar referência ao label de valor
        self.stats_labels[key] = value_label

        layout.addStretch()

        return card

    def _create_chart_widget(self) -> QGroupBox:
        """Cria o widget do gráfico principal"""
        group = QGroupBox("Evolução Temporal - Gráfico de Linha")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 12pt;
                color: #333;
                border: 2px solid #333;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 20, 15, 15)

        # Controle de modo de visualização
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Tipo de Visualização:")
        mode_label.setStyleSheet("border: none; font-size: 10pt; font-weight: normal;")
        mode_layout.addWidget(mode_label)

        self.chart_mode_combo = QComboBox()
        self.chart_mode_combo.setMinimumWidth(200)
        self.chart_mode_combo.addItems(["Evolução Temporal", "Comparação por Ano"])
        self.chart_mode_combo.currentTextChanged.connect(self._on_chart_mode_changed)
        mode_layout.addWidget(self.chart_mode_combo)
        mode_layout.addStretch()

        layout.addLayout(mode_layout)

        # Canvas do matplotlib
        self.canvas = MplCanvas(self, width=10, height=6, dpi=100)
        layout.addWidget(self.canvas)

        group.setLayout(layout)
        return group

    def _create_details_panel(self) -> QFrame:
        """Cria o painel lateral de detalhes"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #333;
                border-radius: 8px;
            }
        """)
        panel.setMinimumWidth(350)
        panel.setMaximumWidth(440)

        main_layout = QVBoxLayout(panel)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Título
        title_container = QFrame()
        title_container.setStyleSheet("background-color: white; border: none;")
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(15, 10, 15, 5)

        title = QLabel("Análise Detalhada")
        title.setStyleSheet("font-size: 11pt; font-weight: bold; color: #333; border: none;")
        title_layout.addWidget(title)

        main_layout.addWidget(title_container)

        # Área de scroll para os detalhes (ocupa todo o espaço restante)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        # Container para os itens de detalhe
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: white;")
        self.details_layout = QVBoxLayout(scroll_content)
        self.details_layout.setSpacing(8)
        self.details_layout.setContentsMargins(15, 0, 15, 15)
        self.details_layout.addStretch()

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)  # stretch factor 1 para ocupar todo espaço

        return panel

    def _update_details_panel(self):
        """Atualiza o painel lateral com os detalhes dos períodos"""
        # Limpar itens anteriores
        for i in reversed(range(self.details_layout.count())):
            widget = self.details_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Adicionar novos itens (limitar a 10 mais recentes)
        dados_recentes = sorted(
            self.dados_financeiros,
            key=lambda x: x['data'],
            reverse=True
        )[:10]

        meses_nomes = [
            "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
            "Jul", "Ago", "Set", "Out", "Nov", "Dez"
        ]

        for dado in dados_recentes:
            item = QFrame()
            item.setStyleSheet("""
                QFrame {
                    background-color: #F5F5F5;
                    border: 1px solid #E0E0E0;
                    border-radius: 6px;
                }
            """)
            item.setMinimumHeight(70)

            layout = QVBoxLayout(item)
            layout.setSpacing(3)
            layout.setContentsMargins(12, 8, 12, 8)

            # Período
            mes_nome = meses_nomes[dado['mes'] - 1] if 1 <= dado['mes'] <= 12 else str(dado['mes'])
            periodo_label = QLabel(f"{mes_nome}/{dado['ano']}")
            periodo_label.setStyleSheet("font-weight: bold; color: #555; border: none; font-size: 10pt;")
            layout.addWidget(periodo_label)

            # Valor
            valor_fmt = f"R$ {dado['valor_total']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            valor_label = QLabel(valor_fmt)
            valor_label.setStyleSheet("color: #2196F3; font-size: 13pt; font-weight: bold; border: none;")
            layout.addWidget(valor_label)

            # Quantidade
            qtd_label = QLabel(f"{dado['quantidade']} produções")
            qtd_label.setStyleSheet("color: #888; font-size: 9pt; border: none;")
            layout.addWidget(qtd_label)

            self.details_layout.insertWidget(0, item)

        self.details_layout.addStretch()

    def _load_initial_data(self):
        """Carrega dados iniciais para os filtros"""
        try:
            # Clientes
            self.clientes_list = self.db.obter_clientes_unicos()
            combo_cliente = self.filter_widgets['cliente']
            combo_cliente.blockSignals(True)
            for cliente in sorted(self.clientes_list):
                combo_cliente.addItem(cliente)
            combo_cliente.blockSignals(False)

            # Tipos de Produção
            self.tipos_producao = self.db.listar_tipos_producao()
            combo_tipo = self.filter_widgets['tipo']
            combo_tipo.blockSignals(True)
            for tipo in sorted(self.tipos_producao):
                combo_tipo.addItem(tipo)
            combo_tipo.blockSignals(False)

            # Anos disponíveis
            self.anos_disponiveis = self.db.obter_anos_disponiveis()
            combo_ano = self.filter_widgets['ano']
            combo_ano.blockSignals(True)
            for ano in self.anos_disponiveis:
                combo_ano.addItem(str(ano))
            combo_ano.blockSignals(False)

            # Meses
            combo_mes = self.filter_widgets['mes']
            combo_mes.blockSignals(True)
            meses = [
                "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
            ]
            for i, mes in enumerate(meses, 1):
                combo_mes.addItem(f"{i:02d} - {mes}")
            combo_mes.blockSignals(False)

            # Status pagamento
            combo_status = self.filter_widgets['status_pagamento']
            combo_status.blockSignals(True)
            combo_status.addItems(["Em aberto", "Pago"])
            combo_status.blockSignals(False)

            logger.info("Dados iniciais carregados para filtros")

        except Exception as e:
            logger.error(f"Erro ao carregar dados iniciais: {e}", exc_info=True)
            QMessageBox.warning(self, "Erro", f"Erro ao carregar dados: {e}")

    def _on_filter_changed(self, text: str):
        """Chamado quando um filtro é alterado"""
        self._update_chart()

    def _on_chart_mode_changed(self, text: str):
        """Chamado quando o modo de visualização do gráfico é alterado"""
        self._plot_chart()

    def _clear_filters(self):
        """Limpa todos os filtros"""
        try:
            for key, widget in self.filter_widgets.items():
                widget.blockSignals(True)
                widget.setCurrentIndex(0)
                widget.blockSignals(False)

            self._update_chart()
            logger.info("Filtros limpos")

        except Exception as e:
            logger.error(f"Erro ao limpar filtros: {e}", exc_info=True)

    def _get_current_filters(self) -> Dict[str, Any]:
        """Retorna os filtros atuais selecionados"""
        filtros = {}

        # Cliente
        cliente = self.filter_widgets['cliente'].currentText()
        if cliente and cliente != "Todos":
            filtros['cliente'] = cliente

        # Ano
        ano_text = self.filter_widgets['ano'].currentText()
        if ano_text and ano_text != "Todos":
            filtros['ano'] = int(ano_text)

        # Mês
        mes_text = self.filter_widgets['mes'].currentText()
        if mes_text and mes_text != "Todos":
            mes_num = int(mes_text.split('-')[0].strip())
            filtros['mes'] = mes_num

        # Tipo de Produção
        tipo = self.filter_widgets['tipo'].currentText()
        if tipo and tipo != "Todos":
            filtros['tipo_producao'] = tipo

        # Status Pagamento
        status = self.filter_widgets['status_pagamento'].currentText()
        if status and status != "Todos":
            filtros['status_pagamento'] = status

        return filtros

    def _update_chart(self):
        """Atualiza o gráfico e estatísticas"""
        try:
            # Obter filtros
            filtros = self._get_current_filters()

            # Buscar dados do banco
            self.dados_financeiros = self.db.obter_dados_financeiros_por_periodo(filtros)

            # Atualizar estatísticas
            self._update_statistics()

            # Atualizar painel de detalhes
            self._update_details_panel()

            # Atualizar gráfico
            self._plot_chart()

            logger.info(f"Dashboard atualizado com {len(self.dados_financeiros)} períodos")

        except Exception as e:
            logger.error(f"Erro ao atualizar dashboard: {e}", exc_info=True)
            QMessageBox.warning(self, "Erro", f"Erro ao atualizar dashboard: {e}")

    def _update_statistics(self):
        """Atualiza as estatísticas dos cards"""
        try:
            # Calcular totais
            valor_total = sum(d['valor_total'] for d in self.dados_financeiros)
            quantidade_total = sum(d['quantidade'] for d in self.dados_financeiros)
            ticket_medio = valor_total / quantidade_total if quantidade_total > 0 else 0

            # Calcular crescimento (comparar último período com anterior)
            crescimento_pct = 0.0
            if len(self.dados_financeiros) >= 2:
                dados_ordenados = sorted(self.dados_financeiros, key=lambda x: x['data'])
                ultimo = dados_ordenados[-1]['valor_total']
                penultimo = dados_ordenados[-2]['valor_total']
                if penultimo > 0:
                    crescimento_pct = ((ultimo - penultimo) / penultimo) * 100

            # Formatar valores
            valor_total_fmt = f"R$ {valor_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            quantidade_fmt = str(quantidade_total)
            ticket_medio_fmt = f"R$ {ticket_medio:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            crescimento_fmt = f"{crescimento_pct:+.1f}%"

            # Atualizar cards
            self.stats_labels['receita'].setText(valor_total_fmt)
            self.stats_labels['producoes'].setText(quantidade_fmt)
            self.stats_labels['ticket'].setText(ticket_medio_fmt)
            self.stats_labels['crescimento'].setText(crescimento_fmt)

        except Exception as e:
            logger.error(f"Erro ao atualizar estatísticas: {e}", exc_info=True)

    def _plot_chart(self):
        """Plota o gráfico de linhas de acordo com o modo selecionado"""
        try:
            # Limpar gráfico anterior
            self.canvas.axes.clear()

            if not self.dados_financeiros:
                # Mensagem se não houver dados
                self.canvas.axes.text(
                    0.5, 0.5,
                    'Nenhum dado disponível para os filtros selecionados',
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=self.canvas.axes.transAxes,
                    fontsize=14,
                    color='#666666'
                )
                self.canvas.axes.set_xlim([0, 1])
                self.canvas.axes.set_ylim([0, 1])
                self.canvas.axes.axis('off')
                self.canvas.draw()
                return

            # Verificar modo de visualização
            modo = self.chart_mode_combo.currentText() if self.chart_mode_combo else "Evolução Temporal"

            if modo == "Comparação por Ano":
                self._plot_year_comparison()
            else:
                self._plot_temporal_evolution()

        except Exception as e:
            logger.error(f"Erro ao plotar gráfico: {e}", exc_info=True)
            self.canvas.axes.clear()
            self.canvas.axes.text(
                0.5, 0.5,
                f'Erro ao gerar gráfico:\n{str(e)}',
                horizontalalignment='center',
                verticalalignment='center',
                transform=self.canvas.axes.transAxes,
                fontsize=12,
                color='red'
            )
            self.canvas.axes.axis('off')
            self.canvas.draw()

    def _plot_temporal_evolution(self):
        """Plota gráfico de evolução temporal (modo contínuo)"""
        # Desabilitar hover neste modo
        self.canvas.hover_enabled = False
        if self.canvas.annot:
            self.canvas.annot.set_visible(False)

        # Preparar dados para o gráfico
        datas = []
        valores = []

        for dado in self.dados_financeiros:
            data_str = dado['data']
            data_obj = dt.strptime(data_str, '%Y-%m-%d')
            datas.append(data_obj)
            valores.append(dado['valor_total'])

            # Plotar linha
            self.canvas.axes.plot(
                datas,
                valores,
                marker='o',
                linestyle='-',
                linewidth=3,
                markersize=8,
                color='#2196F3',
                markerfacecolor='#1976D2',
                markeredgecolor='white',
                markeredgewidth=2,
                label='Valor Total'
            )

            # Adicionar valores nos pontos com fundo branco
            for i, (data, valor) in enumerate(zip(datas, valores)):
                valor_fmt = f"R$ {valor:,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                self.canvas.axes.annotate(
                    valor_fmt,
                    xy=(data, valor),
                    xytext=(0, 15),  # Aumentado de 10 para 15 para afastar da linha
                    textcoords='offset points',
                    ha='center',
                    fontsize=9,
                    color='#1976D2',
                    fontweight='bold',
                    bbox=dict(
                        boxstyle='round,pad=0.4',
                        facecolor='white',
                        edgecolor='none',
                        alpha=0.85
                    )
                )

            # Configurar eixos
            self.canvas.axes.set_xlabel('Período', fontsize=12, fontweight='bold', color='#424242')
            self.canvas.axes.set_ylabel('Valor Total (R$)', fontsize=12, fontweight='bold', color='#424242')

            # Formatar eixo X (datas) - ajustado para evitar sobreposição
            if len(datas) > 15:
                # Muitos pontos: mostrar a cada 3 meses
                self.canvas.axes.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            elif len(datas) > 10:
                # Quantidade média: mostrar a cada 2 meses
                self.canvas.axes.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
            else:
                # Poucos pontos: mostrar todos os meses
                self.canvas.axes.xaxis.set_major_locator(mdates.MonthLocator())

            self.canvas.axes.xaxis.set_major_formatter(mdates.DateFormatter('%m/%Y'))

            # Rotação maior para evitar sobreposição
            plt.setp(
                self.canvas.axes.xaxis.get_majorticklabels(),
                rotation=60,
                ha='right',
                fontsize=9
            )

            # Formatar eixo Y (valores monetários)
            def currency_formatter(x, pos):
                return f"R$ {x:,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')

            from matplotlib.ticker import FuncFormatter
            self.canvas.axes.yaxis.set_major_formatter(FuncFormatter(currency_formatter))

            # Grid e estilo
            self.canvas.axes.grid(True, linestyle='--', alpha=0.3, color='#CCCCCC')
            self.canvas.axes.set_axisbelow(True)
            self.canvas.axes.set_facecolor('#FAFAFA')

        # Ajustar layout
        self.canvas.figure.tight_layout()

        # Redesenhar
        self.canvas.draw()

    def _plot_year_comparison(self):
        """Plota gráfico de comparação por ano (uma linha para cada ano)"""
        # Organizar dados por ano
        dados_por_ano = {}
        for dado in self.dados_financeiros:
            ano = dado['ano']
            mes = dado['mes']

            if ano not in dados_por_ano:
                dados_por_ano[ano] = {}

            dados_por_ano[ano][mes] = dado['valor_total']

        # Cores para diferentes anos
        cores = [
            '#2196F3',  # Azul
            '#4CAF50',  # Verde
            '#FF9800',  # Laranja
            '#9C27B0',  # Roxo
            '#F44336',  # Vermelho
            '#00BCD4',  # Ciano
            '#FFC107',  # Amarelo
            '#795548',  # Marrom
        ]

        # Meses para o eixo X
        meses = list(range(1, 13))
        meses_nomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                       'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

        # Armazenar linhas para tooltip
        self.lines_data = []

        # Plotar uma linha para cada ano
        anos_ordenados = sorted(dados_por_ano.keys())
        for i, ano in enumerate(anos_ordenados):
            valores_ano = []
            meses_com_dados = []

            for mes in meses:
                if mes in dados_por_ano[ano]:
                    valores_ano.append(dados_por_ano[ano][mes])
                    meses_com_dados.append(mes)

            if valores_ano:
                cor = cores[i % len(cores)]
                line, = self.canvas.axes.plot(
                    meses_com_dados,
                    valores_ano,
                    marker='o',
                    linestyle='-',
                    linewidth=2.5,
                    markersize=7,
                    color=cor,
                    markerfacecolor=cor,
                    markeredgecolor='white',
                    markeredgewidth=2,
                    label=str(ano)
                )

                # Armazenar dados para tooltip
                self.lines_data.append({
                    'line': line,
                    'ano': ano,
                    'meses': meses_com_dados,
                    'valores': valores_ano,
                    'meses_nomes': [meses_nomes[m-1] for m in meses_com_dados]
                })

        # Configurar eixos
        self.canvas.axes.set_xlabel('Mês', fontsize=12, fontweight='bold', color='#424242')
        self.canvas.axes.set_ylabel('Valor Total (R$)', fontsize=12, fontweight='bold', color='#424242')

        # Configurar eixo X (meses)
        self.canvas.axes.set_xticks(meses)
        self.canvas.axes.set_xticklabels(meses_nomes)

        # Formatar eixo Y (valores monetários)
        def currency_formatter(x, pos):
            return f"R$ {x:,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')

        from matplotlib.ticker import FuncFormatter
        self.canvas.axes.yaxis.set_major_formatter(FuncFormatter(currency_formatter))

        # Grid e estilo
        self.canvas.axes.grid(True, linestyle='--', alpha=0.3, color='#CCCCCC')
        self.canvas.axes.set_axisbelow(True)
        self.canvas.axes.set_facecolor('#FAFAFA')

        # Legenda
        self.canvas.axes.legend(
            loc='upper left',
            fontsize=10,
            framealpha=0.9,
            title='Ano',
            title_fontsize=11
        )

        # Criar linha vertical para crosshair
        if not hasattr(self, 'vline'):
            self.vline = self.canvas.axes.axvline(x=0, color='#666666', linestyle='--', linewidth=1.5, visible=False, alpha=0.7)

        # Criar anotação para tooltip (caixa fixa)
        if self.canvas.annot is None:
            self.canvas.annot = self.canvas.axes.annotate(
                "",
                xy=(0, 0),
                xytext=(0, 0),
                textcoords="axes fraction",
                bbox=dict(
                    boxstyle="round,pad=0.8",
                    facecolor="white",
                    edgecolor="#2196F3",
                    linewidth=2.5,
                    alpha=0.98
                ),
                fontsize=10,
                fontfamily='monospace',
                color='#333333',
                visible=False,
                zorder=1000,
                verticalalignment='top',
                horizontalalignment='left'
            )

        # Conectar evento de movimento do mouse
        if not hasattr(self, '_hover_cid'):
            self._hover_cid = self.canvas.mpl_connect('motion_notify_event', self._on_hover_comparison)

        self.canvas.hover_enabled = True

        # Ajustar layout
        self.canvas.figure.tight_layout()

        # Redesenhar
        self.canvas.draw()

    def _on_hover_comparison(self, event):
        """Callback para mostrar tooltip estilo crosshair com comparação de todos os anos"""
        if not self.canvas.hover_enabled or event.inaxes != self.canvas.axes:
            # Mouse fora do gráfico
            if self.canvas.annot and self.canvas.annot.get_visible():
                self.canvas.annot.set_visible(False)
                if hasattr(self, 'vline'):
                    self.vline.set_visible(False)
                self.canvas.draw_idle()
            return

        if not hasattr(self, 'lines_data') or not self.lines_data:
            return

        # Obter posição X do mouse (mês)
        x_mouse = event.xdata
        if x_mouse is None:
            return

        # Encontrar o mês mais próximo
        mes_mais_proximo = round(x_mouse)

        # Garantir que está dentro do intervalo válido (1-12)
        if mes_mais_proximo < 1 or mes_mais_proximo > 12:
            if self.canvas.annot.get_visible():
                self.canvas.annot.set_visible(False)
                self.vline.set_visible(False)
                self.canvas.draw_idle()
            return

        # Atualizar linha vertical
        self.vline.set_xdata([mes_mais_proximo])
        self.vline.set_visible(True)

        # Nomes dos meses
        meses_nomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                       'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        mes_nome = meses_nomes[mes_mais_proximo - 1]

        # Coletar dados de todos os anos para este mês
        dados_mes = []
        for line_data in self.lines_data:
            if mes_mais_proximo in line_data['meses']:
                idx = line_data['meses'].index(mes_mais_proximo)
                valor = line_data['valores'][idx]
                ano = line_data['ano']
                dados_mes.append({'ano': ano, 'valor': valor})

        if not dados_mes:
            # Nenhum dado para este mês
            self.canvas.annot.set_visible(False)
            self.vline.set_visible(False)
            self.canvas.draw_idle()
            return

        # Ordenar por ano
        dados_mes.sort(key=lambda x: x['ano'])

        # Criar linhas da tooltip
        linhas = [f"{mes_nome}"]
        linhas.append("─" * 20)

        for i, item in enumerate(dados_mes):
            ano = item['ano']
            valor = item['valor']

            # Formatar valor
            valor_fmt = f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

            # Calcular variação
            variacao_text = ""
            if i > 0:
                valor_anterior = dados_mes[i-1]['valor']
                if valor_anterior > 0:
                    variacao_pct = ((valor - valor_anterior) / valor_anterior) * 100
                    sinal = "▲" if variacao_pct >= 0 else "▼"
                    variacao_text = f" {sinal}{abs(variacao_pct):.1f}%"

            linhas.append(f"{ano}: {valor_fmt}{variacao_text}")

        # Montar texto final
        text = '\n'.join(linhas)

        # Posicionar tooltip no canto superior esquerdo
        self.canvas.annot.set_text(text)
        self.canvas.annot.set_position((0.02, 0.98))
        self.canvas.annot.set_visible(True)

        self.canvas.draw_idle()
