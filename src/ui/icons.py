# -*- coding: utf-8 -*-
"""
Módulo de Ícones usando QtAwesome
"""
import qtawesome as qta
from PyQt6.QtGui import QIcon


class Icons:
    """Gerenciador de ícones usando Font Awesome"""

    # Cores padrão para ícones
    COLOR_PRIMARY = '#2196F3'
    COLOR_SUCCESS = '#4CAF50'
    COLOR_DANGER = '#F44336'
    COLOR_WARNING = '#FF9800'
    COLOR_SECONDARY = '#757575'
    COLOR_WHITE = '#FFFFFF'

    @staticmethod
    def add(color=None) -> QIcon:
        """Ícone de adicionar/novo"""
        return qta.icon('fa5s.plus', color=color or Icons.COLOR_WHITE)

    @staticmethod
    def edit(color=None) -> QIcon:
        """Ícone de editar"""
        return qta.icon('fa5s.edit', color=color or Icons.COLOR_WHITE)

    @staticmethod
    def delete(color=None) -> QIcon:
        """Ícone de deletar"""
        return qta.icon('fa5s.trash', color=color or Icons.COLOR_WHITE)

    @staticmethod
    def save(color=None) -> QIcon:
        """Ícone de salvar"""
        return qta.icon('fa5s.save', color=color or Icons.COLOR_WHITE)

    @staticmethod
    def search(color=None) -> QIcon:
        """Ícone de pesquisar"""
        return qta.icon('fa5s.search', color=color or Icons.COLOR_SECONDARY)

    @staticmethod
    def filter(color=None) -> QIcon:
        """Ícone de filtro"""
        return qta.icon('fa5s.filter', color=color or Icons.COLOR_SECONDARY)

    @staticmethod
    def folder(color=None) -> QIcon:
        """Ícone de pasta"""
        return qta.icon('fa5s.folder-open', color=color or Icons.COLOR_SECONDARY)

    @staticmethod
    def pdf(color=None) -> QIcon:
        """Ícone de PDF"""
        return qta.icon('fa5s.file-pdf', color=color or Icons.COLOR_WHITE)

    @staticmethod
    def settings(color=None) -> QIcon:
        """Ícone de configurações"""
        return qta.icon('fa5s.cog', color=color or Icons.COLOR_WHITE)

    @staticmethod
    def money(color=None) -> QIcon:
        """Ícone de dinheiro"""
        return qta.icon('fa5s.dollar-sign', color=color or Icons.COLOR_WHITE)

    @staticmethod
    def pix(color=None) -> QIcon:
        """Ícone de PIX/pagamento"""
        return qta.icon('fa5s.qrcode', color=color or Icons.COLOR_WHITE)

    @staticmethod
    def chart(color=None) -> QIcon:
        """Ícone de gráfico"""
        return qta.icon('fa5s.chart-bar', color=color or Icons.COLOR_WHITE)

    @staticmethod
    def calendar(color=None) -> QIcon:
        """Ícone de calendário"""
        return qta.icon('fa5s.calendar-alt', color=color or Icons.COLOR_SECONDARY)

    @staticmethod
    def refresh(color=None) -> QIcon:
        """Ícone de atualizar"""
        return qta.icon('fa5s.sync-alt', color=color or Icons.COLOR_WHITE)

    @staticmethod
    def close(color=None) -> QIcon:
        """Ícone de fechar"""
        return qta.icon('fa5s.times', color=color or Icons.COLOR_SECONDARY)

    @staticmethod
    def check(color=None) -> QIcon:
        """Ícone de check/confirmar"""
        return qta.icon('fa5s.check', color=color or Icons.COLOR_SUCCESS)

    @staticmethod
    def info(color=None) -> QIcon:
        """Ícone de informação"""
        return qta.icon('fa5s.info-circle', color=color or Icons.COLOR_PRIMARY)

    @staticmethod
    def warning(color=None) -> QIcon:
        """Ícone de aviso"""
        return qta.icon('fa5s.exclamation-triangle', color=color or Icons.COLOR_WARNING)

    @staticmethod
    def error(color=None) -> QIcon:
        """Ícone de erro"""
        return qta.icon('fa5s.times-circle', color=color or Icons.COLOR_DANGER)

    @staticmethod
    def list(color=None) -> QIcon:
        """Ícone de lista"""
        return qta.icon('fa5s.list', color=color or Icons.COLOR_SECONDARY)

    @staticmethod
    def user(color=None) -> QIcon:
        """Ícone de usuário"""
        return qta.icon('fa5s.user', color=color or Icons.COLOR_SECONDARY)

    @staticmethod
    def company(color=None) -> QIcon:
        """Ícone de empresa"""
        return qta.icon('fa5s.building', color=color or Icons.COLOR_SECONDARY)
