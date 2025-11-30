# -*- coding: utf-8 -*-
"""
Configurações e Constantes Globais do Sistema
"""
from pathlib import Path

# ================================
# Caminhos de Arquivos
# ================================
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = DATA_DIR / "backups"

# Banco de dados SQLite (substituindo Excel)
DATABASE_FILE = DATA_DIR / "productions.db"

# Arquivos de configuração
TIPOS_PRODUCAO_FILE = DATA_DIR / "tipos_producao.txt"
CONFIG_PIX_FILE = DATA_DIR / 'config_pix.json'
REPORT_PATHS_FILE = DATA_DIR / "report_paths.json"
COLUMNS_CONFIG_FILE = DATA_DIR / 'columns_config.json'
LOG_FILE = BASE_DIR / 'production_manager.log'

# Configurações de backup
MAX_BACKUPS = 10

# ================================
# Colunas do Banco de Dados
# ================================
ALL_COLUMNS = [
    "Código", "Cliente", "Data de Recebimento", "Nome", "Tipo de Produção",
    "Quant. Alunos", "Quant. Fotos", "Quant. Kits", "Quant. Capas",
    "Valor por Foto", "Valor por Kit", "Valor por Capa", "Valor Total",
    "Data de Conclusão", "Status Pagamento", "Status", "Relatório"
]

DEFAULT_COLUMNS = ALL_COLUMNS

# Colunas visíveis por padrão (otimizado para melhor visualização)
DEFAULT_VISIBLE_COLUMNS = [
    "Cliente", "Nome", "Tipo de Produção",
    "Quant. Alunos", "Quant. Fotos", "Valor Total",
    "Data de Conclusão", "Status", "Status Pagamento"
]

EDITABLE_COLUMNS = [col for col in ALL_COLUMNS if col not in ["Código", "Valor Total", "Relatório"]]

# Tipos de colunas para validação
NUMERIC_COLUMNS = {
    'Quant. Alunos': int,
    'Quant. Fotos': int,
    'Quant. Kits': int,
    'Quant. Capas': int,
    'Valor por Foto': float,
    'Valor por Kit': float,
    'Valor por Capa': float,
    'Valor Total': float
}

DATE_COLUMNS = ["Data de Recebimento", "Data de Conclusão"]

# ================================
# Opções Padrão
# ================================
DEFAULT_STATUS_OPTIONS = ['Parado', 'Em Andamento', 'Finalizado']
DEFAULT_STATUS_PAGAMENTO_OPTIONS = ["Em aberto", "Pago"]
DEFAULT_TIPOS_PRODUCAO = ["Formatura", "Newborn", "Casamento"]

# ================================
# Geração de Relatórios
# ================================
IMG_EXTENSIONS = {'.jpg', '.jpeg', '.png'}

# ================================
# Configuração de Logging
# ================================
LOG_CONFIG = {
    'filename': str(LOG_FILE),
    'level': 'INFO',
    'format': '%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
}
