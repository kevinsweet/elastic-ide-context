---
name: vector-hybrid-search
description: Complete guide for building vector search, hybrid search, and using Elasticsearch as a vector database for AI pipelines. Covers the full decision tree from deployment type through production optimization and RAG extension. Use when a developer wants semantic search, hybrid BM25+vector search, kNN, embeddings, RAG, or Elasticsearch as a vector store for LangChain/LlamaIndex.
---

# Vector & Hybrid Search Guide

This guide covers the full lifecycle of building vector or hybrid search with Elasticsearch — from planning and data modeling through production optimization and continuous improvement.

## UI Context Hint

If the rule file contains a `# user-context:` line (set by the getting started UI at download time), read it before the first message and open with a confirmation rather than a blank question:

- `# user-context: vector-database` → "Looks like you're building a vector database for an AI pipeline — is that right? Are you using LangChain, LlamaIndex, or a custom stack?"
- `# user-context: hybrid-search` → "Looks like you're building hybrid search — is that right? Will users be typing queries directly, or is this powering an AI pipeline?"
- `# user-context: semantic-search` → "Looks like you're building semantic search — is that right? Tell me about what you're searching over."

If the developer corrects the use case, re-route immediately. No commitment.

If no `# user-context:` hint is present, open with: "What are you building — a search experience for users, or a retrieval backend for an AI pipeline like RAG or LangChain?"

---

## Consumer Fork: The One Question That Matters First

Before any other decision, establish who consumes the search results:

**AI pipeline** (code consumes results) → LangChain, LlamaIndex, custom RAG, agent memory, recommendations
**Human-facing search** (people type queries) → search bar, results page, filters, autocomplete

This determines Decision I (App Integration) and whether to offer a frontend at the end. Everything else — C through H — is shared between both paths.

---

## Phase 1 — Planning & Decision-Making

### Step 1.1: Define Use Case

Ask what they're building. Listen for:

| Signal | Use Case |
|--------|----------|
| "semantic search", "meaning-based", "natural language" | Semantic search |
| "BM25 + vector", "hybrid", "keyword and semantic" | Hybrid search |
| "RAG", "chatbot", "Q&A over documents", "answer from my docs" | RAG — use rag-chatbot skill |
| "LangChain", "LlamaIndex", "vector store", "embeddings pipeline", "agent memory" | AI pipeline / vector DB |
| "recommendations", "similar items", "you might also like" | Vector similarity |
| "image search", "multimodal" | Dense vector with image embeddings |

**Also ask: how much data?** Listen for scale signals — number of documents, dataset size in GB, or phrases like "millions of records", "large dataset", "production scale", "cost". If the developer indicates large scale (>1M documents, >10GB, cost sensitivity, or production deployment), flag quantization early:

> "With that volume, it's worth choosing your quantization strategy now — it affects your mapping and requires reindexing if you add it later. I'll recommend `int8_hnsw` as the default (about 4x memory reduction with minimal recall impact), but we can discuss options when we get to the mapping step."

This surfaces the decision before it becomes expensive to change. Skip this if the dataset is small or size is unknown — bring it up naturally in Phase 4 instead.

### Decision A: Deployment Type

Ask which Elasticsearch deployment they're using. This determines scaling (Decision J) and monitoring (Decision K) automatically — don't ask about those separately.

| Option | Description | Resolves |
|--------|-------------|---------|
| **A1: Elastic Cloud Serverless** | Fully managed, auto-scaled, pay-as-you-go | J1 (automatic scaling), K1 (AutoOps) |
| **A2: Elastic Cloud Hosted (ECH)** | Dedicated cluster on AWS/Azure/GCP, user controls topology | J2 (policy-based scaling), K1 or K2 |
| **A3: Self-Managed** | ECE, ECK, or bare metal — full control, full responsibility | J3 (manual scaling), K2 or K3 |

### Decision B: Embedding Strategy

**Ask these routing questions first** — the answers determine which embedding options are valid:

1. "Are you already generating embeddings in your own pipeline?" → Yes → briefly offer: "Just so you know, Elasticsearch can handle embedding automatically via `semantic_text` — no embedding code on your end. Want to see that option, or do you prefer to keep control of the pipeline?" If they want to keep control → C2/C3 + D2, skip B entirely.
2. "What version of Elasticsearch are you on?" → Below 8.15 → `semantic_text` unavailable, skip C1
3. "Do you have a specific embedding model you need to use?" → Yes + not supported by inference API → C2 + D2

If none of those disqualify managed embeddings, present the options:

| Option | Description | When to Use |
|--------|-------------|-------------|
| **B1: Built-in Models via EIS** | ELSER (sparse, English) or E5 (dense, multilingual) served by Elastic Inference Service — no ML node cost | Default recommendation for new users on 8.15+ |
| **B1b: Built-in Models on ML Nodes** | Same models but served on the developer's own ML nodes | When EIS is unavailable or they need dedicated capacity |
| **B2: Third-Party Service** | OpenAI, Cohere, Bedrock, Azure AI, Google AI, Mistral via inference endpoint | When they have an existing model contract or need a specific model |
| **B3: Self-Hosted Model** | Upload via Eland client, deploy on ML nodes | Advanced — custom fine-tuned models |

**Default recommendation:** B1 (EIS) — no infrastructure to manage, no external API key needed, Elastic handles the embedding pipeline.

---

## Phase 2 — Data Modeling & Ingestion

### Decision C: Vector Field Type

Three paths. The routing questions from Decision B determine which are available.

| Option | Field Type | When to Use | Notes |
|--------|-----------|-------------|-------|
| **C1: `semantic_text`** | `semantic_text` | 8.15+, using inference endpoint, no existing vectors | **Default recommendation** — auto chunking, auto embedding at ingest and query time, no ingest pipeline needed |
| **C2: `dense_vector`** | `dense_vector` | Bringing your own vectors, need dims/similarity/HNSW control, pre-8.15 | Manual embedding required at ingest and query time |
| **C3: `sparse_vector`** | `sparse_vector` | ELSER manual workflow, need token weight maps | Used when running ELSER outside of `semantic_text` |

**C1 bypasses Decision D entirely** — `semantic_text` resolves embedding generation internally via the inference endpoint bound to the field. If C1, go straight to Configure Chunking.

**C2 and C3 require Decision D.**

#### C1: `semantic_text` Mapping

**Minimal — uses default inference endpoint (works out of the box on Serverless):**

```json
PUT /my-index
{
  "mappings": {
    "properties": {
      "content": {
        "type": "semantic_text"
      },
      "title": { "type": "text" },
      "category": { "type": "keyword" },
      "created_at": { "type": "date" }
    }
  }
}
```

On Serverless, the default endpoint uses ELSER automatically — no setup needed.

**With a specific model (when developer has a preference or existing contract):**

Before generating any mapping, ask: "Do you have a specific embedding model you want to use — like OpenAI, Cohere, or a fine-tuned model — or are you happy for Elastic to handle that automatically?"

- "Elastic can handle it" / "I don't know" → use the minimal mapping above, no further setup
- "OpenAI" / "Cohere" / specific model → use the mapping below and generate the matching inference endpoint config
- Unsure → briefly explain: "Elastic includes built-in models — no API key needed. You can also use OpenAI or Cohere if you have a preference. For most people starting out, the built-in option is simplest." Then let them choose.

```json
PUT /my-index
{
  "mappings": {
    "properties": {
      "content": {
        "type": "semantic_text",
        "inference_id": "my-inference-endpoint"
      }
    }
  }
}
```

Create the inference endpoint first:
```json
PUT _inference/text_embedding/my-inference-endpoint
{
  "service": "elastic",
  "service_settings": {
    "model_id": "<current-eis-embedding-model-id>"
  }
}
```

> **Before generating this code, fetch the current model list from [EIS docs](https://www.elastic.co/docs/explore-analyze/elastic-inference/eis) and use the latest generally-available embedding model ID.** Do not use a hardcoded model ID from memory — EIS models are updated regularly and stale IDs will fail. Pick the right model based on the developer's language needs (ELSER for English-only sparse, Jina or E5 for multilingual dense) and confirm it before generating the `PUT _inference` call.

#### C2: `dense_vector` Mapping

```json
PUT /my-index
{
  "mappings": {
    "properties": {
      "content": { "type": "text" },
      "content_embedding": {
        "type": "dense_vector",
        "dims": 1536,
        "index": true,
        "similarity": "cosine",
        "index_options": {
          "type": "hnsw",
          "m": 16,
          "ef_construction": 100
        }
      },
      "category": { "type": "keyword" }
    }
  }
}
```

Set `dims` to match your embedding model's output (OpenAI `text-embedding-3-small` = 1536, E5-small = 384, Cohere embed-v3 = 1024).

### Decision D: Embedding Generation (C2 and C3 only)

| Option | Description | When to Use |
|--------|-------------|-------------|
| **D1: Inference Endpoint + Ingest Pipeline** | Elasticsearch calls the model at ingest time via an inference processor | When using a supported model and want server-side embedding |
| **D2: Application-Side Embedding** | App generates vectors before indexing, passes them directly | When using unsupported models, existing embedding pipeline, or need full control |

#### D1: Ingest Pipeline with Inference Processor

```json
PUT _ingest/pipeline/embedding-pipeline
{
  "processors": [
    {
      "inference": {
        "model_id": "my-inference-endpoint",
        "input_output": [
          { "input_field": "content", "output_field": "content_embedding" }
        ]
      }
    }
  ]
}
```

#### D2: Application-Side (Python example)

```python
import openai
from elasticsearch import Elasticsearch, helpers

es = Elasticsearch("https://your-cluster:443", api_key="your-api-key")

def embed(text):
    return openai.embeddings.create(
        model="text-embedding-3-small", input=text
    ).data[0].embedding

def generate_actions(docs):
    for doc in docs:
        yield {
            "_index": "my-index",
            "_source": {
                "content": doc["text"],
                "content_embedding": embed(doc["text"]),
                "category": doc.get("category")
            }
        }

helpers.bulk(es, generate_actions(your_docs))
```

### Configure Chunking (C1 and D1 paths)

For `semantic_text` (C1), chunking is configured on the field:

```json
"content": {
  "type": "semantic_text",
  "inference_id": "my-inference-endpoint",
  "chunking_settings": {
    "strategy": "sentence",
    "max_chunk_size": 250,
    "overlap": 1
  }
}
```

Strategies: `sentence` (default), `word`, `recursive`. Default: sentence, 250 words, 1 overlap.

For ingest pipeline (D1), chunking happens before the inference processor — use a script processor or handle in application code before indexing.

### Decision E: Ingestion Method

| Option | Description | When to Use |
|--------|-------------|-------------|
| **E1: Bulk API / Client Libraries** | Python, Java, Go, JS, etc. | Most cases — programmatic ingestion from any source |
| **E2: Elastic Open Web Crawler** | Crawls websites and indexes content | Web content, documentation sites |
| **E3: Content Connectors** | SharePoint, Confluence, Jira, MongoDB, S3, and more | Pre-built connectors for common sources |
| **E4: File Upload** | Kibana UI upload | Testing and small datasets only |

#### E1: Bulk API (Python)

```python
from elasticsearch import Elasticsearch, helpers

es = Elasticsearch(
    "https://your-cluster.es.us-central1.gcp.elastic.cloud:443",
    api_key="your-api-key"
)

docs = [
    {"_index": "my-index", "_source": {"content": "...", "category": "docs"}},
    {"_index": "my-index", "_source": {"content": "...", "category": "faq"}},
]

# Allow time for ML model to load on first ingest
success, failed = helpers.bulk(
    es.options(request_timeout=300),
    docs,
    refresh="wait_for"
)
```

---

## Phase 3 — Search Implementation

### Decision F: Search Type

| Option | Description | When to Use |
|--------|-------------|-------------|
| **F1: Pure kNN** | Vector similarity only | All queries are semantic/meaning-based, no need for exact term matching |
| **F2: Hybrid** | BM25 + vector via RRF or Linear Retriever | Users search with both keywords AND natural language; exact terms matter (product IDs, codes, names) |
| **F3: Semantic** | Semantic query via `semantic_text` field | Using C1 path; simplest semantic search |

**Default recommendation for most use cases: F2 (Hybrid)** — covers both exact and meaning-based queries, works well out of the box via RRF without score normalization.

#### F3: Semantic Search (C1 / `semantic_text` path)

```json
POST my-index/_search
{
  "retriever": {
    "standard": {
      "query": {
        "semantic": {
          "field": "content",
          "query": "how do I configure index mappings"
        }
      }
    }
  }
}
```

#### F1: Pure kNN (C2 / `dense_vector` path)

```json
POST my-index/_search
{
  "retriever": {
    "knn": {
      "field": "content_embedding",
      "query_vector": [0.1, 0.2, ...],
      "k": 10,
      "num_candidates": 100
    }
  }
}
```

For approximate kNN (HNSW): tune `num_candidates` (higher = better recall, slower) and `k`.
For exact kNN: use `script_score` — only for small datasets.

#### F2: Hybrid Search with RRF

```json
POST my-index/_search
{
  "retriever": {
    "rrf": {
      "retrievers": [
        {
          "standard": {
            "query": {
              "multi_match": {
                "query": "elasticsearch index mapping",
                "fields": ["title^2", "content"]
              }
            }
          }
        },
        {
          "knn": {
            "field": "content_embedding",
            "query_vector": [0.1, 0.2, ...],
            "k": 50,
            "num_candidates": 100
          }
        }
      ],
      "window_size": 100,
      "rank_constant": 60
    }
  }
}
```

**Why RRF:** Works purely on rank positions — no score normalization needed between BM25 and kNN. Robust out of the box.

**Tuning RRF:**
- `window_size`: How many docs from each retriever to consider. Higher = more semantic influence when BM25 is sparse.
- `rank_constant`: Higher = flatter rank contribution. Lower = steeper preference for top ranks.

#### Hybrid with Filters

```json
POST my-index/_search
{
  "retriever": {
    "rrf": {
      "retrievers": [
        {
          "standard": {
            "query": {
              "bool": {
                "must": { "multi_match": { "query": "mapping", "fields": ["content"] } },
                "filter": { "term": { "category": "docs" } }
              }
            }
          }
        },
        {
          "knn": {
            "field": "content_embedding",
            "query_vector": [...],
            "k": 50,
            "num_candidates": 100,
            "filter": { "term": { "category": "docs" } }
          }
        }
      ]
    }
  }
}
```

### Decision G: Reranking?

| Option | Description | When to Use |
|--------|-------------|-------------|
| **G1: No Reranking** | Use initial retrieval scores | Most cases — RRF already produces good results |
| **G2: Semantic Reranker** | `text_similarity_reranker` retriever — cross-encoder model reranks top results | When relevance quality matters more than latency; adds ~50-200ms |
| **G3: Learning to Rank** | Custom trained model using relevance judgments | Advanced — requires labeled query/document pairs; high investment |
| **G4: Query Rules** | Pin or exclude documents by metadata criteria | Merchandising, editorial control, compliance filtering |

**Default recommendation: G1** — start without reranking, add G2 if relevance isn't good enough after tuning.

#### G2: Semantic Reranker

```json
POST my-index/_search
{
  "retriever": {
    "text_similarity_reranker": {
      "retriever": {
        "rrf": {
          "retrievers": [
            { "standard": { "query": { "multi_match": { "query": "your query", "fields": ["content"] } } } },
            { "knn": { "field": "content_embedding", "query_vector": [...], "k": 50, "num_candidates": 100 } }
          ]
        }
      },
      "field": "content",
      "inference_id": "my-reranker-endpoint",
      "inference_text": "your query",
      "rank_window_size": 50
    }
  }
}
```

> Check [reranker docs](https://www.elastic.co/docs/solutions/search/ranking/semantic-reranking) for current inference endpoint setup.

#### G4: Query Rules

```json
PUT _query_rules/my-ruleset
{
  "rules": [
    {
      "rule_id": "pin-featured",
      "type": "pinned",
      "criteria": [{ "type": "contains", "metadata": "query_string", "values": ["featured"] }],
      "actions": { "ids": ["doc-123"] }
    }
  ]
}
```

### Decision H: Query Method

| Option | Description | When to Use |
|--------|-------------|-------------|
| **H1: Query DSL** | Traditional JSON query | Legacy codebases, maximum compatibility |
| **H2: Retrievers API** | Composable, recommended — all examples above use this | **Default — use for all new code** |
| **H3: ES\|QL** | Pipe-based language for analytics | Not recommended for vector search retrieval — use for analytics and data exploration only |

**Always use H2 (Retrievers API) for vector and hybrid search.** It's composable, handles RRF natively, and is the direction Elastic is investing in.

### Decision I: App Integration

**AI pipeline path:**

| Option | Description |
|--------|-------------|
| **I1: Direct API via Client Library** | Python, JS, Java, Go — raw Elasticsearch client |
| **I4: Agent Builder / RAG** | Elastic's Playground, Agent Builder, ES\|QL COMPLETION for LLM integration |

**Human-facing search path:**

| Option | Description |
|--------|-------------|
| **I1: Direct API** | Custom search endpoint |
| **I2: Search Templates** | Parameterized queries server-side |
| **I3: Search UI** | React library — see search-ui skill |

#### LangChain Integration (AI pipeline)

```bash
pip install langchain-elasticsearch langchain-openai
```

```python
from langchain_elasticsearch import ElasticsearchStore
from langchain_openai import OpenAIEmbeddings
from elasticsearch import Elasticsearch

es_client = Elasticsearch(
    "https://your-cluster.es.us-central1.gcp.elastic.cloud:443",
    api_key="your-api-key"
)

vector_store = ElasticsearchStore(
    es_connection=es_client,
    index_name="my_docs",
    embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
)

# Add documents
vector_store.add_documents([
    {"page_content": "Elasticsearch is a distributed search engine.", "metadata": {"source": "docs"}},
])

# Similarity search
results = vector_store.similarity_search("How do I visualize data?", k=3)

# As retriever in a chain
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI

qa_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(model="gpt-4o-mini"),
    retriever=vector_store.as_retriever(search_kwargs={"k": 5}),
    return_source_documents=True
)
answer = qa_chain.invoke({"query": "What is Kibana?"})
```

#### LlamaIndex Integration (AI pipeline)

```bash
pip install llama-index llama-index-vector-stores-elasticsearch
```

```python
from llama_index.vector_stores.elasticsearch import ElasticsearchVectorStore
from llama_index.core import VectorStoreIndex, Document

vector_store = ElasticsearchVectorStore(
    index_name="llama_docs",
    es_url="https://your-cluster.es.us-central1.gcp.elastic.cloud:443",
    es_api_key="your-api-key",
)

index = VectorStoreIndex.from_documents(
    [Document(text="Elasticsearch supports full-text and vector search.")],
    vector_store=vector_store,
)

response = index.as_query_engine(similarity_top_k=5).query("How do I build dashboards?")
```

#### Search API Endpoint (Human-facing, Python/Flask)

```python
from flask import Flask, request, jsonify
from elasticsearch import Elasticsearch

app = Flask(__name__)
es = Elasticsearch("https://your-cluster:443", api_key="your-api-key")

@app.route("/search")
def search():
    q = request.args.get("q", "")
    if not q:
        return jsonify({"error": "Missing q"}), 400

    # Hybrid search via Retrievers API
    response = es.search(
        index="my-index",
        size=20,
        body={
            "retriever": {
                "rrf": {
                    "retrievers": [
                        {"standard": {"query": {"multi_match": {"query": q, "fields": ["title^2", "content"]}}}},
                        {"knn": {"field": "content_embedding", "query_vector": embed(q), "k": 50, "num_candidates": 100}}
                    ],
                    "window_size": 100,
                    "rank_constant": 60
                }
            }
        }
    )
    return jsonify({"hits": [h["_source"] for h in response["hits"]["hits"]]})
```

Always include pagination — `from`/`size` for basic (up to 10,000 results), `search_after` with PIT for deep pagination.

---

## Phase 4 — Production & Optimization

### Step 4.1: Performance Tuning

**Quantization** — reduces vector memory footprint significantly:

```json
"content_embedding": {
  "type": "dense_vector",
  "dims": 1536,
  "index": true,
  "similarity": "cosine",
  "index_options": {
    "type": "int8_hnsw"
  }
}
```

| Type | Memory reduction | Recall impact |
|------|-----------------|---------------|
| `hnsw` | Baseline | Baseline |
| `int8_hnsw` | ~4x reduction | Minimal |
| `int4_hnsw` | ~8x reduction | Small |
| `bbq_hnsw` | ~32x reduction | Moderate — test with your data |

**Force-merge segments** after bulk ingestion to improve query performance:
```python
es.indices.forcemerge(index="my-index", max_num_segments=1)
```

**Warm filesystem cache** after force-merge:
```python
es.indices.clear_cache(index="my-index")
# Then run a few queries to warm the cache
```

**HNSW vs DiskBBQ:** Use `bbq_hnsw` for large datasets where memory is the constraint and you can tolerate slightly lower recall. Use `int8_hnsw` as the safe default.

### Step 4.2: Shard Sizing

- Target **10–50 GB per shard**
- Max **200M docs per shard**
- Use ILM for rollover on time-series data

```json
PUT _ilm/policy/vector-rollover
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": { "max_size": "50gb", "max_docs": 200000000 }
        }
      }
    }
  }
}
```

### Decision J: Scaling Strategy

Already resolved from Decision A:

| Deployment | Strategy |
|------------|----------|
| **Serverless (A1)** | J1: Automatic — no config needed |
| **ECH / ECE (A2)** | J2: Policy-based autoscaling deciders + adaptive allocations |
| **Self-Managed (A3)** | J3: Manual provisioning + K8s HPA for ECK |

### Decision K: Monitoring

Already resolved from Decision A:

| Deployment | Default |
|------------|---------|
| **Cloud (A1, A2)** | K1: AutoOps — auto-enabled, recommendations and alerts |
| **Self-Managed (A3)** | K2: Stack Monitoring (Metricbeat + Filebeat + Kibana dashboards) or K3: External (Prometheus, Grafana, Datadog) |

---

## Phase 5 — Iteration & Continuous Improvement

### Step 5.1: Evaluate Search Quality

**Ranking Evaluation API (`_rank_eval`)** — measures how well your query ranks known-relevant documents:

```json
POST my-index/_rank_eval
{
  "requests": [
    {
      "id": "query_1",
      "request": {
        "query": { "multi_match": { "query": "elasticsearch mapping", "fields": ["content"] } }
      },
      "ratings": [
        { "_index": "my-index", "_id": "doc-1", "rating": 3 },
        { "_index": "my-index", "_id": "doc-2", "rating": 1 }
      ]
    }
  ],
  "metric": { "ndcg": { "k": 10 } }
}
```

**Profile API** — diagnose latency:

```json
POST my-index/_search
{
  "profile": true,
  "query": { "match": { "content": "test" } }
}
```

### Step 5.2: Refine Pipeline

Work through these levers in order — each addresses a different failure mode:

| Lever | What it fixes |
|-------|--------------|
| Swap embedding model | Poor semantic recall — wrong language, domain mismatch |
| Adjust chunking strategy/size | Chunks too large (noisy) or too small (missing context) |
| Tune hybrid weights (`window_size`, `rank_constant`) | BM25 or semantic dominating when it shouldn't |
| Add reranking (G2) | Top results semantically close but not the best answer |
| Add query rules (G4) | Specific queries returning wrong results despite good overall quality |
| Try quantization level | Memory pressure or latency too high |

### Decision: Extend to RAG?

After search quality is acceptable, decide whether to extend to RAG:

**No** → loop back to Step 5.1, continue optimizing retrieval

**Yes** →

### Step 5.3: Implement RAG

```python
from elasticsearch import Elasticsearch
import openai

es = Elasticsearch("https://your-cluster:443", api_key="your-api-key")
oai = openai.OpenAI()

def rag_query(question: str, k: int = 5) -> dict:
    # Retrieve relevant chunks
    response = es.search(
        index="my-index",
        body={
            "retriever": {
                "rrf": {
                    "retrievers": [
                        {"standard": {"query": {"semantic": {"field": "content", "query": question}}}},
                        {"standard": {"query": {"multi_match": {"query": question, "fields": ["content"]}}}}
                    ]
                }
            },
            "size": k,
            "_source": ["content", "title"]
        }
    )

    chunks = [hit["_source"]["content"] for hit in response["hits"]["hits"]]
    sources = [hit["_source"].get("title", hit["_id"]) for hit in response["hits"]["hits"]]
    context = "\n\n".join(chunks)

    # Generate answer
    completion = oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Answer based only on the provided context. If the answer isn't in the context, say so."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        ]
    )

    return {
        "answer": completion.choices[0].message.content,
        "sources": sources
    }
```

For Elastic-native RAG, see [Agent Builder](https://www.elastic.co/docs/solutions/search) and Playground — no external LLM API key needed if using EIS managed LLMs.

---

## Metadata Filtering Patterns

Store permission and tenant fields on each document and filter at query time:

```json
"properties": {
  "user_ids": { "type": "keyword" },
  "tenant_id": { "type": "keyword" },
  "groups": { "type": "keyword" }
}
```

```json
"filter": {
  "bool": {
    "should": [
      { "term": { "tenant_id": "acme" } },
      { "terms": { "user_ids": ["user_123"] } }
    ]
  }
}
```

For large-scale multi-tenancy, use separate indices per tenant — simpler than row-level security at scale.

---

## Common Follow-ups

| Question | Answer |
|----------|--------|
| "Results aren't relevant enough" | Run `_rank_eval`, then work through Step 5.2 levers |
| "How do I weight keyword vs semantic?" | Tune `window_size` and `rank_constant` in RRF |
| "Results are too semantic / too keyword-heavy" | Adjust `window_size` — higher favors semantic, lower favors BM25 |
| "How do I add reranking?" | Use `text_similarity_reranker` retriever wrapping your RRF retriever |
| "Memory is too high" | Add `int8_hnsw` quantization to `dense_vector` mapping, reindex |
| "How do I delete/update vectors?" | `delete_by_query` or update by `_id`; reindex if embedding model changes |
| "Pinecone/Weaviate vs Elasticsearch?" | Elasticsearch adds hybrid search, metadata filtering, and consolidates search + vectors + analytics in one system |

## When to Use Other Skills

| Situation | Skill |
|-----------|-------|
| Pure keyword search, no vectors needed | keyword-search |
| RAG / Q&A chatbot with LLM answer generation | rag-chatbot |
| React search frontend | search-ui |
| Product catalog with facets and merchandising | catalog-ecommerce |
