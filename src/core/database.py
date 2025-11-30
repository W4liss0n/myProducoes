# -*- coding: utf-8 -*-
"""
Gerenciador de Banco de Dados SQLite para o Sistema de Produções
Substitui o uso de pandas/Excel por um banco de dados relacional
Otimizado com WAL mode e operações paralelas
"""
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import json
import threading

from ..config.constants import (
    DATABASE_FILE, DATA_DIR, ALL_COLUMNS,
    NUMERIC_COLUMNS, DATE_COLUMNS
)

logger = logging.getLogger(__name__)


# Mapeamento de tipos de produção para prefixos de código
TIPO_PREFIXOS = {
    'Formatura': 'FORM',
    'Separação': 'SEP',
    'Completo': 'COMP',
    'Edição': 'EDIT',
    'Poster': 'POST',
    'Foto Tela': 'FTELA',
    'Newborn': 'NEWB',
    'Casamento': 'CASA',
}


class DatabaseManager:
    """Gerencia todas as operações com o banco de dados SQLite com suporte a operações paralelas"""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Inicializa o gerenciador de banco de dados

        Args:
            db_path: Caminho para o arquivo do banco. Se None, usa o padrão.
        """
        self.db_path = db_path or DATABASE_FILE
        self._local = threading.local()  # Pool de conexões thread-local para leituras paralelas
        self._write_lock = threading.Lock()  # Lock para escritas (WAL permite leituras paralelas)
        self._ensure_data_dir()
        self._initialize_database()
        logger.info(f"DatabaseManager initialized with database at: {self.db_path}")
        logger.info("WAL mode enabled: suporte a leitura/escrita paralela ativado")

    def _ensure_data_dir(self):
        """Garante que o diretório de dados existe"""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Erro ao criar diretório de dados: {e}")
            raise

    def _create_connection(self) -> sqlite3.Connection:
        """
        Cria uma nova conexão com o banco de dados otimizada para performance

        Returns:
            Conexão SQLite configurada com otimizações WAL
        """
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,
            check_same_thread=False  # Permite uso em múltiplas threads
        )
        conn.row_factory = sqlite3.Row  # Permite acessar colunas por nome

        # OTIMIZAÇÕES WAL E PERFORMANCE
        conn.execute("PRAGMA journal_mode=WAL")  # Modo WAL para leitura/escrita paralela
        conn.execute("PRAGMA synchronous=NORMAL")  # Balanço entre segurança e velocidade
        conn.execute("PRAGMA cache_size=-64000")  # Cache de 64MB (negativo = KB)
        conn.execute("PRAGMA temp_store=MEMORY")  # Tabelas temporárias em memória
        conn.execute("PRAGMA mmap_size=268435456")  # Memory-mapped I/O de 256MB
        conn.execute("PRAGMA page_size=4096")  # Tamanho de página otimizado
        conn.execute("PRAGMA busy_timeout=5000")  # Timeout de 5s em caso de lock

        # Otimizações WAL específicas
        conn.execute("PRAGMA wal_autocheckpoint=1000")  # Checkpoint a cada 1000 páginas

        return conn

    def _get_connection(self) -> sqlite3.Connection:
        """
        Retorna uma conexão thread-local para operações de leitura paralelas
        WAL mode permite múltiplas leituras simultâneas sem bloqueio

        Returns:
            Conexão SQLite thread-local
        """
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = self._create_connection()
        return self._local.conn

    def _get_write_connection(self) -> sqlite3.Connection:
        """
        Retorna uma nova conexão para operações de escrita
        Escritas usam lock para evitar conflitos

        Returns:
            Conexão SQLite para escrita
        """
        return self._create_connection()

    def _initialize_database(self):
        """Cria as tabelas do banco de dados se não existirem"""
        try:
            # Criar conexão exclusiva para inicialização
            conn = self._create_connection()
            cursor = conn.cursor()

            # Tabela principal de produções
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS producoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT UNIQUE,
                    cliente TEXT NOT NULL,
                    data_recebimento TEXT NOT NULL,
                    nome TEXT NOT NULL,
                    tipo_producao TEXT NOT NULL,
                    quantidade_alunos INTEGER DEFAULT 0,
                    quantidade_fotos INTEGER DEFAULT 0,
                    quantidade_kits INTEGER DEFAULT 0,
                    quantidade_capas INTEGER DEFAULT 0,
                    valor_por_foto REAL DEFAULT 0.0,
                    valor_por_kit REAL DEFAULT 0.0,
                    valor_por_capa REAL DEFAULT 0.0,
                    valor_total REAL DEFAULT 0.0,
                    data_conclusao TEXT,
                    status_pagamento TEXT DEFAULT 'Em aberto',
                    status TEXT DEFAULT 'Parado',
                    relatorio TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela de tipos de produção
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tipos_producao (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela de configurações
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS configuracoes (
                    chave TEXT PRIMARY KEY,
                    valor TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Índices para melhor performance de consultas
            # Índices simples
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cliente
                ON producoes(cliente)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_status
                ON producoes(status)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_data_recebimento
                ON producoes(data_recebimento DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_data_conclusao
                ON producoes(data_conclusao DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_status_pagamento
                ON producoes(status_pagamento)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tipo_producao
                ON producoes(tipo_producao)
            """)

            # Índices compostos para consultas filtradas comuns
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cliente_data
                ON producoes(cliente, data_recebimento DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_status_tipo
                ON producoes(status, tipo_producao)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pagamento_status
                ON producoes(status_pagamento, status)
            """)

            # Verificar se a coluna codigo existe, se não, adicionar
            cursor.execute("PRAGMA table_info(producoes)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'codigo' not in columns:
                logger.info("Adicionando coluna 'codigo' à tabela producoes")
                cursor.execute("ALTER TABLE producoes ADD COLUMN codigo TEXT")

            # Verificar se a coluna pasta_producao existe, se não, adicionar
            cursor.execute("PRAGMA table_info(producoes)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'pasta_producao' not in columns:
                logger.info("Adicionando coluna 'pasta_producao' à tabela producoes")
                cursor.execute("ALTER TABLE producoes ADD COLUMN pasta_producao TEXT")

            # Criar índice para codigo (só se a coluna existir)
            if 'codigo' in columns or True:  # True porque acabamos de adicionar
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_codigo
                    ON producoes(codigo)
                """)

            # Atualizar estatísticas do otimizador de consultas
            cursor.execute("ANALYZE")

            # Verificar se WAL está ativado
            cursor.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()[0]
            logger.info(f"Journal mode: {journal_mode}")

            # Verificar tamanho do cache
            cursor.execute("PRAGMA cache_size")
            cache_size = cursor.fetchone()[0]
            logger.info(f"Cache size: {abs(cache_size)}KB" if cache_size < 0 else f"Cache size: {cache_size} pages")

            conn.commit()
            conn.close()
            logger.info("Database tables initialized successfully")
            logger.info("Database indexes optimized with ANALYZE")

        except Exception as e:
            logger.error(f"Erro ao inicializar banco de dados: {e}")
            raise

    # ================================
    # Operações CRUD de Produções
    # ================================

    def adicionar_producao(self, dados: Dict[str, Any]) -> int:
        """
        Adiciona uma nova produção ao banco de dados

        Args:
            dados: Dicionário com os dados da produção

        Returns:
            ID da produção criada
        """
        try:
            # Calcula o valor total
            valor_total = self._calcular_valor_total(dados)
            dados['valor_total'] = valor_total

            # Gera código único se não fornecido
            if 'codigo' not in dados or not dados['codigo']:
                dados['codigo'] = self._gerar_codigo(
                    dados.get('tipo_producao', ''),
                    dados.get('data_recebimento', '')
                )

            # Usar conexão dedicada para escrita com lock
            with self._write_lock:
                conn = self._get_write_connection()
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO producoes (
                        codigo, cliente, data_recebimento, nome, tipo_producao,
                        quantidade_alunos, quantidade_fotos, quantidade_kits, quantidade_capas,
                        valor_por_foto, valor_por_kit, valor_por_capa, valor_total,
                        data_conclusao, status_pagamento, status, relatorio, pasta_producao
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    dados['codigo'],
                    dados.get('cliente', ''),
                    dados.get('data_recebimento', ''),
                    dados.get('nome', ''),
                    dados.get('tipo_producao', ''),
                    dados.get('quantidade_alunos', 0),
                    dados.get('quantidade_fotos', 0),
                    dados.get('quantidade_kits', 0),
                    dados.get('quantidade_capas', 0),
                    dados.get('valor_por_foto', 0.0),
                    dados.get('valor_por_kit', 0.0),
                    dados.get('valor_por_capa', 0.0),
                    valor_total,
                    dados.get('data_conclusao'),
                    dados.get('status_pagamento', 'Em aberto'),
                    dados.get('status', 'Parado'),
                    dados.get('relatorio'),
                    dados.get('pasta_producao')
                ))

                producao_id = cursor.lastrowid
                conn.commit()
                conn.close()

            logger.info(f"Produção adicionada com código {dados['codigo']} (ID: {producao_id})")
            return producao_id

        except Exception as e:
            logger.error(f"Erro ao adicionar produção: {e}")
            raise

    def atualizar_producao(self, producao_id: int, dados: Dict[str, Any]) -> bool:
        """
        Atualiza uma produção existente

        Args:
            producao_id: ID da produção a ser atualizada
            dados: Dicionário com os novos dados

        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        try:
            # Calcula o valor total
            valor_total = self._calcular_valor_total(dados)
            dados['valor_total'] = valor_total

            # Usar conexão dedicada para escrita com lock
            with self._write_lock:
                conn = self._get_write_connection()
                cursor = conn.cursor()

                cursor.execute("""
                    UPDATE producoes SET
                        cliente = ?,
                        data_recebimento = ?,
                        nome = ?,
                        tipo_producao = ?,
                        quantidade_alunos = ?,
                        quantidade_fotos = ?,
                        quantidade_kits = ?,
                        quantidade_capas = ?,
                        valor_por_foto = ?,
                        valor_por_kit = ?,
                        valor_por_capa = ?,
                        valor_total = ?,
                        data_conclusao = ?,
                        status_pagamento = ?,
                        status = ?,
                        relatorio = ?,
                        pasta_producao = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    dados.get('cliente', ''),
                    dados.get('data_recebimento', ''),
                    dados.get('nome', ''),
                    dados.get('tipo_producao', ''),
                    dados.get('quantidade_alunos', 0),
                    dados.get('quantidade_fotos', 0),
                    dados.get('quantidade_kits', 0),
                    dados.get('quantidade_capas', 0),
                    dados.get('valor_por_foto', 0.0),
                    dados.get('valor_por_kit', 0.0),
                    dados.get('valor_por_capa', 0.0),
                    valor_total,
                    dados.get('data_conclusao'),
                    dados.get('status_pagamento', 'Em aberto'),
                    dados.get('status', 'Parado'),
                    dados.get('relatorio'),
                    dados.get('pasta_producao'),
                    producao_id
                ))

                conn.commit()
                success = cursor.rowcount > 0
                conn.close()

            if success:
                logger.info(f"Produção {producao_id} atualizada com sucesso")
            else:
                logger.warning(f"Nenhuma produção encontrada com ID {producao_id}")

            return success

        except Exception as e:
            logger.error(f"Erro ao atualizar produção {producao_id}: {e}")
            raise

    def remover_producoes(self, ids: List[int]) -> int:
        """
        Remove uma ou mais produções

        Args:
            ids: Lista de IDs das produções a serem removidas

        Returns:
            Número de produções removidas
        """
        try:
            # Usar conexão dedicada para escrita com lock
            with self._write_lock:
                conn = self._get_write_connection()
                cursor = conn.cursor()

                placeholders = ','.join('?' * len(ids))
                cursor.execute(f"DELETE FROM producoes WHERE id IN ({placeholders})", ids)

                removed_count = cursor.rowcount
                conn.commit()
                conn.close()

            logger.info(f"{removed_count} produções removidas")
            return removed_count

        except Exception as e:
            logger.error(f"Erro ao remover produções: {e}")
            raise

    def obter_producao(self, producao_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtém uma produção específica por ID

        Args:
            producao_id: ID da produção

        Returns:
            Dicionário com os dados da produção ou None se não encontrada
        """
        try:
            conn = self._get_connection()  # Conexão do pool - NÃO fechar
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM producoes WHERE id = ?", (producao_id,))
            row = cursor.fetchone()
            # NÃO fechar conexão do pool thread-local

            if row:
                return self._row_to_dict(row)
            return None

        except Exception as e:
            logger.error(f"Erro ao obter produção {producao_id}: {e}")
            raise

    def listar_producoes(self, filtros: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Lista todas as produções, opcionalmente com filtros

        Args:
            filtros: Dicionário com filtros a serem aplicados

        Returns:
            Lista de dicionários com os dados das produções
        """
        try:
            conn = self._get_connection()  # Conexão do pool - NÃO fechar
            cursor = conn.cursor()

            query = "SELECT * FROM producoes"
            params = []

            if filtros:
                conditions = []
                for key, value in filtros.items():
                    if value is not None:
                        conditions.append(f"{key} = ?")
                        params.append(value)

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY data_recebimento DESC"

            logger.debug(f"Query SQL: {query}")
            logger.debug(f"Parâmetros: {params}")
            cursor.execute(query, params)
            rows = cursor.fetchall()
            logger.debug(f"Linhas retornadas: {len(rows)}")
            # NÃO fechar conexão do pool thread-local

            return [self._row_to_dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao listar produções: {e}")
            raise

    # ================================
    # Operações de Tipos de Produção
    # ================================

    def adicionar_tipo_producao(self, nome: str) -> bool:
        """Adiciona um novo tipo de produção"""
        try:
            # Usar conexão dedicada para escrita com lock
            with self._write_lock:
                conn = self._get_write_connection()
                cursor = conn.cursor()

                cursor.execute("INSERT INTO tipos_producao (nome) VALUES (?)", (nome,))
                conn.commit()
                conn.close()

            logger.info(f"Tipo de produção '{nome}' adicionado")
            return True

        except sqlite3.IntegrityError:
            logger.warning(f"Tipo de produção '{nome}' já existe")
            return False
        except Exception as e:
            logger.error(f"Erro ao adicionar tipo de produção: {e}")
            return False

    def remover_tipo_producao(self, nome: str) -> bool:
        """Remove um tipo de produção"""
        try:
            # Usar conexão dedicada para escrita com lock
            with self._write_lock:
                conn = self._get_write_connection()
                cursor = conn.cursor()

                cursor.execute("DELETE FROM tipos_producao WHERE nome = ?", (nome,))
                success = cursor.rowcount > 0
                conn.commit()
                conn.close()

            if success:
                logger.info(f"Tipo de produção '{nome}' removido")
            return success

        except Exception as e:
            logger.error(f"Erro ao remover tipo de produção: {e}")
            raise

    def listar_tipos_producao(self) -> List[str]:
        """Lista todos os tipos de produção"""
        try:
            conn = self._get_connection()  # Conexão do pool - NÃO fechar
            cursor = conn.cursor()

            cursor.execute("SELECT nome FROM tipos_producao ORDER BY nome")
            rows = cursor.fetchall()
            # NÃO fechar conexão do pool thread-local

            return [row['nome'] for row in rows]

        except Exception as e:
            logger.error(f"Erro ao listar tipos de produção: {e}")
            raise

    # ================================
    # Métodos Auxiliares
    # ================================

    def _gerar_codigo(self, tipo_producao: str, data_recebimento: str) -> str:
        """
        Gera um código único para a produção no formato TIPO-ANO-SEQ

        Args:
            tipo_producao: Tipo da produção
            data_recebimento: Data de recebimento (formato: YYYY-MM-DD)

        Returns:
            Código único (ex: FORM-2025-001)
        """
        try:
            # Obter prefixo do tipo
            prefixo = TIPO_PREFIXOS.get(tipo_producao, 'PROD')

            # Extrair ano da data de recebimento
            try:
                if isinstance(data_recebimento, str):
                    ano = data_recebimento.split('-')[0]
                else:
                    ano = str(datetime.now().year)
            except:
                ano = str(datetime.now().year)

            # Buscar última sequência para este tipo e ano
            conn = self._get_connection()  # Conexão do pool - NÃO fechar
            cursor = conn.cursor()

            cursor.execute("""
                SELECT codigo FROM producoes
                WHERE codigo LIKE ?
                ORDER BY codigo DESC
                LIMIT 1
            """, (f"{prefixo}-{ano}-%",))

            resultado = cursor.fetchone()
            # NÃO fechar conexão do pool thread-local

            if resultado and resultado['codigo']:
                # Extrair sequência do último código
                ultimo_codigo = resultado['codigo']
                try:
                    ultima_seq = int(ultimo_codigo.split('-')[-1])
                    nova_seq = ultima_seq + 1
                except:
                    nova_seq = 1
            else:
                nova_seq = 1

            # Gerar código
            codigo = f"{prefixo}-{ano}-{nova_seq:03d}"
            return codigo

        except Exception as e:
            logger.error(f"Erro ao gerar código: {e}")
            # Código de fallback
            return f"PROD-{datetime.now().year}-{datetime.now().microsecond:06d}"

    def _calcular_valor_total(self, dados: Dict[str, Any]) -> float:
        """Calcula o valor total baseado nas quantidades e valores unitários"""
        total = 0.0

        total += dados.get('quantidade_fotos', 0) * dados.get('valor_por_foto', 0.0)
        total += dados.get('quantidade_kits', 0) * dados.get('valor_por_kit', 0.0)
        total += dados.get('quantidade_capas', 0) * dados.get('valor_por_capa', 0.0)

        return round(total, 2)

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Converte uma linha do banco em dicionário"""
        # sqlite3.Row tem acesso por nome de coluna, mas não tem método get()
        try:
            codigo = row['codigo'] if row['codigo'] else ''
        except (KeyError, IndexError):
            codigo = ''

        try:
            pasta_producao = row['pasta_producao'] if row['pasta_producao'] else ''
        except (KeyError, IndexError):
            pasta_producao = ''

        return {
            'ID': row['id'],  # Mantém ID para uso interno
            'Código': codigo,  # Código amigável para exibição
            'Cliente': row['cliente'],
            'Data de Recebimento': row['data_recebimento'],
            'Nome': row['nome'],
            'Tipo de Produção': row['tipo_producao'],
            'Quant. Alunos': row['quantidade_alunos'],
            'Quant. Fotos': row['quantidade_fotos'],
            'Quant. Kits': row['quantidade_kits'],
            'Quant. Capas': row['quantidade_capas'],
            'Valor por Foto': row['valor_por_foto'],
            'Valor por Kit': row['valor_por_kit'],
            'Valor por Capa': row['valor_por_capa'],
            'Valor Total': row['valor_total'],
            'Data de Conclusão': row['data_conclusao'],
            'Status Pagamento': row['status_pagamento'],
            'Status': row['status'],
            'Relatório': row['relatorio'],
            'Pasta Produção': pasta_producao
        }

    # ================================
    # Estatísticas e Relatórios
    # ================================

    def obter_clientes_unicos(self) -> List[str]:
        """Retorna lista de clientes únicos"""
        try:
            conn = self._get_connection()  # Conexão do pool - NÃO fechar
            cursor = conn.cursor()

            cursor.execute("SELECT DISTINCT cliente FROM producoes ORDER BY cliente")
            rows = cursor.fetchall()
            # NÃO fechar conexão do pool thread-local

            return [row['cliente'] for row in rows if row['cliente']]

        except Exception as e:
            logger.error(f"Erro ao obter clientes únicos: {e}")
            raise

    def obter_resumo_financeiro(self, ano: Optional[int] = None, cliente: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtém resumo financeiro das produções

        Args:
            ano: Filtrar por ano específico
            cliente: Filtrar por cliente específico

        Returns:
            Dicionário com estatísticas financeiras
        """
        try:
            conn = self._get_connection()  # Conexão do pool - NÃO fechar
            cursor = conn.cursor()

            query = "SELECT SUM(valor_total) as total, COUNT(*) as quantidade FROM producoes WHERE 1=1"
            params = []

            if ano:
                query += " AND strftime('%Y', data_recebimento) = ?"
                params.append(str(ano))

            if cliente:
                query += " AND cliente = ?"
                params.append(cliente)

            cursor.execute(query, params)
            row = cursor.fetchone()
            # NÃO fechar conexão do pool thread-local

            return {
                'total': row['total'] or 0.0,
                'quantidade': row['quantidade'] or 0
            }

        except Exception as e:
            logger.error(f"Erro ao obter resumo financeiro: {e}")
            raise

    def obter_dados_financeiros_por_periodo(self, filtros: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Obtém dados financeiros agregados por período (mês/ano) para gráficos

        Args:
            filtros: Dicionário com filtros opcionais:
                - cliente: Nome do cliente
                - ano: Ano específico (int)
                - mes: Mês específico (int 1-12)
                - tipo_producao: Tipo de produção
                - status_pagamento: Status de pagamento (Em aberto/Pago)

        Returns:
            Lista de dicionários com dados agregados por mês:
            [
                {
                    'ano': 2025,
                    'mes': 1,
                    'data': '2025-01-01',  # Primeiro dia do mês para ordenação
                    'valor_total': 15000.0,
                    'quantidade': 5
                },
                ...
            ]
        """
        try:
            conn = self._get_connection()  # Conexão do pool - NÃO fechar
            cursor = conn.cursor()

            # Query base: agregar por ano e mês
            query = """
                SELECT
                    strftime('%Y', data_recebimento) as ano,
                    strftime('%m', data_recebimento) as mes,
                    strftime('%Y-%m-01', data_recebimento) as data,
                    SUM(valor_total) as valor_total,
                    COUNT(*) as quantidade
                FROM producoes
                WHERE data_recebimento IS NOT NULL
            """
            params = []

            # Aplicar filtros
            if filtros:
                if filtros.get('cliente'):
                    query += " AND cliente = ?"
                    params.append(filtros['cliente'])

                if filtros.get('ano'):
                    query += " AND strftime('%Y', data_recebimento) = ?"
                    params.append(str(filtros['ano']))

                if filtros.get('mes'):
                    query += " AND strftime('%m', data_recebimento) = ?"
                    params.append(f"{filtros['mes']:02d}")

                if filtros.get('tipo_producao'):
                    query += " AND tipo_producao = ?"
                    params.append(filtros['tipo_producao'])

                if filtros.get('status_pagamento'):
                    query += " AND status_pagamento = ?"
                    params.append(filtros['status_pagamento'])

            # Agrupar por ano e mês, ordenar cronologicamente
            query += """
                GROUP BY strftime('%Y', data_recebimento), strftime('%m', data_recebimento)
                ORDER BY ano, mes
            """

            logger.debug(f"Query financeira: {query}")
            logger.debug(f"Parâmetros: {params}")

            cursor.execute(query, params)
            rows = cursor.fetchall()
            # NÃO fechar conexão do pool thread-local

            resultados = []
            for row in rows:
                # Validar que temos dados válidos
                if row['ano'] is None or row['mes'] is None:
                    logger.warning(f"Linha com dados incompletos ignorada: {dict(row)}")
                    continue

                try:
                    resultados.append({
                        'ano': int(row['ano']),
                        'mes': int(row['mes']),
                        'data': row['data'],  # Formato YYYY-MM-01 para facilitar conversão
                        'valor_total': float(row['valor_total'] or 0.0),
                        'quantidade': int(row['quantidade'] or 0)
                    })
                except (ValueError, TypeError) as e:
                    logger.warning(f"Erro ao processar linha: {dict(row)} - {e}")
                    continue

            logger.info(f"Dados financeiros obtidos: {len(resultados)} períodos")
            return resultados

        except Exception as e:
            logger.error(f"Erro ao obter dados financeiros por período: {e}")
            raise

    def obter_anos_disponiveis(self) -> List[int]:
        """
        Retorna lista de anos disponíveis nas produções (para filtros)

        Returns:
            Lista de anos ordenados (mais recente primeiro)
        """
        try:
            conn = self._get_connection()  # Conexão do pool - NÃO fechar
            cursor = conn.cursor()

            cursor.execute("""
                SELECT DISTINCT strftime('%Y', data_recebimento) as ano
                FROM producoes
                WHERE data_recebimento IS NOT NULL AND data_recebimento != ''
                ORDER BY ano DESC
            """)
            rows = cursor.fetchall()
            # NÃO fechar conexão do pool thread-local

            # Filtrar apenas anos válidos
            anos = []
            for row in rows:
                if row['ano'] is not None and row['ano'] != '':
                    try:
                        anos.append(int(row['ano']))
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Ano inválido ignorado: {row['ano']} - {e}")
                        continue

            return anos

        except Exception as e:
            logger.error(f"Erro ao obter anos disponíveis: {e}")
            raise

    def backup_database(self, backup_path: Path) -> bool:
        """
        Cria um backup do banco de dados

        Args:
            backup_path: Caminho para salvar o backup

        Returns:
            True se backup criado com sucesso
        """
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Backup do banco criado: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Erro ao criar backup do banco: {e}")
            return False
