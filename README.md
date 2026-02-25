# Elastic IDE Context

Use-case-aware developer context for AI-native IDEs. Turns your AI coding assistant into an Elasticsearch solutions architect that guides you from "I want search" to a working search experience.

## What's Inside

### Orchestrator Rule File

`.cursor/rules/elastic.mdc` — A conversational playbook that teaches your AI assistant to:

1. Understand what you're building (intent)
2. Understand your data shape
3. Check what's already in your Elasticsearch cluster
4. Recommend the right search pattern
5. Guide you through ingestion and implementation
6. Iterate based on your feedback

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

## Setup (Cursor)

1. Copy `.cursor/` into your project root
2. The rule file loads automatically and guides the AI's behavior
3. Pattern guides are available when the AI detects a matching use case

## Getting Started

Open a new Agent chat and describe what you're building. The more specific, the better. For example:

- *"I need fast product search across 2 million SKUs with filters, autocomplete, and typo tolerance."*
- *"I want a Q&A chatbot that answers questions from our internal documentation."*
- *"I need semantic search across support tickets so agents can find similar past cases."*
- *"I want to use Elasticsearch as a vector database for my LangChain app."*
- *"I'm building a RAG pipeline and need a retrieval backend with hybrid search."*
- *"I need a customer support knowledge base where users can find answers themselves."*
- *"I want location-based search — find nearby stores, restaurants, or services."*

The AI will walk you through the right approach for your use case, help you design your index mapping, and generate production-ready code tailored to your data.

## Setup (Other IDEs)

- **GitHub Copilot**: Copy rule file content to `.github/copilot-instructions.md`
- **Claude Code**: Copy rule file content to `CLAUDE.md`

## How It Works

This follows a three-layer architecture:

1. **Orchestrator** (rule file) — Lightweight playbook that drives the conversation flow
2. **Pattern guides** (skill files) — Pre-built, tested knowledge for each search pattern
3. **Live data** (MCP server) — Connect to your Elasticsearch cluster for real-time schema inspection and queries (requires [Elastic MCP server](https://github.com/elastic/elasticsearch-mcp-server))
