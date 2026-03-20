# -*- coding: utf-8 -*-
"""
Widgets personalizados da apresentação Qt.
"""

import logging

from PyQt6.QtCore import QStringListModel, Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QCompleter, QLineEdit

logger = logging.getLogger(__name__)


class AutocompleteLineEdit(QLineEdit):
    def __init__(self, autocomplete_list: list[str] | None = None, parent=None):
        super().__init__(parent)
        self.autocomplete_list = sorted(autocomplete_list or [], key=str.lower)
        self._completer = QCompleter(self.autocomplete_list, self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completer.setFilterMode(Qt.MatchFlag.MatchStartsWith)
        popup = self._completer.popup()
        if popup is not None:
            popup.setStyleSheet(
            """
            QListView {
                border: 1px solid #CCCCCC;
                background-color: white;
                selection-background-color: #2196F3;
                selection-color: white;
                font-size: 10pt;
            }
            QListView::item {
                padding: 5px;
            }
            QListView::item:hover {
                background-color: #E3F2FD;
            }
            """
            )
        self.setCompleter(self._completer)
        logger.debug("AutocompleteLineEdit initialized with %s items", len(self.autocomplete_list))

    def update_autocomplete_list(self, new_list: list[str]) -> None:
        self.autocomplete_list = sorted(new_list, key=str.lower)
        self._completer.setModel(QStringListModel(self.autocomplete_list))

    def get_autocomplete_list(self) -> list[str]:
        return self.autocomplete_list.copy()


class MoneyLineEdit(QLineEdit):
    value_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cents = 0
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("0,00")
        self.setPlaceholderText("0,00")

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        if event is None:
            return
        key = event.key()
        if key == Qt.Key.Key_Backspace:
            self._cents = self._cents // 10
            self._update_display()
            return

        if key == Qt.Key.Key_Delete or (
            event.modifiers() & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_A
        ):
            self._cents = 0
            self._update_display()
            return

        if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            digit = key - Qt.Key.Key_0
            self._cents = min((self._cents * 10) + digit, 999999)
            self._update_display()
            return

        if key in (
            Qt.Key.Key_Tab,
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
            Qt.Key.Key_Escape,
            Qt.Key.Key_Left,
            Qt.Key.Key_Right,
        ):
            super().keyPressEvent(event)
            return

        event.ignore()

    def _update_display(self) -> None:
        reais = self._cents / 100.0
        formatted = f"{reais:,.2f}".replace(".", ",")
        self.setText(formatted)
        self.value_changed.emit(reais)

    def value(self) -> float:
        return self._cents / 100.0

    def setValue(self, value: float) -> None:
        self._cents = min(int(value * 100), 999999)
        self._update_display()

    def clear(self) -> None:
        self._cents = 0
        self._update_display()
