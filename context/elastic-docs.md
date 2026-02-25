# Elastic Documentation Reference

Base URL: https://www.elastic.co/docs

Use these links and structure when recommending documentation to developers or when you need to reference official guidance.

## Search Use Cases (https://www.elastic.co/docs/solutions/search)

### Getting Started
- Index and search basics quickstart
- Keyword search with Python quickstart
- Semantic search quickstart

### Search Approaches
- **Full-text search**: How it works, text analysis, relevance optimizations, synonyms
- **AI-powered search**: Vector search (dense vector, kNN, sparse vector), semantic search (semantic_text, inference API, ELSER, Cohere, OpenAI)
- **Hybrid search**: Hybrid search with semantic_text
- **Ranking and reranking**: Semantic reranking, Learning To Rank (LTR)

### Building Queries
- The _search API
- ES|QL for search
- Retrievers (kNN, linear, pinned, RRF, standard, text similarity re-ranker)
- Search templates

### RAG
- https://www.elastic.co/docs/solutions/search/rag

### Add Search to Your App
- Client libraries (Python, JavaScript, Java, Go, .NET, PHP, Ruby, Rust)
- Search UI library

## Manage Data (https://www.elastic.co/docs/manage-data)

### The Elasticsearch Data Store
- Index basics, data streams, mapping (dynamic/explicit/runtime fields)
- Text analysis: anatomy of an analyzer, configure/test analyzers, custom analyzers
- Templates and aliases

### Ingestion
- Ingesting time series data, solution-specific data, application data
- Ingest with Node.js, Python
- Ingest from relational databases
- Ingest architectures (Agent → ES, Agent → Logstash → ES, with Kafka, etc.)

### Transform and Enrich
- Elasticsearch ingest pipelines
- Data enrichment (enrich processor, geolocation, exact values, ranges)

## Explore and Analyze (https://www.elastic.co/docs/explore-analyze)

### Query Languages
- **Query DSL**: Full-text queries, geo queries, vector queries, term-level queries
- **ES|QL**: Piped syntax, commands (FROM, WHERE, STATS, EVAL, etc.), functions
- **KQL**: Kibana Query Language for search bars
- **SQL**: Elasticsearch SQL interface

### AI Features
- **Agent Builder**: Custom agents, built-in agents, tools (ES|QL tools, index search tools, MCP tools), programmatic access (Kibana APIs, A2A server, MCP server)
- AI chat experiences, AI assistants

### Inference
- Elastic Inference Service (EIS)
- Inference integrations

## Deploy and Manage (https://www.elastic.co/docs/deploy-manage)

### Deployment Options
- **Elastic Cloud Serverless**: Create a project, fully managed, usage-based pricing
- **Elastic Cloud Hosted**: Create a deployment, customer-controlled topology
- **Elastic Cloud on Kubernetes (ECK)**: Kubernetes operator
- **Self-managed**: Local installation, Docker, Linux/macOS/Windows

### Security
- SSL/TLS, API keys, RBAC, users and roles

## Reference (https://www.elastic.co/docs/reference)

### Elasticsearch Reference
- REST APIs, mapping (field data types including dense_vector, semantic_text, sparse_vector)
- Text analysis components (analyzers, tokenizers, token filters, character filters)
- Aggregations (bucket, metrics, pipeline)
- Processor reference (inference, script, enrich, etc.)

### Client Libraries
- Python, JavaScript, Java, Go, .NET, PHP, Ruby, Rust
- Each includes: getting started, installation, connecting, configuration, querying, ES|QL

### Query Language References
- Query DSL: compound, full-text, geo, vector, specialized, term-level queries
- ES|QL: commands, functions (aggregation, date-time, math, search, string, dense vector, multivalue)

## Key Documentation Pages for Common Developer Questions

| Question | Doc Page |
|----------|----------|
| How do I get started? | https://www.elastic.co/docs/get-started |
| How do I set up keyword search? | https://www.elastic.co/docs/solutions/search/full-text |
| How do I set up semantic search? | https://www.elastic.co/docs/solutions/search/semantic |
| How do I do hybrid search? | https://www.elastic.co/docs/solutions/search/hybrid |
| How do I build RAG? | https://www.elastic.co/docs/solutions/search/rag |
| How do I use ES|QL? | https://www.elastic.co/docs/reference/query-languages/esql |
| How do I create an index? | https://www.elastic.co/docs/manage-data/data-store |
| How do I define mappings? | https://www.elastic.co/docs/manage-data/data-store/mapping |
| How do I set up an ingest pipeline? | https://www.elastic.co/docs/manage-data/ingest/transform-enrich/ingest-pipelines |
| How do I use the Python client? | https://www.elastic.co/docs/reference/elasticsearch-clients/python |
| How do I use the JavaScript client? | https://www.elastic.co/docs/reference/elasticsearch-clients/javascript |
| How do I deploy on Elastic Cloud? | https://www.elastic.co/docs/deploy-manage/deploy/elastic-cloud |
| How do I configure dense vectors? | https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/dense-vector |
| How do I use semantic_text? | https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/semantic-text |
| How do I use Agent Builder? | https://www.elastic.co/docs/explore-analyze/ai-features/agent-builder |
| How do I troubleshoot? | https://www.elastic.co/docs/troubleshoot |
