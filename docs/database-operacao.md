# Operação de Banco de Dados

## Objetivo
Este documento define o fluxo operacional para diagnóstico, migração e recuperação do banco SQLite da aplicação.

## Pré-requisitos
- Usar o Python do ambiente virtual: `.\venv\Scripts\python.exe`
- Estar na raiz do projeto: `C:\Users\walis\Desktop\Programas\myProducoes`
- Para instalar a aplicação em modo editável e habilitar o comando desktop:

```powershell
.\venv\Scripts\python.exe -m pip install -e .
```

## Entrada da aplicação
Os pontos de entrada suportados para iniciar o desktop são:

```powershell
.\venv\Scripts\python.exe -m src
```

ou, após `pip install -e .`:

```powershell
myproducoes-desktop
```

## Preflight
Executa diagnóstico completo sem alterar dados.

```powershell
.\venv\Scripts\python.exe .\scripts\db_maintenance.py preflight
```

Validações obrigatórias no relatório:
- `has_alembic_version`
- `integrity_check`
- `foreign_key_check_count`
- `producoes_indexes`
- `status_case_insensitive_duplicates`

## Migração
Executa bootstrap Alembic no banco atual e cria backup pré-migração.

```powershell
.\venv\Scripts\python.exe .\scripts\db_maintenance.py migrate
```

## Pós-migração (bloqueante)
Executa verificação final. O comando falha com `exit code 1` se houver inconsistência.

```powershell
.\venv\Scripts\python.exe .\scripts\db_maintenance.py postcheck
```

## Backup manual (UI)
- Abra `Configurações Gerais`
- Clique em `Criar Backup Manual do Banco`
- Confirme o caminho exibido no feedback da aplicação

## Restore de backup
O restore pode ser acionado via `DatabaseManager.restaurar_backup(...)` em ferramentas internas.

Checklist após restore:
1. Rodar `preflight`
2. Rodar `postcheck`
3. Abrir a aplicação e validar listagem principal
4. Validar resumo financeiro com filtros básicos

## Rotina mensal de teste de restore
1. Selecionar backup recente de produção
2. Restaurar em cópia isolada do banco
3. Executar `postcheck`
4. Registrar data, backup testado e resultado em log operacional
