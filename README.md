# Elastic IDE Context

Use-case-aware developer context for AI-native IDEs. Turns your AI coding assistant into an Elasticsearch solutions architect that guides you from "I want search" to a working search experience.

## Two Modes

This repo includes two rule files. **Guided Mode is active by default.** Both files ship together — no need to delete anything.

### Guided Mode (default — active)

`.cursor/rules/elastic.mdc` — A structured conversational playbook. The AI walks you step by step from intent to working search: asks what you're building, understands your data, recommends an approach, walks through the mapping, and generates production-ready code. Best for developers who are new to Elasticsearch or want an opinionated, end-to-end experience.

### Open Mode

`.cursor/rules/elastic-open.mdc` — An expert assistant with no prescribed sequence. The AI has the same Elasticsearch knowledge, documentation references, and code standards, but it responds to what you ask rather than driving a flow. Best for developers who already know Elasticsearch and want a knowledgeable pair-programmer, not a guided tour.

### Switching Modes

Each rule file has a settings block at the top. The line `alwaysApply: true` means that mode is active. To switch:

1. Open `.cursor/rules/elastic-open.mdc` and change `alwaysApply: false` to `alwaysApply: true`
2. Open `.cursor/rules/elastic.mdc` and change `alwaysApply: true` to `alwaysApply: false`

Both files share the same pattern guides, documentation, and MCP setup — the only difference is the conversation style.

### Search Pattern Guides

Each guide is a complete, tested pattern covering index mapping, ingestion, query patterns, API endpoint, and relevance tuning.

| Pattern | Use Case |
|---------|----------|
| **keyword-search** | Full-text search, filters, facets, autocomplete, typo tolerance |
| **semantic-search** | Vector/embedding-based search, kNN, meaning-based matching |
| **hybrid-search** | BM25 + kNN combined with Reciprocal Rank Fusion (RRF) |
| **rag-chatbot** | Retrieval-augmented generation, Q&A, chatbots over documents |
| **catalog-ecommerce** | Product search, faceted navigation, merchandising, autocomplete |
| **vector-database** | Elasticsearch as a vector store for AI apps (LangChain, LlamaIndex) |
| **search-ui** | React search frontend — search bar, facets, results, autocomplete, pagination |

## Setup (Cursor)

1. Copy `.cursor/` into your project root
2. The Guided Mode rule file loads automatically
3. Pattern guides are available when the AI detects a matching use case
4. To use Open Mode instead, see [Switching Modes](#switching-modes) above

## Getting Started

Open a new Agent chat and describe what you're building. The more specific, the better. For example:

- *"I need fast product search across 2 million SKUs with filters, autocomplete, and typo tolerance."*
- *"I want a Q&A chatbot that answers questions from our internal documentation."*
- *"I need semantic search across support tickets so agents can find similar past cases."*
- *"I want to use Elasticsearch as a vector database for my LangChain app."*
- *"I'm building a RAG pipeline and need a retrieval backend with hybrid search."*
- *"I need a customer support knowledge base where users can find answers themselves."*
- *"I want location-based search — find nearby stores, restaurants, or services."*
- *"I have a working Elasticsearch index and need to build a search page with React."*

The AI will walk you through the right approach for your use case, help you design your index mapping, and generate production-ready code tailored to your data.

## Setup (Other IDEs)

- **GitHub Copilot**: Copy rule file content to `.github/copilot-instructions.md`
- **Claude Code**: Copy rule file content to `CLAUDE.md`

## How It Works

This follows a three-layer architecture:

1. **Orchestrator** (rule file) — Lightweight playbook that drives the conversation flow
2. **Pattern guides** (skill files) — Pre-built, tested knowledge for each search pattern
3. **Live data** (MCP server) — Connect to your Elasticsearch cluster for real-time schema inspection and queries (requires [Elastic MCP server](https://github.com/elastic/elasticsearch-mcp-server))
