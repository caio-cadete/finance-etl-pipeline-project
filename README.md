# finance-etl-pipeline-project

Este projeto implementa um pipeline de ETL (Extract, Transform, Load) completo para o processamento de dados de faturamento e clientes, utilizando a **Medallion Architecture** (Arquitetura de Medalhão) para garantir a organização e qualidade dos dados.

### O que é a Medallion Architecture?
É um padrão de design de dados que organiza a informação em camadas lógicas (Bronze, Silver e Gold), aumentando a qualidade à medida que o dado flui pelo pipeline:

* **Bronze (Raw)**: Camada de ingestão. Os dados brutos são mantidos em `data/processed/raw` como recebidos da fonte, servindo como histórico imutável.
* **Silver (Validated)**: Fase de limpeza e padronização. Aqui os nomes são tratados, tipos de dados corrigidos e a integridade referencial entre clientes e cobranças é validada.
* **Gold (Enriched)**: Camada de negócio. Dados agregados em "Views" prontas para consumo em BI, contendo KPIs como faturamento por estado e inadimplência.

## 🚀 Como Executar

Instale as dependências:
` ` ` bash
pip install -r requirements.txt
` ` `

Execute o pipeline:
` ` ` bash
python main.py
` ` `
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

## 🧪 Qualidade e Testes (Auditoria)

Para garantir a confiabilidade das transformações, o projeto utiliza scripts de Auditoria Lado a Lado em `tests/`:

**Scripts**: test_pipeline_clients.py e test_pipeline_billings.py.

**Lógica**: O teste cria um backup de cada coluna original (ex: valor_original) antes da limpeza.

**Resultado**: Relatório em `tests_output/` para comparação direta entre o dado bruto e o dado tratado.

Execução:

` ` ` bash
python tests/test_pipeline_clients.py
python tests/test_pipeline_billings.py
` ` `

## 🧠 Diferenciais Implementados

**Integridade de Dados**: Implementação de filtro para **IDs Órfãos**, descartando cobranças sem clientes vinculados para um faturamento 100% auditável.

**Regra de Inadimplência Crítica**: Lógica SQL para identificar proativamente clientes com mais de 3 meses de atraso consecutivo.

**Automação de Alertas**: Geração de arquivos específicos em `data/alerts` para simular o envio de notificações para a equipe de cobrança.

**Logs de Produção**: Interface de terminal customizada para monitoramento em tempo real.

## 📂 Organização do Repositório

`src/`: Módulos de extração, transformação e definição de schema.

`tests/`: Scripts de auditoria para validação das transformações.

`data/raw/`: Pasta para os arquivos de entrada do originais.

`data/processed/analytics`: Destino dos dados tratados (Silver/Gold).

`data/alerts/`: Central de saída para os alertas de inadimplência crítica.

## Observação Técnica

Ao realizar o pré-processamento via SQL e Python antes da visualização, otimizamos a performance do Power BI e garantimos que as regras de negócio estejam centralizadas e documentadas diretamente no código.