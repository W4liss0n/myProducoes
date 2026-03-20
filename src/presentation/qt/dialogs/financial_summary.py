from __future__ import annotations

import logging

import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ....domain.models import ProductionFilters
from ..contracts import FinancialSummaryViewModelProtocol
from ..icons import Icons
from ..types import FinancialDashboardRow
from .financial_summary_metrics import compute_dashboard_metrics
from .financial_summary_plotter import FinancialSummaryPlotter
from .financial_summary_support import (
    SHORT_MONTH_NAMES,
    build_month_options,
    map_periods_to_dashboard_rows,
    recent_dashboard_rows,
)

matplotlib.use("QtAgg")
logger = logging.getLogger(__name__)


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=10, height=6, dpi=100) -> None:
        fig = Figure(figsize=(width, height), dpi=dpi, facecolor="white")
        self.axes = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)
        FigureCanvasQTAgg.setSizePolicy(self, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        FigureCanvasQTAgg.updateGeometry(self)
        self.annot = None
        self.hover_enabled = False


class FinancialSummaryDialog(QDialog):
    def __init__(self, *, view_model: FinancialSummaryViewModelProtocol, parent=None) -> None:
        super().__init__(parent)
        self.view_model = view_model
        self.canvas: MplCanvas | None = None
        self.filter_widgets: dict[str, QComboBox] = {}
        self.stats_labels: dict[str, QLabel] = {}
        self.chart_mode_combo: QComboBox | None = None
        self.plotter: FinancialSummaryPlotter | None = None
        self.dados_financeiros: list[FinancialDashboardRow] = []

        self._setup_ui()
        if self.canvas is None:
            raise RuntimeError("Canvas financeiro não foi inicializado.")
        self.plotter = FinancialSummaryPlotter(self.canvas, logger)
        self._load_filter_options()
        self._update_chart()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Dashboard Cards")
        self.setMinimumSize(1400, 900)
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.addWidget(self._create_compact_filters())
        main_layout.addLayout(self._create_metric_cards())

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        content_layout.addWidget(self._create_chart_widget(), 3)
        content_layout.addWidget(self._create_details_panel(), 1)
        main_layout.addLayout(content_layout, 1)

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

    def _create_compact_filters(self) -> QFrame:
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setSpacing(15)
        for label_text, key, width in (
            ("Cliente", "cliente", 200),
            ("Ano", "ano", 120),
            ("Mês", "mes", 150),
            ("Tipo", "tipo", 180),
            ("Status", "status_pagamento", 140),
        ):
            layout.addWidget(QLabel(f"{label_text}:"))
            combo = QComboBox()
            combo.setMinimumWidth(width)
            combo.addItem("Todos")
            combo.currentTextChanged.connect(self._update_chart)
            self.filter_widgets[key] = combo
            layout.addWidget(combo)
        layout.addStretch()
        btn_clear = QPushButton("Limpar Filtros")
        btn_clear.setObjectName("secondaryButton")
        btn_clear.setIcon(Icons.delete(Icons.COLOR_SECONDARY))
        btn_clear.setMinimumWidth(140)
        btn_clear.clicked.connect(self._clear_filters)
        layout.addWidget(btn_clear)
        return frame

    def _create_metric_cards(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(20)
        for title, key, color in (
            ("Receita Total", "receita", "#4CAF50"),
            ("Total Produções", "producoes", "#2196F3"),
            ("Ticket Médio", "ticket", "#FF9800"),
            ("Crescimento", "crescimento", "#9C27B0"),
        ):
            card = QFrame()
            card_layout = QVBoxLayout(card)
            card_layout.addWidget(QLabel(title))
            value_label = QLabel("R$ 0,00" if key != "producoes" else "0")
            value_label.setStyleSheet(f"color: {color}; font-size: 16pt; font-weight: bold;")
            self.stats_labels[key] = value_label
            card_layout.addWidget(value_label)
            card_layout.addStretch()
            layout.addWidget(card)
        return layout

    def _create_chart_widget(self) -> QGroupBox:
        group = QGroupBox("Evolução Temporal - Gráfico de Linha")
        layout = QVBoxLayout()
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Tipo de Visualização:"))
        self.chart_mode_combo = QComboBox()
        self.chart_mode_combo.setMinimumWidth(200)
        self.chart_mode_combo.addItems(["Evolução Temporal", "Comparação por Ano"])
        self.chart_mode_combo.currentTextChanged.connect(self._plot_chart)
        mode_layout.addWidget(self.chart_mode_combo)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)
        self.canvas = MplCanvas(self, width=10, height=6, dpi=100)
        layout.addWidget(self.canvas)
        group.setLayout(layout)
        return group

    def _create_details_panel(self) -> QFrame:
        panel = QFrame()
        panel.setMinimumWidth(350)
        panel.setMaximumWidth(440)
        main_layout = QVBoxLayout(panel)
        title_container = QFrame()
        title_layout = QVBoxLayout(title_container)
        title_layout.addWidget(QLabel("Análise Detalhada"))
        main_layout.addWidget(title_container)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.details_layout = QVBoxLayout(scroll_content)
        self.details_layout.addStretch()
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)
        return panel

    def _load_filter_options(self) -> None:
        try:
            state = self.view_model.load_initial_state()
            self._fill_combo(self.filter_widgets["cliente"], state.clientes_list)
            self._fill_combo(self.filter_widgets["tipo"], state.tipos_producao)
            self._fill_combo(self.filter_widgets["ano"], [str(ano) for ano in state.anos_disponiveis])
            self._fill_combo(self.filter_widgets["mes"], build_month_options())
            self._fill_combo(self.filter_widgets["status_pagamento"], ["Em aberto", "Parcial", "Pago"])
        except Exception as exc:
            logger.error("Erro ao carregar dados iniciais: %s", exc, exc_info=True)
            QMessageBox.warning(self, "Erro", f"Erro ao carregar dados: {exc}")

    @staticmethod
    def _fill_combo(combo: QComboBox, values: list[str]) -> None:
        combo.blockSignals(True)
        for value in values:
            combo.addItem(value)
        combo.blockSignals(False)

    def _clear_filters(self) -> None:
        for widget in self.filter_widgets.values():
            widget.blockSignals(True)
            widget.setCurrentIndex(0)
            widget.blockSignals(False)
        self._update_chart()

    def _current_filters(self) -> ProductionFilters:
        cliente = self.filter_widgets["cliente"].currentText()
        ano_text = self.filter_widgets["ano"].currentText()
        mes_text = self.filter_widgets["mes"].currentText()
        tipo = self.filter_widgets["tipo"].currentText()
        status = self.filter_widgets["status_pagamento"].currentText()
        return ProductionFilters(
            cliente=cliente if cliente and cliente != "Todos" else None,
            ano=int(ano_text) if ano_text and ano_text != "Todos" else None,
            mes=int(mes_text.split("-")[0].strip()) if mes_text and mes_text != "Todos" else None,
            tipo_producao=tipo if tipo and tipo != "Todos" else None,
            status_pagamento=status if status and status != "Todos" else None,
        )

    def _update_chart(self) -> None:
        try:
            periodos = self.view_model.load_periods(self._current_filters())
            self.dados_financeiros = map_periods_to_dashboard_rows(periodos)
            self._update_statistics()
            self._render_details_panel(self.dados_financeiros)
            self._plot_chart()
        except Exception as exc:
            logger.error("Erro ao atualizar dashboard: %s", exc, exc_info=True)
            QMessageBox.warning(self, "Erro", f"Erro ao atualizar dashboard: {exc}")

    def _update_statistics(self) -> None:
        metrics = compute_dashboard_metrics(self.dados_financeiros)
        self.stats_labels["receita"].setText(metrics.valor_total_fmt)
        self.stats_labels["producoes"].setText(metrics.quantidade_fmt)
        self.stats_labels["ticket"].setText(metrics.ticket_medio_fmt)
        self.stats_labels["crescimento"].setText(metrics.crescimento_fmt)

    def _clear_details_panel(self) -> None:
        while self.details_layout.count() > 0:
            item = self.details_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _render_details_panel(self, rows: list[FinancialDashboardRow]) -> None:
        self._clear_details_panel()
        for dado in recent_dashboard_rows(rows):
            frame = QFrame()
            layout = QVBoxLayout(frame)
            layout.addWidget(QLabel(f"{SHORT_MONTH_NAMES[dado.mes - 1]}/{dado.ano}"))
            valor_fmt = f"R$ {dado.valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            layout.addWidget(QLabel(valor_fmt))
            layout.addWidget(QLabel(f"{dado.quantidade} produções"))
            self.details_layout.insertWidget(0, frame)
        self.details_layout.addStretch()

    def _plot_chart(self) -> None:
        modo = self.chart_mode_combo.currentText() if self.chart_mode_combo else "Evolução Temporal"
        if self.plotter is not None:
            self.plotter.plot_chart(self.dados_financeiros, modo)
