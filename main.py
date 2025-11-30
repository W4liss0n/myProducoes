# -*- coding: utf-8 -*-
"""
Gerenciador de Produções Fotográficas
Ponto de entrada da aplicação PyQt6
"""
import sys
import logging
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent))

from src.ui.main_window import MainWindow
from src.ui.constants import APP_STYLESHEET, FONT_FAMILY
from src.config.constants import LOG_FILE, DATA_DIR


def setup_logging():
    """Configura o sistema de logging"""
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s',
        encoding='utf-8'
    )

    # Também exibir no console
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    logging.info("=" * 60)
    logging.info("Gerenciador de Produções iniciando...")
    logging.info("=" * 60)


def ensure_directories():
    """Garante que os diretórios necessários existam"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logging.info(f"Diretório de dados: {DATA_DIR}")


def main():
    """Função principal da aplicação"""
    # Configurar logging
    setup_logging()

    # Criar diretórios necessários
    ensure_directories()

    # Criar aplicação Qt
    app = QApplication(sys.argv)

    # Configurar fonte padrão
    font = QFont(FONT_FAMILY, 10)
    app.setFont(font)

    # Aplicar stylesheet global
    app.setStyleSheet(APP_STYLESHEET)

    # Configurar nome da aplicação
    app.setApplicationName("Gerenciador de Produções")
    app.setOrganizationName("MyProducoes")

    # Criar e exibir janela principal
    try:
        window = MainWindow()
        window.show()

        logging.info("Janela principal exibida com sucesso")

        # Executar loop de eventos
        sys.exit(app.exec())

    except Exception as e:
        logging.critical(f"Erro fatal ao iniciar aplicação: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
