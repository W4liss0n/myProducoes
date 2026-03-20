# -*- coding: utf-8 -*-
"""
Módulo de ícones usando QtAwesome.
"""

import qtawesome as qta
from PyQt6.QtGui import QIcon


class Icons:
    COLOR_PRIMARY = "#2196F3"
    COLOR_SUCCESS = "#4CAF50"
    COLOR_DANGER = "#F44336"
    COLOR_WARNING = "#FF9800"
    COLOR_SECONDARY = "#757575"
    COLOR_WHITE = "#FFFFFF"

    @staticmethod
    def add(color=None) -> QIcon:
        return qta.icon("fa5s.plus", color=color or Icons.COLOR_WHITE)

    @staticmethod
    def edit(color=None) -> QIcon:
        return qta.icon("fa5s.edit", color=color or Icons.COLOR_WHITE)

    @staticmethod
    def delete(color=None) -> QIcon:
        return qta.icon("fa5s.trash", color=color or Icons.COLOR_WHITE)

    @staticmethod
    def save(color=None) -> QIcon:
        return qta.icon("fa5s.save", color=color or Icons.COLOR_WHITE)

    @staticmethod
    def search(color=None) -> QIcon:
        return qta.icon("fa5s.search", color=color or Icons.COLOR_SECONDARY)

    @staticmethod
    def filter(color=None) -> QIcon:
        return qta.icon("fa5s.filter", color=color or Icons.COLOR_SECONDARY)

    @staticmethod
    def folder(color=None) -> QIcon:
        return qta.icon("fa5s.folder-open", color=color or Icons.COLOR_SECONDARY)

    @staticmethod
    def pdf(color=None) -> QIcon:
        return qta.icon("fa5s.file-pdf", color=color or Icons.COLOR_WHITE)

    @staticmethod
    def settings(color=None) -> QIcon:
        return qta.icon("fa5s.cog", color=color or Icons.COLOR_WHITE)

    @staticmethod
    def money(color=None) -> QIcon:
        return qta.icon("fa5s.dollar-sign", color=color or Icons.COLOR_WHITE)

    @staticmethod
    def pix(color=None) -> QIcon:
        return qta.icon("fa5s.qrcode", color=color or Icons.COLOR_WHITE)

    @staticmethod
    def chart(color=None) -> QIcon:
        return qta.icon("fa5s.chart-bar", color=color or Icons.COLOR_WHITE)

    @staticmethod
    def calendar(color=None) -> QIcon:
        return qta.icon("fa5s.calendar-alt", color=color or Icons.COLOR_SECONDARY)

    @staticmethod
    def refresh(color=None) -> QIcon:
        return qta.icon("fa5s.sync-alt", color=color or Icons.COLOR_WHITE)

    @staticmethod
    def close(color=None) -> QIcon:
        return qta.icon("fa5s.times", color=color or Icons.COLOR_SECONDARY)

    @staticmethod
    def check(color=None) -> QIcon:
        return qta.icon("fa5s.check", color=color or Icons.COLOR_SUCCESS)

    @staticmethod
    def info(color=None) -> QIcon:
        return qta.icon("fa5s.info-circle", color=color or Icons.COLOR_PRIMARY)

    @staticmethod
    def warning(color=None) -> QIcon:
        return qta.icon("fa5s.exclamation-triangle", color=color or Icons.COLOR_WARNING)

    @staticmethod
    def error(color=None) -> QIcon:
        return qta.icon("fa5s.times-circle", color=color or Icons.COLOR_DANGER)

    @staticmethod
    def list(color=None) -> QIcon:
        return qta.icon("fa5s.list", color=color or Icons.COLOR_SECONDARY)

    @staticmethod
    def user(color=None) -> QIcon:
        return qta.icon("fa5s.user", color=color or Icons.COLOR_SECONDARY)

    @staticmethod
    def company(color=None) -> QIcon:
        return qta.icon("fa5s.building", color=color or Icons.COLOR_SECONDARY)
