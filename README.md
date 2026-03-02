# finance-etl-pipeline-project

Este projeto de **Engenharia de Dados** implementa um pipeline de ETL (Extract, Transform, Load) completo para o processamento de dados de faturamento e clientes, utilizando a **Medallion Architecture** (Arquitetura de Medalhão) para garantir a organização e qualidade dos dados.
O pipeline de dados é modular e resiliente, focado em transformar dados brutos de cobranças e clientes em insights estratégicos
para faturamento e controle de inadimplência.

### O que é a Medallion Architecture?

É um padrão de design de dados que organiza a informação em camadas lógicas (Bronze, Silver e Gold), aumentando a qualidade à medida que o dado flui pelo pipeline:

* **Bronze (Raw)**: Camada de ingestão. Os dados brutos são mantidos em `data/raw` como recebidos da fonte, servindo como histórico imutável.
* **Silver (Validated)**: Fase de limpeza e padronização. Aqui os nomes são tratados, tipos de dados corrigidos e a integridade referencial entre clientes e cobranças é validada.
* **Gold (Enriched)**: Camada de negócio. Dados agregados em "Views" prontas para consumo em BI, contendo KPIs como faturamento por estado e inadimplência.

## 🚀 Como Executar

Siga os passos abaixo para configurar o ambiente e rodar o pipeline em sua máquina local:

**1. Clonar o repositório**

```git clone https://github.com/caio-cadete/finance-etl-pipeline-project.git```

```cd finance-etl-pipeline-project```

**2. Configurar o Ambiente Virtual (venv)**

Crie o ambiente isolado para instalar as dependências:

```python -m venv venv```

Agora, ative o ambiente de acordo com o seu sistema:

* **Windows**:

```.\venv\Scripts\activate```

* **Linux/ macOS**:

```source venv/bin/activate```

**3. Instalar Dependências**

Execute o pipeline:

```pip install -r requirements.txt```

**4. Executar o Pipeline**

```python main.py```

*Os dados processados serão gerados em `data/processed` e os alertas de inadimplência em `data/alerts`. Para validar as transformações, você também pode executar os scripts na pasta `tests/`.*

## 🛠️ Tecnologias Utilizadas

**Python**: Core do pipeline, utilizando Pandas para manipulação de DataFrames e Regex (`re`) para saneamento complexo de strings.

**SQLite**: Engine de banco de dados relacional para persistência e execução de lógica de negócio via **SQL Views** e **Triggers**.

**YAML**: Utilizado para a gestão de configurações e caminhos do projeto, garantindo um código desacoplado e fácil de manter.

**OS & Pathlib**: Gerenciamento dinâmico de diretórios e automação de sistemas de arquivos.

**Parquet/CSV**: Formatos de exportação otimizados para alta performance e consumo direto no Power BI.

## 📐 Arquitetura do Projeto

O pipeline foi desenhado com foco em **idempotência**, permitindo execuções sucessivas sem o risco de duplicidade ou corrupção de dados:

* **Estratégia de Carga (Full Load)**: Adota o padrão de reprocessamento integral. Isso garante que o estado final do banco de dados seja sempre o reflexo fiel e mais recente da origem (**Single Source of Truth**).

* **Sanitização de Ingestão**: O sistema realiza o truncate (limpeza) automático das tabelas antes de novas cargas, eliminando resíduos de processamentos anteriores.

* **Desacoplamento de Configuração**: Através do uso de arquivos YAML, os caminhos de pastas e parâmetros de banco são geridos externamente, facilitando a portabilidade do projeto entre diferentes ambientes.

### Detalhe dos Estágios:

### **1. Extração Dinâmica (`src/extract`)**
* **Resiliência**: O extrator utiliza um arquivo  `schema.yaml ` para mapear as origens, permitindo que o código seja agnóstico ao formato (Excel ou CSV).

* **Encoding**: Implementa  `utf-8-sig ` para neutralizar problemas de acentuação em exportações brasileiras.

### **2. Transformação e Data Quality (`src/transform`)**

Essa camada é o "coração" do pipeline, onde o dado **Bronze** é lapidado para o estado **Silver**.
O foco aqui é a aplicação de regras de negócio e eliminação de inconsistências técnicas.

🧩 **Clientes (`transform_clients.py`)**

* **Saneamento de Nomes**: Utiliza `Regex determinístico` para remover sufixos jurídicos (LTDA, S.A, etc.), padronizando a base para análises de grupos econômicos.

* **Reconstrução de Identidade Digital**: Gera e-mails únicos e padronizados baseados no cliente_id e no slug do nome, garantindo 100% de consistência para comunicações automatizadas.

* **Sincronização de Status (Regra de Negócio)**: Implementa uma lógica de **Data Quality** que cruza a `data_desativacao` com o `status_cliente`. Se houver data, o status é forçado para "Cancelado", corrigindo erros de preenchimento manual da origem.

* **Geografia Inteligente**: Possui um motor de correção que identifica cidades e força a UF correta (ex: "Belo Horizonte" sempre será "MG"), eliminando ruídos de localização.

📅 **Datas (`transform_date.py`)**

* **Motor Híbrido de Conversão**: Resolve um dos problemas mais comuns em ETLs financeiros: a mistura de formatos.

    * **Excel Serials**: Converte números inteiros (ex: 45259) para o padrão de data correto.

    * **Regex Brasileiro**: Captura strings no formato DD/MM/AAAA e as reestrutura para o padrão **ISO 8601** (YYYY-MM-DD), garantindo compatibilidade total com o banco de dados SQL.

💰 **Cobranças (`transform_billings.py`)**

* **Normalização Monetária**: Trata strings "sujas" vindas de diferentes sistemas (uso de vírgulas, pontos e espaços), convertendo-as em float64 com precisão de duas casas decimais.

* **Categorização por Mapeamento**: Agrupa variações de entrada (ex: "pago", "Paga", "PAGO") em categorias únicas e limpas através de dicionários de mapeamento, facilitando a criação de Dashboards.

### 3. Carga e Auditoria (`src/load`)

* **Camada Silver**: Antes da carga no SQLite, o sistema remove cobranças "órfãs" (sem cliente correspondente), garantindo um faturamento 100% auditável.

* **Camada Gold**: Extrai visões complexas via SQL (Views), como análise de Churn e faturamento consolidado, entregando dados processados ao Power BI.

## 🧪 Qualidade e Testes (Auditoria)

Para garantir a confiabilidade das transformações e a integridade dos dados, o projeto utiliza uma camada de **Auditoria Lado a Lado** localizada na pasta `tests_output/` que valida o saneamento e a padronização das informações, assegurando fidelidade total aos dados brutos após transformações.

Os relatórios de comparação entre os estados **Bronzes** (Dados Brutos) e **Silver** (Dados Tratados) são gerados em `tests_output/`, permitindo uma **validação humana** detalhada da limpeza de nomes, valores monetários e padronização de datas através dos comandos:

* **Auditoria do Pipeline de Clientes**

``` python tests/test_pipeline_clients.py```

* **Auditoria do Pipeline de Cobranças**

```python tests/test_pipeline_billings.py```

**Nota:** *Para os testes funcionarem, é necessário que os arquivos brutos estejam presentes na pasta  `data/raw/ `.*

## 🧠 Diferenciais Implementados

### **1. Governança e Integridade Referencial**

* **PRAGMA Foreign Keys**: O pipeline garante a integridade dos dados ativando chaves estrangeiras, impedindo a existência de **IDs Órfãos** (cobranças sem clientes).

* **Cascade Updates/Deletes**: Configuração de `ON DELETE CASCADE` , garantindo que a limpeza na tabela de clientes reflita automaticamente nas cobranças, mantendo o banco sempre higienizado.

* **Check Constraints**: Implementação de travas de segurança a nível de banco (`CHECK`) para impedir inconsistências lógicas, como um cliente "Ativo" possuir uma "Data de Desativação".

### **2. Automação via Triggers (Business Intelligence Real-time)**

* **Sincronização Automática de Status**: O banco de dados possui inteligência própria. Através de **Triggers**, o status do cliente é recalculado automaticamente em qualquer `INSERT` ou `UPDATE` da data de desativação, eliminando a dependência de processamento externo.

### **3. Camada Analítica e Semântica (Views)**

* **Abstração de Complexidade**: Criação de Views Analíticas que transformam tabelas normalizadas em um "Planilhão Base" (como a `vw_faturamento_consolidado`), facilitando o consumo por ferramentas de BI como Power BI ou Tableau.

* **KPIs Geográficos e Churn**: Motores de agregação nativos que calculam Ticket Médio por estado e faturamento por Grupo Econômico diretamente no SQL.

* **Cálculo Dinâmico de Atraso**: Uso de funções julianday para calcular o envelhecimento da dívida (Aging) em tempo real.

### **4. Regras de Inadimplência Crítica (Advanced SQL)**

* **Análise de Janela (Window Functions)**: Utilização de `ROW_NUMBER()` e `PARTITION BY` para analisar o histórico de pagamentos e identificar proativamente clientes de alto risco (com as últimas 3 cobranças consecutivas em aberto).

### **5. Monitoramento e Alertas**

* **Logs de Produção**: Interface de terminal customizada para monitoramento do processo de ETL em tempo real.

* **Automação de Alertas**: Geração de arquivos específicos em `data/alerts` para disparar ações imediatas da equipe de cobrança.

## 📂 Estrutura do Projeto

O projeto segue uma organização modular, separando a lógica de negócio da persistência de dados e dos processos de auditoria:

* `src/`: Núcleo do pipeline. Contém os módulos de extração (E), transformação (T) e a definição das regras de negócio.

* `src/database/`: Camada de persistência. Contém o schema.py com a modelagem das tabelas, **Triggers de automação** e as **Views analíticas**.

* `tests/`: Motores de auditoria. Scripts dedicados à validação "Lado a Lado" para garantir a integridade das transformações.

* `data/raw/`: Camada **Bronze**. Repositório dos arquivos originais (imutáveis) recebidos das fontes externas.

* `data/processed/`: Camada **Silver**. Dados saneados e padronizados, prontos para consumo e carga no banco de dados.

* `data/processed/analytics/`: Camada **Gold**. Tabelas enriquecidas e agregadas para estudos avançados e consumo direto por ferramentas de BI.

* `data/alerts/`: Output de Negócio. Central de saída para relatórios de inadimplência crítica, gerados automaticamente pelo pipeline.

### Mapa Visual do Diretório:

```
finance_etl_pipeline_project/
├── config/
│   └── schema.yaml          # Configurações de colunas e seletores
├── data/
│   ├── raw/                 # Camada Bronze: Arquivos originais imutáveis
│   ├── database/            # Banco de Dados SQLite (etl_local.db)
│   ├── processed/           # Camada Silver: Bases limpas para o BI
│   │   └── analytics/       # Camada Gold: Estudos analíticos enriquecidos
│   └── alerts/              # Central de Alertas de Inadimplência
├── src/
│   ├── extract/
│   │   └── loaders.py       # Extração resiliente e leitura de YAML
│   ├── transform/
│   │   ├── transform_clients.py   # Regras de limpeza de clientes
│   │   ├── transform_billings.py  # Normalização de cobranças
│   │   └── transform_date.py      # Motor de conversão de datas
│   └── load/
│       └── exporter.py      # Carga Silver/Gold e exportação
├── tests/
│   ├── test_pipeline_clients.py   # Auditoria lado a lado de clientes
│   └── tests_pipeline_billings.py # Auditoria lado a lado de cobranças
├── tests_output/            # Relatórios para validação humana (RAIZ)
├── main.py                  # Orquestrador central do Pipeline
├── requirements.txt         # Dependências do projeto
└── .gitignore               # Filtro de arquivos locais e temporários
```

## ⚙️ Observações Técnicas e Evolução

Ao realizar o pré-processamento via SQL e Python antes da visualização, otimizamos a performance do Power BI e garantimos que as regras de negócio estejam centralizadas e documentadas diretamente no código.

Esta arquitetura evita a sobrecarga de processamento na camada de visualização, assegurando que o cálculo de KPIs seja uniforme e consistente para qualquer ferramenta que consuma esses dados.

### Oportunidades de Refatoração e Escalabilidade

Para cenários de maior volume de dados ou ambientes corporativos de alta complexidade, o projeto permite as seguintes evoluções:

* **Migração de Engine (DuckDB/PostgreSQL)**: Substituição do SQLite por **DuckDB** (para processamento analítico em memória com milhões de registros) ou **PostgreSQL** (para suporte a múltiplas conexões simultâneas).

* **Orquestração de Workflows**: Implementação de ferramentas como **Airflow** ou **Prefect** para gerenciar dependências entre tarefas, retentativas automáticas e monitoramento de falhas críticas.

* **Camada de Testes Unitários**: Inclusão de **Pytest** nas funções de transformação para garantir que novas alterações no código não causem regressões nas regras de negócio.

* **Contenerização (Docker)**: Empacotamento do pipeline em containers para eliminar riscos de conflitos de versão de bibliotecas entre os ambientes de desenvolvimento e produção.
