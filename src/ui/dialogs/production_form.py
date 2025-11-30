# -*- coding: utf-8 -*-
"""
Diálogo de Formulário de Produção (Adicionar/Editar) - PyQt6
Layout Horizontal Otimizado
"""
import logging
import os
from typing import Dict, Any, Optional, Callable, List, Tuple
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QGroupBox,
    QWidget, QMessageBox, QFileDialog, QDateEdit, QSpinBox
)
from PyQt6.QtCore import Qt, QDate
import qtawesome as qta

from ..constants import PAD_X, PAD_Y
from ..widgets import AutocompleteLineEdit, MoneyLineEdit
from ..icons import Icons
from ...core.pdf_generator import PDFGenerator

logger = logging.getLogger(__name__)


class ProductionFormDialog(QDialog):
    """Diálogo unificado para adicionar ou editar produções - Layout Horizontal"""

    def __init__(
        self,
        parent=None,
        mode: str = 'add',
        initial_data: Optional[Dict[str, Any]] = None,
        tipos_producao: Optional[List[str]] = None,
        clientes_list: Optional[List[str]] = None,
        on_save: Optional[Callable] = None
    ):
        """
        Inicializa o diálogo

        Args:
            parent: Widget pai
            mode: 'add' para adicionar ou 'edit' para editar
            initial_data: Dados iniciais (para modo edição)
            tipos_producao: Lista de tipos de produção disponíveis
            clientes_list: Lista de clientes para autocomplete
            on_save: Callback chamado ao salvar (recebe dicionário com dados)
        """
        super().__init__(parent)

        self.mode = mode
        self.initial_data = initial_data or {}
        self.tipos_producao = tipos_producao or []
        self.clientes_list = clientes_list or []
        self.on_save_callback = on_save

        self.widgets: Dict[str, QWidget] = {}
        self.pasta_producao = self.initial_data.get('Pasta Produção', '') or ""
        self.result_data = None

        # Labels para exibir valores calculados
        self.label_valor_total = None

        self._setup_ui()
        self._connect_signals()
        self._calculate_total()

    def _setup_ui(self):
        """Configura a interface do diálogo"""
        # Título dinâmico
        if self.mode == 'add':
            title = "Adicionar Produção"
        else:
            cliente = self.initial_data.get('Cliente', '')
            title = f"Editar Produção - {cliente}"

        self.setWindowTitle(title)

        # Tamanho fixo - não redimensionável
        self.setFixedSize(1000, 580)

        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Layout de conteúdo (2 colunas)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)

        # Coluna Esquerda - Informações Gerais
        left_group = self._create_info_group()
        content_layout.addWidget(left_group, stretch=1)

        # Coluna Direita - Quantidades, Valores e Relatórios
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)

        quantities_group = self._create_quantities_group()
        right_layout.addWidget(quantities_group)

        values_group = self._create_values_group()
        right_layout.addWidget(values_group)

        reports_group = self._create_reports_group()
        right_layout.addWidget(reports_group)

        content_layout.addLayout(right_layout, stretch=1)

        main_layout.addLayout(content_layout, stretch=1)

        # Espaçador flexível para empurrar botões para baixo
        main_layout.addStretch()

        # Botões
        button_layout = self._create_button_layout()
        main_layout.addLayout(button_layout)

    def _create_info_group(self) -> QGroupBox:
        """Cria o grupo de informações gerais"""
        group = QGroupBox("Informações Gerais")
        main_layout = QVBoxLayout(group)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Cliente
        label_layout = QHBoxLayout()
        label_layout.setSpacing(5)
        label_layout.addWidget(qta.IconWidget('fa5s.user', color='#555'))
        label_layout.addWidget(QLabel("Cliente*"))
        label_layout.addStretch()
        main_layout.addLayout(label_layout)

        cliente_input = AutocompleteLineEdit(self.clientes_list)
        cliente_input.setText(str(self.initial_data.get('Cliente', '')))
        main_layout.addWidget(cliente_input)
        self.widgets['Cliente'] = cliente_input

        # Nome
        label_layout = QHBoxLayout()
        label_layout.setSpacing(5)
        label_layout.addWidget(qta.IconWidget('fa5s.file-alt', color='#555'))
        label_layout.addWidget(QLabel("Nome*"))
        label_layout.addStretch()
        main_layout.addLayout(label_layout)

        nome_input = QLineEdit()
        nome_input.setText(str(self.initial_data.get('Nome', '')))
        main_layout.addWidget(nome_input)
        self.widgets['Nome'] = nome_input

        # Tipo Serviço
        label_layout = QHBoxLayout()
        label_layout.setSpacing(5)
        label_layout.addWidget(qta.IconWidget('fa5s.tag', color='#555'))
        label_layout.addWidget(QLabel("Tipo Serviço*"))
        label_layout.addStretch()
        main_layout.addLayout(label_layout)

        tipo_input = QComboBox()
        tipo_input.addItems(self.tipos_producao)
        initial_tipo = self.initial_data.get('Tipo de Produção', '')
        if initial_tipo:
            index = tipo_input.findText(str(initial_tipo))
            if index >= 0:
                tipo_input.setCurrentIndex(index)
        main_layout.addWidget(tipo_input)
        self.widgets['Tipo de Produção'] = tipo_input

        # Data Recebimento
        label_layout = QHBoxLayout()
        label_layout.setSpacing(5)
        label_layout.addWidget(qta.IconWidget('fa5s.calendar-alt', color='#555'))
        label_layout.addWidget(QLabel("Data Recebimento*"))
        label_layout.addStretch()
        main_layout.addLayout(label_layout)

        data_receb_input = QDateEdit()
        data_receb_input.setCalendarPopup(True)
        data_receb_input.setDisplayFormat("dd/MM/yyyy")
        self._set_date_value(data_receb_input, self.initial_data.get('Data de Recebimento', ''))
        main_layout.addWidget(data_receb_input)
        self.widgets['Data de Recebimento'] = data_receb_input

        # Data Conclusão
        label_layout = QHBoxLayout()
        label_layout.setSpacing(5)
        label_layout.addWidget(qta.IconWidget('fa5s.calendar-check', color='#555'))
        label_layout.addWidget(QLabel("Data Conclusão"))
        label_layout.addStretch()
        main_layout.addLayout(label_layout)

        data_conc_input = QDateEdit()
        data_conc_input.setCalendarPopup(True)
        data_conc_input.setDisplayFormat("dd/MM/yyyy")
        self._set_date_value(data_conc_input, self.initial_data.get('Data de Conclusão', ''))
        main_layout.addWidget(data_conc_input)
        self.widgets['Data de Conclusão'] = data_conc_input

        # Status e Status Pagamento (labels lado a lado)
        labels_layout = QHBoxLayout()
        labels_layout.setSpacing(10)

        status_label_layout = QHBoxLayout()
        status_label_layout.setSpacing(5)
        status_label_layout.addWidget(qta.IconWidget('fa5s.tasks', color='#555'))
        status_label_layout.addWidget(QLabel("Status*"))
        status_label_layout.addStretch()
        labels_layout.addLayout(status_label_layout)

        status_pag_label_layout = QHBoxLayout()
        status_pag_label_layout.setSpacing(5)
        status_pag_label_layout.addWidget(qta.IconWidget('fa5s.money-bill-wave', color='#555'))
        status_pag_label_layout.addWidget(QLabel("Status Pagamento*"))
        status_pag_label_layout.addStretch()
        labels_layout.addLayout(status_pag_label_layout)

        main_layout.addLayout(labels_layout)

        # Inputs lado a lado
        inputs_layout = QHBoxLayout()
        inputs_layout.setSpacing(10)

        status_input = QComboBox()
        status_input.addItems(['Parado', 'Em Andamento', 'Finalizado'])
        status_input.setCurrentText(str(self.initial_data.get('Status', 'Parado')))
        inputs_layout.addWidget(status_input)
        self.widgets['Status'] = status_input

        status_pag_input = QComboBox()
        status_pag_input.addItems(['Em aberto', 'Pago'])
        status_pag_input.setCurrentText(str(self.initial_data.get('Status Pagamento', 'Em aberto')))
        inputs_layout.addWidget(status_pag_input)
        self.widgets['Status Pagamento'] = status_pag_input

        main_layout.addLayout(inputs_layout)

        return group

    def _create_quantities_group(self) -> QGroupBox:
        """Cria o grupo de quantidades"""
        group = QGroupBox("Quantidades")
        layout = QGridLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        # Headers com ícones
        quantities = [
            ('fa5s.users', 'Alunos', 'Quant. Alunos'),
            ('fa5s.camera', 'Fotos', 'Quant. Fotos'),
            ('fa5s.box', 'Kits', 'Quant. Kits'),
            ('fa5s.book', 'Capas', 'Quant. Capas'),
        ]

        for col, (icon_name, label_text, key) in enumerate(quantities):
            # Header com ícone
            header_layout = QHBoxLayout()
            header_layout.setSpacing(4)
            header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            icon_label = QLabel()
            icon_label.setPixmap(qta.icon(icon_name, color='#555').pixmap(14, 14))
            header_layout.addWidget(icon_label)
            header_layout.addWidget(QLabel(label_text))

            header_widget = QWidget()
            header_widget.setLayout(header_layout)
            layout.addWidget(header_widget, 0, col, Qt.AlignmentFlag.AlignCenter)

            # Campo de input
            widget = QLineEdit()
            widget.setText(str(self.initial_data.get(key, '0')))
            widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            widget.setMaximumWidth(100)
            layout.addWidget(widget, 1, col, Qt.AlignmentFlag.AlignCenter)
            self.widgets[key] = widget

        return group

    def _create_values_group(self) -> QGroupBox:
        """Cria o grupo de valores"""
        group = QGroupBox("Valores Unitários")
        layout = QGridLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        # Headers com ícones
        values = [
            ('fa5s.dollar-sign', 'R$/Foto', 'Valor por Foto'),
            ('fa5s.dollar-sign', 'R$/Kit', 'Valor por Kit'),
            ('fa5s.dollar-sign', 'R$/Capa', 'Valor por Capa'),
        ]

        for col, (icon_name, label_text, key) in enumerate(values):
            # Header com ícone
            header_layout = QHBoxLayout()
            header_layout.setSpacing(4)
            header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            icon_label = QLabel()
            icon_label.setPixmap(qta.icon(icon_name, color='#28a745').pixmap(14, 14))
            header_layout.addWidget(icon_label)
            header_layout.addWidget(QLabel(label_text))

            header_widget = QWidget()
            header_widget.setLayout(header_layout)
            layout.addWidget(header_widget, 0, col, Qt.AlignmentFlag.AlignCenter)

            # Campo de input estilo caixa registradora
            widget = MoneyLineEdit()
            widget.setMaximumWidth(120)

            # Definir valor inicial
            initial_value = self.initial_data.get(key, 0.0)
            if isinstance(initial_value, str):
                try:
                    initial_value = float(initial_value.replace(',', '.'))
                except:
                    initial_value = 0.0
            widget.setValue(float(initial_value))

            layout.addWidget(widget, 1, col, Qt.AlignmentFlag.AlignCenter)
            self.widgets[key] = widget

        # Valor Total (calculado)
        layout.addWidget(QLabel(""), 2, 0, 1, 3)  # Espaçador

        total_layout = QHBoxLayout()
        total_layout.setSpacing(8)

        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.coins', color='#28a745').pixmap(18, 18))
        total_layout.addWidget(icon_label)

        total_layout.addWidget(QLabel("Valor Total:"))

        self.label_valor_total = QLabel("R$ 0,00")
        self.label_valor_total.setStyleSheet("font-weight: bold; color: #28a745; font-size: 14px;")
        total_layout.addWidget(self.label_valor_total)

        total_layout.addWidget(QLabel("(calculado automaticamente)"))
        total_layout.addStretch()

        total_widget = QWidget()
        total_widget.setLayout(total_layout)
        layout.addWidget(total_widget, 3, 0, 1, 3)

        return group

    def _create_reports_group(self) -> QGroupBox:
        """Cria o grupo de relatórios"""
        group = QGroupBox("Relatórios")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        # Botão Gerar PDF
        btn_gerar_pdf = QPushButton("Gerar Relatório PDF")
        btn_gerar_pdf.setIcon(qta.icon('fa5s.file-pdf', color='#dc3545'))
        btn_gerar_pdf.clicked.connect(self._gerar_relatorio_pdf)
        btn_gerar_pdf.setMinimumHeight(40)
        layout.addWidget(btn_gerar_pdf)

        # Label de informação
        info_label = QLabel("Gera relatório detalhado dos alunos\ncom fotos e kits por aluno")
        info_label.setStyleSheet("color: #666; font-size: 11px;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)

        return group

    def _create_button_layout(self) -> QHBoxLayout:
        """Cria o layout de botões"""
        button_layout = QHBoxLayout()

        # Botão Selecionar Pasta (à esquerda)
        btn_folder = QPushButton("Selecionar Pasta da Produção")
        btn_folder.setObjectName("secondaryButton")
        btn_folder.setIcon(qta.icon('fa5s.folder', color='#666'))
        btn_folder.clicked.connect(self._select_folder)
        btn_folder.setMinimumWidth(180)
        button_layout.addWidget(btn_folder)

        button_layout.addStretch()

        # Botão Cancelar
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("secondaryButton")
        btn_cancel.setIcon(qta.icon('fa5s.times', color='#666'))
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setMinimumWidth(120)
        button_layout.addWidget(btn_cancel)

        # Botão Salvar
        save_text = "Salvar Alterações" if self.mode == 'edit' else "Adicionar Produção"
        btn_save = QPushButton(save_text)
        btn_save.setObjectName("successButton" if self.mode == 'add' else "primaryButton")
        btn_save.setIcon(qta.icon('fa5s.save', color='white'))
        btn_save.clicked.connect(self._on_save)
        btn_save.setMinimumWidth(150)
        button_layout.addWidget(btn_save)

        return button_layout

    def _set_date_value(self, widget: QDateEdit, value):
        """Define o valor de um QDateEdit"""
        if value:
            try:
                if isinstance(value, str):
                    # Tentar vários formatos
                    for fmt in ['%d/%m/%Y', '%Y-%m-%d']:
                        try:
                            date_obj = datetime.strptime(value.split()[0], fmt)
                            widget.setDate(QDate(date_obj.year, date_obj.month, date_obj.day))
                            return
                        except:
                            continue
                widget.setDate(QDate.currentDate())
            except:
                widget.setDate(QDate.currentDate())
        else:
            widget.setDate(QDate.currentDate())

    def _connect_signals(self):
        """Conecta sinais para cálculo automático"""
        # Conectar mudanças nos campos numéricos para recalcular total
        for key in ['Quant. Fotos', 'Valor por Foto', 'Quant. Kits', 'Valor por Kit',
                    'Quant. Capas', 'Valor por Capa']:
            if key in self.widgets:
                widget = self.widgets[key]
                if isinstance(widget, MoneyLineEdit):
                    widget.valueChanged.connect(self._calculate_total)
                elif isinstance(widget, QLineEdit):
                    widget.textChanged.connect(self._calculate_total)

    def _calculate_total(self):
        """Calcula o valor total automaticamente"""
        try:
            total = 0.0

            # Fotos
            qtd_fotos_widget = self.widgets.get('Quant. Fotos')
            qtd_fotos = int(qtd_fotos_widget.text() or 0) if isinstance(qtd_fotos_widget, QLineEdit) else 0

            val_foto_widget = self.widgets.get('Valor por Foto')
            val_foto = val_foto_widget.value() if isinstance(val_foto_widget, MoneyLineEdit) else 0.0
            total += qtd_fotos * val_foto

            # Kits
            qtd_kits_widget = self.widgets.get('Quant. Kits')
            qtd_kits = int(qtd_kits_widget.text() or 0) if isinstance(qtd_kits_widget, QLineEdit) else 0

            val_kit_widget = self.widgets.get('Valor por Kit')
            val_kit = val_kit_widget.value() if isinstance(val_kit_widget, MoneyLineEdit) else 0.0
            total += qtd_kits * val_kit

            # Capas
            qtd_capas_widget = self.widgets.get('Quant. Capas')
            qtd_capas = int(qtd_capas_widget.text() or 0) if isinstance(qtd_capas_widget, QLineEdit) else 0

            val_capa_widget = self.widgets.get('Valor por Capa')
            val_capa = val_capa_widget.value() if isinstance(val_capa_widget, MoneyLineEdit) else 0.0
            total += qtd_capas * val_capa

            # Atualizar label
            if self.label_valor_total:
                self.label_valor_total.setText(f"R$ {total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

        except Exception as e:
            if self.label_valor_total:
                self.label_valor_total.setText("R$ 0,00")

    def _select_folder(self):
        """Abre diálogo para selecionar pasta e calcula quantidades automaticamente"""
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta da Produção")
        if folder:
            self.pasta_producao = folder

            # Extrair nome da pasta (último componente do caminho)
            nome_pasta = os.path.basename(folder)

            # Preencher campo Nome automaticamente
            if 'Nome' in self.widgets and nome_pasta:
                self.widgets['Nome'].setText(nome_pasta)

            # Calcular quantidades automaticamente
            try:
                fotos, alunos, kits = self._calcular_quantidades(folder)

                # Atualizar campos do formulário
                if 'Quant. Fotos' in self.widgets:
                    self.widgets['Quant. Fotos'].setText(str(fotos))

                if 'Quant. Alunos' in self.widgets:
                    self.widgets['Quant. Alunos'].setText(str(alunos))

                if 'Quant. Kits' in self.widgets:
                    self.widgets['Quant. Kits'].setText(str(kits))

            except Exception as e:
                logger.error(f"Erro ao calcular quantidades: {e}", exc_info=True)
                QMessageBox.warning(
                    self,
                    "Aviso",
                    f"Não foi possível calcular as quantidades automaticamente.\nErro: {e}"
                )

    def _encontrar_pasta(self, pasta_base: str, nome_busca: str) -> Optional[str]:
        """
        Encontra uma pasta que contenha o nome_busca (case insensitive)

        Args:
            pasta_base: Pasta onde buscar
            nome_busca: Nome a procurar (ex: "albuns", "kits")

        Returns:
            Caminho completo da pasta encontrada ou None
        """
        try:
            for item in os.listdir(pasta_base):
                caminho = os.path.join(pasta_base, item)
                if os.path.isdir(caminho):
                    if nome_busca.lower() in item.lower():
                        return caminho
        except Exception as e:
            logger.error(f"Erro ao procurar pasta '{nome_busca}' em '{pasta_base}': {e}")
        return None

    def _contar_pastas_com_fotos_diretas(self, pasta_raiz: str, extensoes_imagem: set) -> tuple[int, int]:
        """
        Conta recursivamente pastas que contêm fotos diretamente (não em subpastas)
        e o total de fotos

        Args:
            pasta_raiz: Pasta raiz para buscar
            extensoes_imagem: Set de extensões válidas

        Returns:
            Tupla (total_fotos, total_pastas_com_fotos)
        """
        total_fotos = 0
        total_pastas = 0

        def percorrer_recursivo(pasta_atual: str):
            nonlocal total_fotos, total_pastas

            try:
                fotos_nesta_pasta = 0
                tem_subpastas = False

                for item in os.listdir(pasta_atual):
                    caminho_completo = os.path.join(pasta_atual, item)

                    if os.path.isdir(caminho_completo):
                        tem_subpastas = True
                        # Continuar recursão
                        percorrer_recursivo(caminho_completo)
                    elif os.path.isfile(caminho_completo):
                        ext = os.path.splitext(item.lower())[1]
                        if ext in extensoes_imagem:
                            fotos_nesta_pasta += 1
                            total_fotos += 1

                # Se tem fotos diretamente nesta pasta, conta como 1 aluno
                if fotos_nesta_pasta > 0:
                    total_pastas += 1

            except Exception as e:
                logger.error(f"Erro ao percorrer pasta '{pasta_atual}': {e}")

        percorrer_recursivo(pasta_raiz)
        return total_fotos, total_pastas

    def _calcular_quantidades(self, pasta_producao: str) -> tuple[int, int, int]:
        """
        Calcula quantidades de fotos, alunos e kits baseado na estrutura da pasta

        Estrutura flexível:
        - Busca pasta que contém "albuns" (case insensitive, ex: "04 - Albuns")
        - Suporta múltiplos níveis: Albuns/Turma 1/Turma A/Aluno/fotos
        - Busca pasta que contém "kits" para calcular kits

        Args:
            pasta_producao: Caminho da pasta da produção

        Returns:
            Tupla (fotos, alunos, kits)
        """
        # Extensões de imagem válidas
        extensoes_imagem = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.heic'}

        total_fotos = 0
        total_alunos = 0
        total_kits = 0

        # 1. Procurar pasta de Albuns (flexível: "Albuns", "albuns", "04 - Albuns", etc)
        pasta_albuns = self._encontrar_pasta(pasta_producao, 'albuns')
        if pasta_albuns:
            total_fotos, total_alunos = self._contar_pastas_com_fotos_diretas(pasta_albuns, extensoes_imagem)

        # 2. Calcular kits na pasta Kits (flexível: "Kits", "kits", "05 - Kits", etc)
        pasta_kits = self._encontrar_pasta(pasta_producao, 'kits')
        if pasta_kits:
            # Dicionário para contar fotos por aluno (ID)
            fotos_por_aluno = {}

            # Percorrer todas as pastas dentro de Kits (tamanhos: 10x15, 24x30, etc)
            try:
                for tamanho in os.listdir(pasta_kits):
                    caminho_tamanho = os.path.join(pasta_kits, tamanho)
                    if os.path.isdir(caminho_tamanho):
                        # Iterar pelas fotos dentro da pasta de tamanho
                        for arquivo in os.listdir(caminho_tamanho):
                            ext = os.path.splitext(arquivo.lower())[1]
                            if ext in extensoes_imagem:
                                # Extrair ID do aluno do nome do arquivo (sem extensão)
                                nome_sem_ext = os.path.splitext(arquivo)[0]
                                # Pegar apenas a parte antes do underscore
                                # Ex: "001_I" -> "001", "001_II" -> "001", "001" -> "001"
                                aluno_id = nome_sem_ext.split('_')[0].strip()

                                # Contar foto para este aluno
                                if aluno_id not in fotos_por_aluno:
                                    fotos_por_aluno[aluno_id] = 0
                                fotos_por_aluno[aluno_id] += 1
            except Exception as e:
                logger.error(f"Erro ao processar pasta Kits: {e}")

            # Calcular kits: para cada aluno, 3 fotos = 1 kit
            for aluno_id, num_fotos in fotos_por_aluno.items():
                kits_aluno = num_fotos // 3
                total_kits += kits_aluno

        return total_fotos, total_alunos, total_kits

    def _extrair_dados_alunos(self, pasta_producao: str) -> List[Dict[str, Any]]:
        """
        Extrai dados detalhados de cada aluno para o relatório

        Args:
            pasta_producao: Caminho da pasta da produção

        Returns:
            Lista de dicionários com dados dos alunos:
            [{'id': 'Aluno1', 'fotos': 10, 'kits': 2, 'curso': 'Turma Manhã - A'}, ...]
        """
        extensoes_imagem = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.heic'}
        alunos_data = {}

        # 1. Percorrer pasta Albuns para coletar alunos, fotos e cursos
        pasta_albuns = self._encontrar_pasta(pasta_producao, 'albuns')
        if pasta_albuns:
            def percorrer_albuns(pasta_atual: str, caminho_curso: List[str] = None, nome_pasta_atual: str = None):
                """Percorre recursivamente a estrutura de Albuns"""
                if caminho_curso is None:
                    caminho_curso = []

                try:
                    tem_fotos_diretas = False
                    fotos_count = 0
                    subpastas = []

                    # Verificar se há fotos e coletar subpastas
                    for item in os.listdir(pasta_atual):
                        caminho_completo = os.path.join(pasta_atual, item)

                        if os.path.isfile(caminho_completo):
                            ext = os.path.splitext(item.lower())[1]
                            if ext in extensoes_imagem:
                                tem_fotos_diretas = True
                                fotos_count += 1
                        elif os.path.isdir(caminho_completo):
                            subpastas.append((item, caminho_completo))

                    # Se esta pasta tem fotos, é uma pasta de aluno
                    if tem_fotos_diretas:
                        aluno_id = os.path.basename(pasta_atual)
                        # Curso não inclui o nome da pasta do aluno
                        curso = ' - '.join(caminho_curso) if caminho_curso else ''

                        alunos_data[aluno_id] = {
                            'id': aluno_id,
                            'fotos': fotos_count,
                            'kits': 0,  # Será preenchido depois
                            'capas': 0,  # Por enquanto sempre 0
                            'curso': curso
                        }
                    else:
                        # Se não tem fotos, é uma pasta intermediária (turma)
                        # Adicionar o nome desta pasta ao caminho do curso
                        novo_caminho_base = caminho_curso.copy()
                        if nome_pasta_atual:
                            novo_caminho_base.append(nome_pasta_atual)

                        # Continuar percorrendo subpastas
                        for nome_subpasta, caminho_subpasta in subpastas:
                            percorrer_albuns(caminho_subpasta, novo_caminho_base, nome_subpasta)

                except Exception as e:
                    logger.error(f"Erro ao percorrer Albuns em '{pasta_atual}': {e}")

            percorrer_albuns(pasta_albuns)

        # 2. Calcular kits baseado na pasta Kits
        pasta_kits = self._encontrar_pasta(pasta_producao, 'kits')
        if pasta_kits:
            fotos_por_aluno = {}

            try:
                # Percorrer pastas de tamanho (10x15, 24x30, etc)
                for tamanho in os.listdir(pasta_kits):
                    caminho_tamanho = os.path.join(pasta_kits, tamanho)
                    if os.path.isdir(caminho_tamanho):
                        for arquivo in os.listdir(caminho_tamanho):
                            ext = os.path.splitext(arquivo.lower())[1]
                            if ext in extensoes_imagem:
                                # Extrair ID do aluno (parte antes do _)
                                nome_sem_ext = os.path.splitext(arquivo)[0]
                                aluno_id = nome_sem_ext.split('_')[0].strip()

                                if aluno_id not in fotos_por_aluno:
                                    fotos_por_aluno[aluno_id] = 0
                                fotos_por_aluno[aluno_id] += 1
            except Exception as e:
                logger.error(f"Erro ao processar Kits: {e}")

            # Atualizar kits para cada aluno
            for aluno_id, num_fotos in fotos_por_aluno.items():
                kits = num_fotos // 3
                if aluno_id in alunos_data:
                    alunos_data[aluno_id]['kits'] = kits
                else:
                    # Aluno tem kits mas não está nos albuns
                    alunos_data[aluno_id] = {
                        'id': aluno_id,
                        'fotos': 0,
                        'kits': kits,
                        'capas': 0,
                        'curso': ''
                    }

        # Converter para lista e ordenar por ID
        alunos_lista = sorted(alunos_data.values(), key=lambda x: x['id'])
        return alunos_lista

    def _gerar_relatorio_pdf(self):
        """Gera relatório PDF com dados detalhados dos alunos"""
        # Verificar se há pasta selecionada ou salva
        if not self.pasta_producao:
            resposta = QMessageBox.question(
                self,
                "Pasta não selecionada",
                "Nenhuma pasta da produção está selecionada.\nDeseja selecionar uma pasta agora?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if resposta == QMessageBox.StandardButton.Yes:
                folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta da Produção")
                if folder:
                    self.pasta_producao = folder
                else:
                    return
            else:
                return

        # Verificar se a pasta ainda existe
        if not os.path.exists(self.pasta_producao):
            QMessageBox.warning(
                self,
                "Pasta não encontrada",
                f"A pasta da produção não foi encontrada:\n{self.pasta_producao}\n\nPor favor, selecione a pasta novamente."
            )
            folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta da Produção")
            if folder:
                self.pasta_producao = folder
            else:
                return

        try:
            # Obter nome da produção
            nome_producao = self.widgets.get('Nome')
            if nome_producao and isinstance(nome_producao, QLineEdit):
                nome_producao = nome_producao.text() or os.path.basename(self.pasta_producao)
            else:
                nome_producao = os.path.basename(self.pasta_producao)

            # Solicitar local para salvar o PDF
            arquivo_pdf, _ = QFileDialog.getSaveFileName(
                self,
                "Salvar Relatório PDF",
                f"{nome_producao}.pdf",
                "PDF Files (*.pdf)"
            )

            if not arquivo_pdf:
                return

            # Extrair dados dos alunos
            alunos = self._extrair_dados_alunos(self.pasta_producao)

            if not alunos:
                QMessageBox.warning(
                    self,
                    "Sem dados",
                    "Não foram encontrados alunos na pasta da produção."
                )
                return

            # Obter nome da empresa do campo Cliente (se disponível)
            empresa = self.widgets.get('Cliente')
            if empresa and isinstance(empresa, (QLineEdit, AutocompleteLineEdit)):
                empresa = empresa.text() or ""
            else:
                empresa = ""

            # Criar gerador de PDF
            pdf_gen = PDFGenerator(empresa=empresa)

            # Gerar PDF
            sucesso = pdf_gen.gerar_relatorio_producao(
                arquivo_saida=arquivo_pdf,
                nome_producao=nome_producao,
                alunos=alunos,
                incluir_capas=True
            )

            if sucesso:
                # Mensagem de sucesso
                resposta = QMessageBox.question(
                    self,
                    "PDF Gerado",
                    f"Relatório gerado com sucesso!\n\n{arquivo_pdf}\n\nDeseja abrir o arquivo?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )

                if resposta == QMessageBox.StandardButton.Yes:
                    if os.name == 'nt':
                        os.startfile(arquivo_pdf)
                    else:
                        os.system(f'xdg-open "{arquivo_pdf}"')
            else:
                QMessageBox.warning(
                    self,
                    "Erro",
                    "Não foi possível gerar o relatório PDF."
                )

        except Exception as e:
            logger.error(f"Erro ao gerar PDF: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Erro ao gerar PDF",
                f"Ocorreu um erro ao gerar o relatório:\n{str(e)}"
            )

    def _on_save(self):
        """Valida e salva os dados"""
        try:
            dados = {}

            # Coletar dados de cada campo
            for key, widget in self.widgets.items():
                if isinstance(widget, AutocompleteLineEdit):
                    dados[key] = widget.text().strip()
                elif isinstance(widget, QComboBox):
                    dados[key] = widget.currentText().strip()
                elif isinstance(widget, QDateEdit):
                    # Salvar datas no formato ISO 8601 (YYYY-MM-DD) para o banco
                    dados[key] = widget.date().toString("yyyy-MM-dd")
                elif isinstance(widget, (MoneyLineEdit, QSpinBox)):
                    dados[key] = widget.value()
                elif isinstance(widget, QLineEdit):
                    value = widget.text().strip()
                    # Converter tipos numéricos
                    if 'Quant.' in key:
                        dados[key] = int(value) if value else 0
                    elif 'Valor' in key:
                        dados[key] = float(value.replace(',', '.')) if value else 0.0
                    else:
                        dados[key] = value

            # Validações básicas
            if not dados.get('Cliente'):
                QMessageBox.warning(self, "Campos Obrigatórios", "O campo Cliente é obrigatório!")
                return

            if not dados.get('Nome'):
                QMessageBox.warning(self, "Campos Obrigatórios", "O campo Nome é obrigatório!")
                return

            if not dados.get('Tipo de Produção'):
                QMessageBox.warning(self, "Campos Obrigatórios", "O campo Tipo de Serviço é obrigatório!")
                return

            # Adicionar pasta se selecionada
            if self.pasta_producao:
                dados['pasta_producao'] = self.pasta_producao

            # Chamar callback se existir
            if self.on_save_callback:
                self.on_save_callback(dados)

            self.result_data = dados
            self.accept()

        except ValueError as e:
            QMessageBox.critical(self, "Erro de Validação", f"Valor inválido em um dos campos numéricos: {e}")
        except Exception as e:
            logger.error(f"Erro ao salvar formulário: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro ao processar o formulário: {e}")

    def get_data(self) -> Optional[Dict[str, Any]]:
        """Retorna os dados do formulário após execução"""
        return self.result_data
