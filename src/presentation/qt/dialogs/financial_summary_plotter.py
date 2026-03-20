from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime as dt
from typing import Callable, Protocol, Sequence

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.backend_bases import MouseEvent
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.text import Annotation
from matplotlib.ticker import FuncFormatter

from ..types import FinancialDashboardRow


class PlotCanvasProtocol(Protocol):
    axes: Axes
    figure: Figure
    annot: Annotation | None
    hover_enabled: bool

    def draw_idle(self) -> None: ...

    def mpl_connect(self, signal: str, callback: Callable[[MouseEvent], None]) -> int: ...


@dataclass(slots=True)
class YearComparisonSeries:
    ano: int
    meses: list[int]
    valores: list[float]
    cor: str


class FinancialSummaryPlotter:
    def __init__(self, canvas: PlotCanvasProtocol, logger) -> None:
        self.canvas = canvas
        self.logger = logger
        self.lines_data: list[YearComparisonSeries] = []
        self.vline: Line2D | None = None
        self._hover_cid: int | None = None

    def plot_chart(self, dados_financeiros: Sequence[FinancialDashboardRow], modo: str = "Evolução Temporal") -> None:
        self.canvas.axes.clear()

        if not dados_financeiros:
            self.canvas.axes.text(
                0.5,
                0.5,
                "Nenhum dado disponível para os filtros selecionados",
                horizontalalignment="center",
                verticalalignment="center",
                transform=self.canvas.axes.transAxes,
                fontsize=14,
                color="#666666",
            )
            self.canvas.axes.set_xlim((0.0, 1.0))
            self.canvas.axes.set_ylim((0.0, 1.0))
            self.canvas.axes.axis("off")
            self.canvas.draw_idle()
            return

        if modo == "Comparação por Ano":
            self.plot_year_comparison(dados_financeiros)
        else:
            self.plot_temporal_evolution(dados_financeiros)

    def plot_temporal_evolution(self, dados_financeiros: Sequence[FinancialDashboardRow]) -> None:
        self.canvas.hover_enabled = False
        if self.canvas.annot:
            self.canvas.annot.set_visible(False)

        datas = []
        valores = []
        for dado in dados_financeiros:
            datas.append(dt.strptime(dado.data, "%Y-%m-%d"))
            valores.append(dado.valor_total)
        datas_num = mdates.date2num(datas)

        self.canvas.axes.plot(
            datas_num,
            valores,
            marker="o",
            linestyle="-",
            linewidth=3,
            markersize=8,
            color="#2196F3",
            markerfacecolor="#1976D2",
            markeredgecolor="white",
            markeredgewidth=2,
            label="Valor Total",
        )

        if len(datas) <= 36:
            for data_num, valor in zip(datas_num, valores):
                valor_fmt = f"R$ {valor:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
                self.canvas.axes.annotate(
                    valor_fmt,
                    xy=(float(data_num), valor),
                    xytext=(0, 15),
                    textcoords="offset points",
                    ha="center",
                    fontsize=9,
                    color="#1976D2",
                    fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="none", alpha=0.85),
                )

        self.canvas.axes.set_xlabel("Período", fontsize=12, fontweight="bold", color="#424242")
        self.canvas.axes.set_ylabel("Valor Total (R$)", fontsize=12, fontweight="bold", color="#424242")

        if len(datas) > 15:
            self.canvas.axes.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        elif len(datas) > 10:
            self.canvas.axes.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        else:
            self.canvas.axes.xaxis.set_major_locator(mdates.MonthLocator())

        self.canvas.axes.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
        plt.setp(self.canvas.axes.xaxis.get_majorticklabels(), rotation=60, ha="right", fontsize=9)
        self.canvas.axes.yaxis.set_major_formatter(
            FuncFormatter(lambda x, pos: f"R$ {x:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."))
        )
        self.canvas.axes.grid(True, linestyle="--", alpha=0.3, color="#CCCCCC")
        self.canvas.axes.set_axisbelow(True)
        self.canvas.axes.set_facecolor("#FAFAFA")
        self.canvas.figure.tight_layout()
        self.canvas.draw_idle()

    def plot_year_comparison(self, dados_financeiros: Sequence[FinancialDashboardRow]) -> None:
        dados_por_ano: dict[int, dict[int, float]] = {}
        for dado in dados_financeiros:
            dados_por_ano.setdefault(dado.ano, {})[dado.mes] = dado.valor_total

        cores = ["#2196F3", "#4CAF50", "#FF9800", "#9C27B0", "#F44336", "#00BCD4", "#FFC107", "#795548"]
        meses = list(range(1, 13))
        meses_nomes = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

        self.lines_data = []
        for i, ano in enumerate(sorted(dados_por_ano.keys())):
            valores_ano = []
            meses_com_dados = []
            for mes in meses:
                if mes in dados_por_ano[ano]:
                    valores_ano.append(dados_por_ano[ano][mes])
                    meses_com_dados.append(mes)
            if not valores_ano:
                continue

            cor = cores[i % len(cores)]
            self.canvas.axes.plot(
                meses_com_dados,
                valores_ano,
                marker="o",
                linestyle="-",
                linewidth=2.5,
                markersize=7,
                color=cor,
                markerfacecolor=cor,
                markeredgecolor="white",
                markeredgewidth=2,
                label=str(ano),
            )
            self.lines_data.append(YearComparisonSeries(ano=ano, meses=meses_com_dados, valores=valores_ano, cor=cor))

        self.canvas.axes.set_xlabel("Mês", fontsize=12, fontweight="bold", color="#424242")
        self.canvas.axes.set_ylabel("Valor Total (R$)", fontsize=12, fontweight="bold", color="#424242")
        self.canvas.axes.set_xticks(meses)
        self.canvas.axes.set_xticklabels(meses_nomes)
        self.canvas.axes.yaxis.set_major_formatter(
            FuncFormatter(lambda x, pos: f"R$ {x:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."))
        )
        self.canvas.axes.grid(True, linestyle="--", alpha=0.3, color="#CCCCCC")
        self.canvas.axes.set_axisbelow(True)
        self.canvas.axes.set_facecolor("#FAFAFA")
        self.canvas.axes.legend(title="Ano", loc="upper left", frameon=True, fancybox=True, shadow=True)

        if self.canvas.annot is None:
            self.canvas.annot = self.canvas.axes.annotate(
                "",
                xy=(0, 0),
                xytext=(20, 20),
                textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="gray", alpha=0.95),
                arrowprops=dict(arrowstyle="->", color="gray", alpha=0.7),
                fontsize=9,
                fontweight="bold",
            )
            self.canvas.annot.set_visible(False)

        if self.vline is None:
            vline = self.canvas.axes.axvline(x=0, color="gray", linestyle="--", alpha=0.4, linewidth=1)
            vline.set_visible(False)
            self.vline = vline

        if self._hover_cid is None:
            self._hover_cid = self.canvas.mpl_connect("motion_notify_event", self.on_hover_comparison)

        self.canvas.hover_enabled = True
        self.canvas.figure.tight_layout()
        self.canvas.draw_idle()

    def on_hover_comparison(self, event: MouseEvent) -> None:
        if not self.canvas.hover_enabled or event.inaxes != self.canvas.axes:
            if self.canvas.annot and self.canvas.annot.get_visible():
                self.canvas.annot.set_visible(False)
                if self.vline:
                    self.vline.set_visible(False)
                self.canvas.draw_idle()
            return

        x_mouse = event.xdata
        if x_mouse is None or not self.lines_data:
            return

        mes_mais_proximo = round(x_mouse)
        if mes_mais_proximo < 1 or mes_mais_proximo > 12:
            if self.canvas.annot and self.canvas.annot.get_visible():
                self.canvas.annot.set_visible(False)
                if self.vline:
                    self.vline.set_visible(False)
                self.canvas.draw_idle()
            return

        if self.vline:
            self.vline.set_xdata([mes_mais_proximo])
            self.vline.set_visible(True)

        meses_nomes = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        dados_mes = []
        for line_data in self.lines_data:
            if mes_mais_proximo in line_data.meses:
                idx = line_data.meses.index(mes_mais_proximo)
                dados_mes.append(
                    {
                        "ano": line_data.ano,
                        "valor": line_data.valores[idx],
                    }
                )

        if not dados_mes:
            if self.canvas.annot and self.canvas.annot.get_visible():
                self.canvas.annot.set_visible(False)
                if self.vline:
                    self.vline.set_visible(False)
                self.canvas.draw_idle()
            return

        dados_mes.sort(key=lambda item: item["ano"], reverse=True)
        tooltip_lines = [f"{meses_nomes[mes_mais_proximo - 1]}:"]
        for dado in dados_mes:
            valor_fmt = f"R$ {dado['valor']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            tooltip_lines.append(f"{dado['ano']}: {valor_fmt}")

        annotation = self.canvas.annot
        if annotation is None:
            return
        x_pos = mes_mais_proximo
        y_pos = max(dado["valor"] for dado in dados_mes)
        annotation.xy = (x_pos, y_pos)
        annotation.set_text("\n".join(tooltip_lines))
        annotation.set_visible(True)
        self.canvas.draw_idle()
