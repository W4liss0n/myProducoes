# -*- coding: utf-8 -*-
"""
Constantes visuais e estilos da interface PyQt6.
"""

APP_BG_COLOR = "#f0f0f0"
DIALOG_BG_COLOR = "#f8f8f8"
PRIMARY_COLOR = "#2196F3"
PRIMARY_HOVER = "#1976D2"
SECONDARY_COLOR = "#757575"
SECONDARY_HOVER = "#616161"
SUCCESS_COLOR = "#28a745"
DANGER_COLOR = "#dc3545"
WARNING_COLOR = "#ffc107"
BLUE_ACTION_COLOR = "#007bff"

TABLE_HEADER_BG = "#E1E1E1"
TABLE_EVEN_ROW_BG = "#f5f5f5"
TABLE_SELECTED_BG = "#3399FF"
TABLE_BORDER = "#dddddd"

BUTTON_HEIGHT = 35
INPUT_HEIGHT = 30

FONT_FAMILY = "Segoe UI"
FONT_SIZE_NORMAL = 10
FONT_SIZE_TITLE = 12

APP_STYLESHEET = f"""
    QMainWindow {{
        background-color: {APP_BG_COLOR};
    }}

    QDialog {{
        background-color: {DIALOG_BG_COLOR};
    }}

    QPushButton#primaryButton {{
        background-color: {PRIMARY_COLOR};
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        font-size: {FONT_SIZE_NORMAL}pt;
        font-weight: bold;
        min-height: {BUTTON_HEIGHT}px;
    }}

    QPushButton#primaryButton:hover {{
        background-color: {PRIMARY_HOVER};
    }}

    QPushButton#primaryButton:pressed {{
        background-color: #0D47A1;
    }}

    QPushButton#primaryButton:disabled {{
        background-color: #BDBDBD;
        color: #757575;
    }}

    QPushButton#secondaryButton {{
        background-color: {SECONDARY_COLOR};
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        font-size: {FONT_SIZE_NORMAL}pt;
        min-height: {BUTTON_HEIGHT}px;
    }}

    QPushButton#secondaryButton:hover {{
        background-color: {SECONDARY_HOVER};
    }}

    QPushButton#secondaryButton:pressed {{
        background-color: #424242;
    }}

    QPushButton#successButton {{
        background-color: {SUCCESS_COLOR};
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        font-size: {FONT_SIZE_NORMAL}pt;
        font-weight: bold;
        min-height: {BUTTON_HEIGHT}px;
    }}

    QPushButton#successButton:hover {{
        background-color: #218838;
    }}

    QPushButton#dangerButton {{
        background-color: {DANGER_COLOR};
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        font-size: {FONT_SIZE_NORMAL}pt;
        min-height: {BUTTON_HEIGHT}px;
    }}

    QPushButton#dangerButton:hover {{
        background-color: #D32F2F;
    }}

    QPushButton#blueActionButton {{
        background-color: {BLUE_ACTION_COLOR};
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        font-size: {FONT_SIZE_NORMAL}pt;
        font-weight: bold;
        min-height: {BUTTON_HEIGHT}px;
    }}

    QPushButton#blueActionButton:hover {{
        background-color: #0056b3;
    }}

    QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        border: 1px solid #CCCCCC;
        border-radius: 4px;
        padding: 6px;
        background-color: white;
        min-height: {INPUT_HEIGHT}px;
        font-size: {FONT_SIZE_NORMAL}pt;
    }}

    QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
        border: 2px solid {PRIMARY_COLOR};
    }}

    QLineEdit:disabled, QComboBox:disabled {{
        background-color: #F5F5F5;
        color: #9E9E9E;
    }}

    QComboBox::drop-down {{
        border: none;
        padding-right: 8px;
    }}

    QComboBox::down-arrow {{
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid #666666;
        margin-right: 8px;
    }}

    QLabel {{
        color: #212121;
        font-size: {FONT_SIZE_NORMAL}pt;
    }}

    QLabel#titleLabel {{
        font-size: {FONT_SIZE_TITLE}pt;
        font-weight: bold;
        color: #1976D2;
    }}

    QLabel#subtitleLabel {{
        font-size: {FONT_SIZE_NORMAL}pt;
        font-weight: bold;
        color: #424242;
    }}

    QGroupBox {{
        border: 1px solid #CCCCCC;
        border-radius: 4px;
        margin-top: 8px;
        font-weight: bold;
        padding: 10px;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px;
        color: #1976D2;
    }}

    QTableWidget, QTableView {{
        border: 1px solid {TABLE_BORDER};
        gridline-color: {TABLE_BORDER};
        background-color: white;
        alternate-background-color: {TABLE_EVEN_ROW_BG};
        selection-background-color: {TABLE_SELECTED_BG};
        selection-color: white;
    }}

    QTableWidget::item {{
        padding: 5px;
    }}

    QHeaderView::section {{
        background-color: {TABLE_HEADER_BG};
        color: #212121;
        padding: 8px;
        border: none;
        border-right: 1px solid {TABLE_BORDER};
        border-bottom: 2px solid {TABLE_BORDER};
        font-weight: bold;
    }}

    QTableCornerButton::section {{
        background-color: {TABLE_HEADER_BG};
        border: none;
        border-right: 1px solid {TABLE_BORDER};
        border-bottom: 2px solid {TABLE_BORDER};
    }}

    QScrollBar:vertical {{
        border: none;
        background: #F5F5F5;
        width: 12px;
        margin: 0;
    }}

    QScrollBar::handle:vertical {{
        background: #BDBDBD;
        border-radius: 6px;
        min-height: 20px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: #9E9E9E;
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        border: none;
        background: #F5F5F5;
        height: 12px;
        margin: 0;
    }}

    QScrollBar::handle:horizontal {{
        background: #BDBDBD;
        border-radius: 6px;
        min-width: 20px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background: #9E9E9E;
    }}

    QMenuBar {{
        background-color: white;
        border-bottom: 1px solid #E0E0E0;
    }}

    QMenuBar::item {{
        padding: 8px 12px;
    }}

    QMenuBar::item:selected {{
        background-color: #E3F2FD;
    }}

    QMenu {{
        background-color: white;
        border: 1px solid #E0E0E0;
    }}

    QMenu::item {{
        padding: 8px 24px;
    }}

    QMenu::item:selected {{
        background-color: #E3F2FD;
    }}

    QStatusBar {{
        background-color: #FAFAFA;
        border-top: 1px solid #E0E0E0;
    }}

    QProgressBar {{
        border: 1px solid #CCCCCC;
        border-radius: 4px;
        text-align: center;
        background-color: #F5F5F5;
    }}

    QProgressBar::chunk {{
        background-color: {PRIMARY_COLOR};
        border-radius: 3px;
    }}
"""
