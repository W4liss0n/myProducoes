# -*- coding: utf-8 -*-
"""
Constantes Visuais e Estilos da Interface PyQt6
"""

# ================================
# Cores (Hex)
# ================================
APP_BG_COLOR = "#f0f0f0"          # Fundo principal (cinza claro)
DIALOG_BG_COLOR = "#f8f8f8"       # Fundo de diálogos
PRIMARY_COLOR = "#2196F3"         # Azul primário
PRIMARY_HOVER = "#1976D2"         # Azul escuro (hover)
SECONDARY_COLOR = "#757575"       # Cinza secundário
SECONDARY_HOVER = "#616161"       # Cinza escuro (hover)
SUCCESS_COLOR = "#28a745"         # Verde sucesso (mais vibrante)
DANGER_COLOR = "#dc3545"          # Vermelho perigo
WARNING_COLOR = "#ffc107"         # Amarelo aviso
BLUE_ACTION_COLOR = "#007bff"     # Azul para ações (PDF, etc)

# Treeview/TableWidget
TABLE_HEADER_BG = "#E1E1E1"       # Cabeçalho
TABLE_ODD_ROW_BG = "#ffffff"      # Linha ímpar
TABLE_EVEN_ROW_BG = "#f5f5f5"     # Linha par
TABLE_SELECTED_BG = "#3399FF"     # Seleção
TABLE_BORDER = "#dddddd"          # Bordas

# ================================
# Espaçamentos e Tamanhos
# ================================
PAD_X = 5
PAD_Y = 5
FRAME_PADDING = 8
BUTTON_HEIGHT = 35
INPUT_HEIGHT = 30

# ================================
# Fontes
# ================================
FONT_FAMILY = "Segoe UI"
FONT_SIZE_SMALL = 9
FONT_SIZE_NORMAL = 10
FONT_SIZE_TITLE = 12
FONT_SIZE_LARGE = 14

# ================================
# Estilos PyQt6 (QSS - Qt Style Sheets)
# ================================

# Estilo global da aplicação
APP_STYLESHEET = f"""
    QMainWindow {{
        background-color: {APP_BG_COLOR};
    }}

    QDialog {{
        background-color: {DIALOG_BG_COLOR};
    }}

    /* Botões Primários */
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

    /* Botões Secundários */
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

    /* Botão de Sucesso */
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

    /* Botão de Perigo */
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

    /* Botão Azul de Ação */
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

    /* Campos de Entrada */
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

    /* ComboBox */
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

    /* Labels */
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

    /* GroupBox */
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

    /* TableWidget */
    QTableWidget {{
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

    /* Botão de canto da tabela (quina) */
    QTableCornerButton::section {{
        background-color: {TABLE_HEADER_BG};
        border: none;
        border-right: 1px solid {TABLE_BORDER};
        border-bottom: 2px solid {TABLE_BORDER};
    }}

    /* ScrollBar */
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

    /* MenuBar */
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

    /* StatusBar */
    QStatusBar {{
        background-color: #FAFAFA;
        border-top: 1px solid #E0E0E0;
    }}

    /* ProgressBar */
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
