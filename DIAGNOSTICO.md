# Diagnostico
> Problemas encontrados ordenados do mais grave para o menos grave. cada problema acompanha evidência, solução proposta, impacto e consequência.  

## 1. Ausência de idempotência e conflitos de eventos

O fluxo permite reprocessar arquivos dos últimos sete dias, mas o schema original não impedia a duplicação de evento_id. A documentação indica que o evento_id é único, mas não diz se globalmente ou por processo. Assumi unicidade global (UNIQUE em evento_id)., mas no schema não tem UNIQUE.

alteração proposta é adicionar UNIQUE ao schema, garantir idempotência, caso o arquivo seja reprocessado, eventos duplicados não são gravados.

```
 evento_id TEXT NOT NULL > evento_id TEXT NOT NULL UNIQUE 

```

## 2. valores não são padronizados. 

Os valores de pagamento e dos precatorios divergem em tipo (float, int, string, null e negativos) e podem causar erros de conversão ou imprecisão de valores, que em uma operação finaceira é inviável.

Arquivos: [pagamentos.json](dados/pagamentos.json), [hub.csv](dados/hub.csv),       [tribunal.csv](dados/tribunal.csv)

```
  {
    "evento_id": "ev-003",
    "processo": "0023456-21.2020.8.26.0053",
    "valor": 8000, # int
    ...
  },
  {
    "evento_id": "ev-002",
    "processo": "0012345-10.2019.8.26.0053",
    "valor": "2.500,50", # string
    ...
  },
  {
    "evento_id": "ev-004",
    "processo": "0023456-21.2020.8.26.0053",
    "valor": null, # null
    ...
  },

```

Prevenção proposta para esse caso seria padronizar o campo valor em numero decimal 00.00.

Para o tratamento dos dados atuais, converti todos os valores para decimal e reportei os [dados invalidos](README.md/#relatórios-gerados).

## 3. Conflito de eventos

Dois pagamentos com o mesmo id divergem em valor e em data de atualização:

```
  {
    "evento_id": "ev-001",
    "processo": "0012345-10.2019.8.26.0053",
    "valor": 15000.0,
    "data_pagamento": "2025-03-10",
    "tipo": "pagamento",
    "atualizado_em": "2025-03-10T10:00:00-03:00"
  }

    {
    "evento_id": "ev-001",
    "processo": "0012345-10.2019.8.26.0053",
    "valor": 15500.0,
    "data_pagamento": "2025-03-10",
    "tipo": "pagamento",
    "atualizado_em": "2025-03-11T09:00:00-03:00"
  }
```

resgitrei em [duvidas](#duvidas), porém Mantive a primeira versão lida (valor 15000.00) e registrei a segunda como 'evento duplicado' em inconsistencias_pagamentos.csv. O relatório não indica que o valor divergia. assumi que o pagamento nao poderia ser alterado depois de realizado.


## 4. Datas em formatos divergentes

Evidências:

- ev-002: 10/04/2025, divergente do padrão documentado.

Impacto: interpretação incorreta da data de apresentação e, consequentemente, do prazo.

Proposta: padronizar o formato de entrada.

## 5. Divergência entre as bases de precatórios

**hub x tribunal**

| arquivo |	registro |	processo	| campo	 | classificacao	| motivo |
|---------|----------|------------|--------|----------------|--------|
| hub.csv x tribunal.csv | 0023456-21.2020.8.26.0053	| 0023456-21.2020.8.26.0053|valor_face |	duvidoso | valor_face diverge (hub=31000.00, tribunal=30000.00)|
hub.csv x tribunal.csv | 0045678-43.2021.5.02.0011	| 0045678-43.2021.5.02.0011	|ente |	duvidoso |	ente diverge (hub=MunicÃ­pio de Santos, tribunal=UniÃ£o)|
hub.csv |	0056789-54.2017.4.03.6100	| 0056789-54.2017.4.03.6100 |	processo	|duvidoso |	ausente no tribunal|
tribunal.csv|	0067890-65.2016.8.26.0053	| 0067890-65.2016.8.26.0053 |	processo	| duvidoso	| ausente no hub| 

dados oriundos do relatorio [inconsistencas_bases.csv] gerado pelo código.

## 6. Incompatibilidade no identificador do processo

O número CNJ possui 20 dígitos e 25 caracteres quando formatado. O schema original utiliza CHAR(20).

Impacto: o campo não comporta o identificador formatado completo.

Proposta: utilizar VARCHAR(25) para armazenar a representação formatada e normalizar a comparação dos identificadores.


# Soluções propostas e intervenções realizadas

Com base nos problemas identificados, foram implementadas as seguintes intervenções para garantir maior consistência, rastreabilidade e segurança no processamento dos dados.

## 1. Leitura e normalização dos dados

- **`load.py`**: centraliza a leitura dos arquivos de entrada, respeitando suas particularidades de codificação, delimitadores e formatos.
- **`tratamentos.py`**: concentra a normalização e validação dos registros, incluindo valores monetários com `Decimal`, datas e identificadores de processos CNJ.
- Registros inválidos ou que não atendem aos critérios de validação são identificados e encaminhados para os relatórios de inconsistências, em vez de serem silenciosamente ignorados.

## 2. Reconciliação entre as bases

- **`comparar_bases.py`**: realiza a comparação entre Hub e Tribunal, utilizando os processos apresentados como referência.
- Registros presentes nas duas bases e com correspondência de ente devedor e valor de face são considerados aptos à persistência.
- Registros divergentes não são persistidos até que a inconsistência seja analisada.
- Registros presentes em apenas uma das bases podem ser persistidos quando possuem correspondência em `apresentacoes.json`. A ausência na outra base permanece registrada como inconsistência.

## 3. Persistência no banco de dados

- **`persistencia.py`**: centraliza as operações de gravação no PostgreSQL.
- A estrutura do banco foi ajustada para comportar o identificador CNJ formatado e impedir a duplicação de eventos por meio de restrições de unicidade.
- A persistência considera a possibilidade de reprocessamento dos arquivos, evitando a inclusão repetida de registros já existentes.
- No reprocessamento, os registros já existentes são ignorados e aparecem como 'evento duplicado' ou 'processo já cadastrado' nos relatórios. Valores já gravados não são atualizados.

## 4. Geração de relatórios

- **`relatorios.py`**: centraliza a geração dos relatórios em CSV:
  - `precatorios_atualizados.csv`: dados consolidados dos precatórios armazenados no banco, incluindo os valores de pagamentos.
  - `inconsistencias_bases.csv`: divergências de ente devedor, valor de face e processos ausentes em uma das bases.
  - `inconsistencias_pagamentos.csv`: registros de pagamento inválidos, duplicados ou que não puderam ser associados a um precatório.

## 5. Orquestração

- **`main.py`**: coordena as etapas de leitura, tratamento, reconciliação, persistência e geração dos relatórios, mantendo o fluxo centralizado e reproduzível.




# duvidas: 

1. Unicidade do evento: o evento_id é único globalmente ou apenas dentro de cada processo? Essa definição determina a estratégia de identificação e prevenção de duplicidades no banco.

2. Conflito de eventos: quando um mesmo evento_id aparece com informações diferentes, a versão mais recente, indicada por atualizado_em, deve substituir a anterior ou o caso deve ser encaminhado para análise?

3. Fonte oficial: em caso de divergência entre Hub e Tribunal, qual base deve prevalecer para campos como ente_devedor e valor_face? Até essa definição, os registros divergentes são mantidos fora da persistência.







