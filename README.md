# Data Audit Pipeline

Pipeline de auditoria, tratamento e reconciliação de dados de precatórios.
O projeto processa informações provenientes de diferentes fontes, identifica inconsistências, aplica regras de validação e persiste somente os registros que atendem aos critérios definidos.

Relatório de inconsistencias e soluções em [DIAGNOSTICO.md](DIAGNOSTICO.md).

Relatórios gerados pelo codigo em [relatorios/](relatorios/)

## Objetivos

- Ler e normalizar arquivos CSV e JSON.
- Validar identificadores, datas e valores financeiros.
- Reconciliar informações do Hub e do Tribunal.
- Identificar divergências.
- Garantir idempotência na importação de pagamentos.
- Persistir registros considerados confiáveis em PostgreSQL.
- Gerar relatórios para consulta e auditoria.

## Fluxo de processamento

O processamento é dividido em etapas:

1. **Leitura:** carregamento dos arquivos originais.
2. **Tratamento:** normalização e validação dos dados, incluindo números de processo, valores monetários e datas.
3. **Reconciliação:** comparação entre Hub e Tribunal, utilizando `apresentacoes.json` como referência complementar.
4. **Persistência:** gravação dos precatórios que atendem aos critérios de confiabilidade e dos pagamentos válidos.
5. **Relatórios:** consulta aos dados persistidos e geração dos arquivos de saída.

### Critérios de reconciliação

A comparação entre Hub e Tribunal segue as seguintes regras:

| Situação | Ação |
|---|---|
| Processo presente nas duas fontes, com ente e valor iguais | Persistir |
| Processo presente nas duas fontes, com divergência | Não persistir e registrar inconsistência |
| Processo presente em apenas uma fonte, mas existente em `apresentacoes.json` | Persistir e registrar a ausência na outra fonte |
| Processo presente em apenas uma fonte e ausente em `apresentacoes.json` | Não persistir e registrar inconsistência |

As divergências não são resolvidas por sobrescrita automática. Registros que necessitam de confirmação permanecem identificados para análise.

## Relatórios gerados

Ao final do processamento, são gerados três arquivos:

| Arquivo | Conteúdo |
|---|---|
| `precatorios_atualizados.csv` | Precatórios persistidos com total_pago, total_estornado, saldo_devedor e presenca_bases (hub e tribunal, somente hub ou somente tribunal). |
| `inconsistencias_bases.csv` | Divergências entre Hub e Tribunal, como diferenças de ente devedor, valor e processos ausentes em uma das fontes. |
| `inconsistencias_pagamentos.csv` | Registros de pagamentos inválidos, duplicados ou que não puderam ser associados a um precatório. |

Os relatórios permitem consultar tanto os dados consolidados quanto os problemas encontrados durante o processamento.

## Requisitos

- Python 3.10 ou superior.
- PostgreSQL.
- Banco de dados configurado para o projeto.

## Configuração

Clone o repositório:

```bash
git clone https://github.com/luccacorbo/data-audit-pipeline
cd data-audit-pipeline
```

Crie e ative o ambiente virtual:

```bash
python -m venv venv
```

No Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Configure a variável `DATABASE_URL` em um arquivo `.env` na raiz:

```env
DATABASE_URL=postgresql://usuario:senha@localhost:5432/data_audit
```

## Execução

Execute o pipeline:

```bash
python main.py # executa todo o pipeline
python main.py --inconsistencias # gera os dois CSVs de inconsistências
python main.py --atualizados # gera precatorios_atualizados.csv
```
O pipeline completo, inclusive a gravação no banco, roda sempre. Os argumentos só escolhem quais CSVs são gerados.

## Testes

Execute os testes automatizados:

```bash
pytest
```

Os testes contemplam regras de leitura, validação, conversão, comparação entre as bases e toda a orquestração .


## Uso de inteligência artificial

A IA foi utilizada como pair programming, gerando o codigo e testes de cada camada definida antes do desenvolvimento, validando antes de seguir.

## Tecnologias

- Python 3.10+
- PostgreSQL
- Psycopg2
- Pytest