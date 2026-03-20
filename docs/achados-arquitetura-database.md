# Achados de Arquitetura (Foco em Database)

Data da analise: 2026-02-28  
Projeto: `myProducoes`

Atualizacao (eficiencia): 2026-03-01

## Escopo

Analise da arquitetura atual com foco em:

1. Modelagem e integridade de dados.
2. Acesso a dados (queries, filtros, ordenacao).
3. Evolucao de schema (bootstrap e migracoes).
4. Riscos operacionais (backup e consistencia).

## Achados Principais

### P0 - Integridade referencial quebravel e ja quebrada

- O SQLite esta operando com `foreign_keys` desativado por conexao.
- A remocao de producoes usa `query.delete(...)`, que nao dispara cascade ORM.
- Resultado: ja existe registro orfao em `itens_producao`.

Evidencias:

- `PRAGMA foreign_keys` no banco principal retornou `0`.
- `PRAGMA foreign_key_check` retornou 1 problema: `('itens_producao', 353, 'producoes', 0)`.
- Arquivos relevantes:
  - `src/core/models.py` (`create_engine` sem ativacao explicita de foreign keys).
  - `src/core/database.py` (`remover_producoes` com delete em lote direto).

Impacto:

- Risco alto de corrupcao logica silenciosa.
- Relatorios e totais podem divergir sem erro aparente.

---

### P1 - Falta de fluxo robusto para bootstrap/migracao de schema

- Existe funcao para criar tabelas (`create_all_tables`), mas nao ha bootstrap automatico no startup.
- Em banco novo, a aplicacao pode falhar em consultas iniciais por tabela inexistente.
- Nao ha pipeline de migracao versionada (ex.: Alembic) no repositorio.

Evidencias:

- Startup da UI instancia `DatabaseManager` e consulta dados sem garantir schema criado.
- Teste com banco novo retornou erro: `OperationalError: no such table: tipos_producao`.

Impacto:

- Onboarding fragil para novos ambientes.
- Alto risco em upgrades de versao e manutencao de longo prazo.

---

### P1 - Estrategia de indices insuficiente para consultas chave

- A tabela `producoes` esta praticamente indexada apenas por `codigo`.
- Filtros e ordenacoes frequentes usam colunas sem indice (`cliente_id`, `tipo_producao_id`, `status_*`, datas).
- Queries com `strftime(...)` para ano/mes forcam `SCAN` completo.

Evidencias:

- `EXPLAIN QUERY PLAN` mostra `SCAN` e uso de `TEMP B-TREE` para `ORDER BY`/`GROUP BY`.
- Nao foram encontrados indices uteis para:
  - `cliente_id`
  - `tipo_producao_id`
  - `status_producao_id`
  - `status_pagamento_id`
  - `data_recebimento`
  - `data_conclusao`

Impacto:

- Degradacao progressiva conforme o volume cresce.
- Latencia maior em listagem principal e dashboard financeiro.

---

### P1 - Dominio de status sem normalizacao canonica

- O sistema aceita variacoes textuais e cria novo status automaticamente.
- UI e filtros assumem valores fixos (`Em aberto`/`Pago`), mas banco ja contem variacao (`pago`).

Evidencias:

- Encontrada duplicidade semantica: `Pago` e `pago`.
- Ha pelo menos 1 producao vinculada ao status `pago`.

Impacto:

- Filtros/relatorios podem omitir dados validos.
- Inconsistencia funcional entre telas.

---

### P2 - Acoplamento alto entre camada de dados e camada de UI

- `DatabaseManager` retorna dicionarios com chaves de apresentacao (nomes de coluna da tabela UI).
- A UI remapeia novamente para formato de persistencia no salvar/editar.

Impacto:

- Mudancas de schema ou de apresentacao exigem alteracoes em multiplos pontos.
- Aumenta custo de manutencao e risco de regressao.

---

### P2 - Backup/recovery incompleto na pratica

- Existe metodo de backup no codigo, mas sem integracao clara no fluxo da aplicacao.
- Config de retencao (`MAX_BACKUPS`) existe, mas sem uso operacional visivel.

Impacto:

- Risco operacional em incidente real (corrupcao/erro humano).

## Achados de Eficiencia (Atualizacao, Filtros e Afins)

### P0 - Grafico financeiro com custo quadratico no modo de evolucao temporal

- O metodo `_plot_temporal_evolution` plota a linha e cria anotacoes dentro do loop de dados.
- Com isso, o volume de desenho cresce aproximadamente em O(n^2).

Evidencias (medicao em ambiente local, Qt offscreen):

- 12 pontos: `~1.35s`
- 36 pontos: `~3.87s`
- 60 pontos: `~8.33s`
- 120 pontos: `~25.95s`

Impacto:

- O dashboard financeiro degrada fortemente com historico maior.

---

### P1 - Renderizacao da tabela domina o tempo total da tela principal

- O custo principal nao esta no filtro logico e sim na criacao massiva de `QTableWidgetItem`.
- A tela depende de renderizacao completa para operar com base em memoria.

Evidencias (base sintetica com 15.000 producoes):

- `DatabaseManager.listar_producoes()`: `~1.61s`
- `_load_table_data` (UI): `~3.43s` a `~4.86s`
- `_apply_filters` + render com tudo (`15k`): `~2.05s`
- filtro logico apenas (`refresh_display=False`): `~2ms`
- render apenas (`15k` linhas): `~1.66s`

Impacto:

- Em volumes maiores, a UX tende a travar na atualizacao/repintura da grade.

---

### P1 - Filtros principais sao client-side e dependem de preload total

- Em `MainWindow`, o filtro percorre `self.producoes` em memoria.
- Isso so fica rapido apos carregar tudo do banco e desenhar a grade.

Evidencias (15.000 producoes):

- filtro em memoria (ja carregado): `~0.87ms` para cliente+status.
- filtro equivalente consultando DB: `~10.27ms` (19 linhas retornadas).

Impacto:

- O problema nao e o filtro em si; e a dependencia de preload + render completo.

---

### P1 - Queries de listagem/financeiro com plano subotimo por falta de indices adequados

- Sem indices para chaves/filtros/datas, `EXPLAIN QUERY PLAN` mostra `SCAN` + `TEMP B-TREE`.
- Consultas com `strftime` para ano/mes ampliam custo de varredura.

Evidencias:

- `listar` ordenado por data/id: `SCAN`.
- `financeiro` por ano e agrupado por mes: `SCAN`.

Teste de melhoria em copia do banco com indices:

- Listagem ordenada: `~9.61ms` -> `~1.92ms`
- Filtro cliente+status_pagamento: `~2.53ms` -> `~0.04ms`
- Financeiro por ano: `~3.06ms` -> `~0.87ms`
- Financeiro agrupado: `~11.09ms` -> `~4.16ms`

Trade-off medido:

- Atualizacao unitaria ficou mais lenta com mais indices:
  - sem indices extras: `~7.58ms` por update
  - com indices extras: `~9.31ms` por update

Impacto:

- Ganho forte de leitura/filtro com custo moderado de escrita.

---

### P2 - Fluxo de atualizacao com round-trips acima do necessario

- `atualizar_producao` executa multiplas consultas de dominio + sincronizacao de itens.
- Fluxo da UI ainda busca novamente a producao apos update.

Evidencias:

- Contagem medida de statements em update tipico: `~10` statements.
- Medicao agregada (200 operacoes):
  - update: `~7.96ms` medio
  - update + readback: `~10.28ms` medio
  - obter_producao isolado: `~1.11ms` medio

Impacto:

- Custos acumulados em operacoes repetitivas e lotes.

## Recomendacoes Prioritarias

1. Integridade primeiro:
   - Habilitar `foreign_keys=ON` em toda conexao SQLite.
   - Ajustar estrategia de delete para garantir cascata consistente.
   - Corrigir registros orfaos existentes com script de saneamento.
2. Migracoes:
   - Introduzir migracoes versionadas (Alembic).
   - Garantir bootstrap automatico idempotente no startup.
3. Performance:
   - Criar indices para FKs e datas usadas em filtro/ordenacao.
   - Revisar queries com `strftime` (colunas derivadas/materializadas ou estrategia alternativa).
   - Reescrever o plot temporal para O(n), movendo `plot/annotate` para fora do loop incremental.
   - Migrar filtros principais para consulta no DB (com opcao de paginacao/limit).
   - Reduzir round-trips no update (evitar readback quando nao necessario, otimizar sincronizacao de itens).
4. Governanca de dominio:
   - Canonicalizar status/tipos (normalizacao de texto, validacao central).
   - Bloquear criacao de status arbitrario por entrada livre.
5. Arquitetura de camadas:
   - Separar DTOs de dominio dos dicionarios de exibicao da UI.
   - Centralizar mapeamentos em um adaptador especifico.
6. Operacao:
   - Conectar backup ao fluxo real (manual assistido + rotina automatica com retencao).
   - Definir checklist de restauracao e teste periodico.

## Risco Atual (Resumo Executivo)

Os maiores riscos imediatos sao:

1. Integridade de dados (ja com inconsistencia detectada no banco atual).
2. Ausencia de pipeline confiavel de evolucao de schema.

Sem tratar esses pontos, o crescimento da base tende a ampliar divergencias e incidentes de manutencao.
