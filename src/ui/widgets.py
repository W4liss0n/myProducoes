# -*- coding: utf-8 -*-
"""
Widgets Personalizados para PyQt6
"""
import logging
from typing import List

from PyQt6.QtWidgets import QLineEdit, QCompleter
from PyQt6.QtCore import Qt, QStringListModel, pyqtSignal
from PyQt6.QtGui import QKeyEvent

logger = logging.getLogger(__name__)


class AutocompleteLineEdit(QLineEdit):
    """
    QLineEdit com autocomplete inteligente usando QCompleter
    """

    def __init__(self, autocomplete_list: List[str] = None, parent=None):
        """
        Inicializa o widget de autocomplete

        Args:
            autocomplete_list: Lista de strings para autocomplete
            parent: Widget pai
        """
        super().__init__(parent)

        self.autocomplete_list = sorted(autocomplete_list or [], key=str.lower)

        # Criar e configurar o completer
        self.completer = QCompleter(self.autocomplete_list, self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setFilterMode(Qt.MatchFlag.MatchStartsWith)

        # Estilo do popup
        self.completer.popup().setStyleSheet("""
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
        """)

        self.setCompleter(self.completer)

        logger.debug(f"AutocompleteLineEdit initialized with {len(self.autocomplete_list)} items")

    def update_autocomplete_list(self, new_list: List[str]):
        """
        Atualiza a lista de sugestões

        Args:
            new_list: Nova lista de sugestões
        """
        self.autocomplete_list = sorted(new_list, key=str.lower)

        # Atualizar o modelo do completer
        model = QStringListModel(self.autocomplete_list)
        self.completer.setModel(model)

        logger.debug(f"Autocomplete list updated with {len(self.autocomplete_list)} items")

    def get_autocomplete_list(self) -> List[str]:
        """Retorna a lista atual de autocomplete"""
        return self.autocomplete_list.copy()


class DateEdit(QLineEdit):
    """
    Widget de entrada de data com formato brasileiro (DD/MM/YYYY)
    Pode ser substituído por QDateEdit se preferir um calendário
    """

    def __init__(self, parent=None):
        """Inicializa o widget de data"""
        super().__init__(parent)
        self.setPlaceholderText("DD/MM/AAAA")
        self.setInputMask("99/99/9999")
        self.setMaxLength(10)


class MoneyLineEdit(QLineEdit):
    """
    Campo de entrada de dinheiro estilo caixa registradora
    Digita centavos da direita para esquerda:
    - "1" -> "0,01"
    - "12" -> "0,12"
    - "123" -> "1,23"
    - "1234" -> "12,34"
    """

    valueChanged = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cents = 0  # Armazena valor em centavos
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("0,00")
        self.setPlaceholderText("0,00")

    def keyPressEvent(self, event: QKeyEvent):
        """Captura teclas e formata como dinheiro"""
        key = event.key()

        # Backspace: remove último dígito
        if key == Qt.Key.Key_Backspace:
            self._cents = self._cents // 10
            self._update_display()
            return

        # Delete ou Clear: zera
        if key == Qt.Key.Key_Delete or (event.modifiers() & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_A):
            self._cents = 0
            self._update_display()
            return

        # Números 0-9: adiciona dígito
        if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            digit = key - Qt.Key.Key_0
            self._cents = (self._cents * 10) + digit

            # Limitar a 999999 centavos (9999.99 reais)
            if self._cents > 999999:
                self._cents = 999999

            self._update_display()
            return

        # Tab, Enter, Shift, etc: permitir navegação normal
        if key in [Qt.Key.Key_Tab, Qt.Key.Key_Return, Qt.Key.Key_Enter,
                   Qt.Key.Key_Escape, Qt.Key.Key_Left, Qt.Key.Key_Right]:
            super().keyPressEvent(event)
            return

        # Ignorar outras teclas
        event.ignore()

    def _update_display(self):
        """Atualiza o display com o valor formatado"""
        # Converter centavos para reais
        reais = self._cents / 100.0

        # Formatar como moeda brasileira
        formatted = f"{reais:,.2f}".replace('.', ',')

        self.setText(formatted)
        self.valueChanged.emit(reais)

    def value(self) -> float:
        """Retorna o valor em reais"""
        return self._cents / 100.0

    def setValue(self, value: float):
        """Define o valor em reais"""
        self._cents = int(value * 100)

        # Limitar a 999999 centavos
        if self._cents > 999999:
            self._cents = 999999

        self._update_display()

    def clear(self):
        """Limpa o campo"""
        self._cents = 0
        self._update_display()
