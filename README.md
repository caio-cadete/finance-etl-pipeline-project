# finance-etl-pipeline-project

Este projeto implementa um pipeline de ETL (Extract, Transform, Load) completo para o processamento de dados de faturamento e clientes, utilizando a **Medallion Architecture** (Arquitetura de Medalhão) para garantir a organização e qualidade dos dados.
O pipeline de dados é modular e resiliente, focado em transformar dados brutos de cobranças e clientes em insights estratégicos
para faturamento e controle de inadimplência.

### O que é a Medallion Architecture?

É um padrão de design de dados que organiza a informação em camadas lógicas (Bronze, Silver e Gold), aumentando a qualidade à medida que o dado flui pelo pipeline:

* **Bronze (Raw)**: Camada de ingestão. Os dados brutos são mantidos em `data/processed/raw` como recebidos da fonte, servindo como histórico imutável.
* **Silver (Validated)**: Fase de limpeza e padronização. Aqui os nomes são tratados, tipos de dados corrigidos e a integridade referencial entre clientes e cobranças é validada.
* **Gold (Enriched)**: Camada de negócio. Dados agregados em "Views" prontas para consumo em BI, contendo KPIs como faturamento por estado e inadimplência.

## 🚀 Como Executar

Instale as dependências:

` ` ` pip install -r requirements.txt` ` `


Execute o pipeline:

` ` ` python main.py` ` `


*Os dados processados serão gerados em `data/processed` e os alertas em `data/alerts`.*

## 🛠️ Tecnologias Utilizadas

**Python**: Processamento e transformações via biblioteca Pandas.

**SQLite**: Armazenamento e criação de lógica de negócio através de SQL Views.

**Parquet/CSV**: Exportação otimizada para consumo direto no Power BI.

## 📐 Arquitetura do Projeto

O pipeline foi desenhado com foco em **idempotência**, permitindo execuções sucessivas sem o risco de duplicidade ou corrupção de dados:

* **Estratégia de Carga (Full Load)**: O pipeline adota uma estratégia onde toda a base é reprocessada e reimportada sempre que uma nova carga chega. Isso garante que o estado final do banco de dados reflita exatamente a versão mais recente dos arquivos de origem.
* **Limpeza Automática**: Antes de iniciar uma nova ingestão, o sistema realiza o truncamento (limpeza) das tabelas temporárias e de processamento, evitando o acúmulo de registros antigos ou inconsistentes.
* **Consistência**: Essa abordagem elimina problemas comuns de atualizações parciais e garante que, independentemente de quantas vezes o script seja executado, o resultado final seja sempre o mesmo e esteja correto.

### Detalhe dos Estágios:

### *1. Extração Dinâmica (`src/extract`)
* **Resiliência**: O extrator utiliza um arquivo  `schema.yaml ` para mapear as origens, permitindo que o código seja agnóstico ao formato (Excel ou CSV).

* **Encoding**: Implementa  `utf-8-sig ` para neutralizar problemas de acentuação em exportações brasileiras.

### **2. Transformação e Data Quality ( `src/transform`)**

* **Clientes**: Padroniza nomes jurídicos via Regex, reconstrói e-mails para unicidade e sincroniza o status do cliente com base na presença de uma data de desativação.

* **Datas**: Motor que resolve números seriais do Excel e strings brasileiras (DD/MM/AAAA) via Regex, convertendo-os para o padrão ISO YYYY-MM-DD.

* **Geografia**: Corrige automaticamente cidades vinculadas a estados errados no dado bruto.

### 3. Carga e Auditoria (`src/load`)

* **Camada Silver**: Antes da carga no SQLite, o sistema remove cobranças "órfãs" (sem cliente correspondente), garantindo um faturamento 100% auditável.

* **Camada Gold**: Extrai visões complexas via SQL (Views), como análise de Churn e faturamento consolidado, entregando dados processados ao Power BI.

## 🧪 Qualidade e Testes (Auditoria)

Para garantir a confiabilidade das transformações, o projeto utiliza scripts de Auditoria Lado a Lado em `tests/`:

**Scripts**: test_pipeline_clients.py e test_pipeline_billings.py.

**Lógica**: Permite a validação humana de que o Regex de datas e a limpeza de nomes mantiveram a fidelidade à informação bruta.

**Resultado**: Relatório em `tests_output/` para comparação direta entre o dado bruto e o dado tratado.

Execução:

` ` ` python tests/test_pipeline_clients.py` ` `

` ` `python tests/test_pipeline_billings.py` ` `


## 🧠 Diferenciais Implementados

**Integridade de Dados**: Implementação de filtro para **IDs Órfãos**, descartando cobranças sem clientes vinculados para um faturamento 100% auditável.

**Regra de Inadimplência Crítica**: Lógica SQL para identificar proativamente clientes com mais de 3 meses de atraso consecutivo.

**Automação de Alertas**: Geração de arquivos específicos em `data/alerts` para simular o envio de notificações para a equipe de cobrança.

**Logs de Produção**: Interface de terminal customizada para monitoramento em tempo real.

## 📂 Organização do Repositório

`src/`: Módulos de extração, transformação e definição de schema.

`tests/`: Scripts de auditoria para validação das transformações.

`data/raw/`: Pasta para os arquivos de entrada do originais.

`data/processed`: Destino dos dados utilizados no BI (Silver).

`data/processed/analytics`: Destino dos estudos analíticos enriquecidos (Gold).

`data/alerts/`: Central de saída para os alertas de inadimplência crítica.

## Observação Técnica

Ao realizar o pré-processamento via SQL e Python antes da visualização, otimizamos a performance do Power BI e garantimos que as regras de negócio estejam centralizadas e documentadas diretamente no código.