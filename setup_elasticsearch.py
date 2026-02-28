"""
Sets up Elasticsearch for hybrid product search:
  1. Inference endpoint (sentence-transformers for embeddings)
  2. Synonym set (updateable via Synonyms API — no reindex needed)
  3. Ingest pipeline (auto-generates embeddings on index)
  4. Index with mapping + alias

Run once before ingesting data.

Getting Started — Finding Your Credentials
-------------------------------------------
Cloud ID:
  In Kibana, click the help icon (?) → Connection details.
  Or visit https://cloud.elastic.co → your deployment → overview page.

API Key:
  In Kibana → Management → Security → API keys → Create API key.
  Copy the "Encoded" value — that's your api_key.
  Or via Dev Tools:
    POST /_security/api_key
    {"name": "dev-key", "expiration": "30d"}

Self-managed:
  Set ES_URL to your Elasticsearch host instead of using cloud_id.
  Set ES_USER and ES_PASSWORD for basic auth.

Environment Variables
---------------------
  ES_CLOUD_ID   — Elastic Cloud deployment ID
  ES_API_KEY    — Encoded API key
  -- OR for self-managed --
  ES_URL        — Elasticsearch URL (default: https://localhost:9200)
  ES_USER       — Username (default: elastic)
  ES_PASSWORD   — Password (default: changeme)
"""

import os
import sys
from elasticsearch import Elasticsearch


INFERENCE_ID = "product-embedding-model"
SYNONYM_SET_ID = "product-synonyms"
PIPELINE_ID = "product-embedding-pipeline"
INDEX_NAME = "products-v1"
ALIAS_NAME = "products"


def get_client():
    cloud_id = os.environ.get("ES_CLOUD_ID")
    api_key = os.environ.get("ES_API_KEY")

    if cloud_id and api_key:
        return Elasticsearch(cloud_id=cloud_id, api_key=api_key)

    return Elasticsearch(
        hosts=[os.environ.get("ES_URL", "https://localhost:9200")],
        basic_auth=(
            os.environ.get("ES_USER", "elastic"),
            os.environ.get("ES_PASSWORD", "changeme"),
        ),
        verify_certs=False,
    )


def create_inference_endpoint(es):
    """Deploy sentence-transformers model for product embeddings (384 dims)."""
    print(f"Creating inference endpoint '{INFERENCE_ID}'...")
    es.inference.put(
        task_type="text_embedding",
        inference_id=INFERENCE_ID,
        inference_config={
            "service": "elasticsearch",
            "service_settings": {
                "model_id": "sentence-transformers__all-MiniLM-L6-v2",
                "num_allocations": 1,
                "num_threads": 1,
            },
        },
    )
    print("  Done — inference endpoint created")


def create_synonym_set(es):
    """Create an updateable synonym set via the Synonyms API.

    Start with a minimal set — expand based on your product domain
    and what users actually search for. Update anytime without reindexing:
      PUT _synonyms/product-synonyms
    """
    print(f"Creating synonym set '{SYNONYM_SET_ID}'...")
    es.synonyms.put_synonym(
        id=SYNONYM_SET_ID,
        body={
            "synonyms_set": [
                {"id": "starter-1", "synonyms": "laptop, notebook"},
                {"id": "starter-2", "synonyms": "phone, mobile, cell phone"},
                {"id": "starter-3", "synonyms": "tv, television"},
                {"id": "starter-4", "synonyms": "headphones, earphones, earbuds"},
            ]
        },
    )
    print("  Done — update anytime via PUT _synonyms/product-synonyms")


def create_ingest_pipeline(es):
    """Create pipeline that generates embeddings from name + description."""
    print(f"Creating ingest pipeline '{PIPELINE_ID}'...")
    es.ingest.put_pipeline(
        id=PIPELINE_ID,
        body={
            "description": "Generate product embeddings from name + description",
            "processors": [
                {
                    "set": {
                        "field": "_combined_text",
                        "value": "{{name}} {{description}}",
                    }
                },
                {
                    "inference": {
                        "model_id": INFERENCE_ID,
                        "input_output": [
                            {
                                "input_field": "_combined_text",
                                "output_field": "product_embedding",
                            }
                        ],
                    }
                },
                {"remove": {"field": "_combined_text"}},
            ],
        },
    )
    print("  Done — ingest pipeline created")


def create_index(es):
    """Create the products index with mapping, analyzers, and alias."""
    print(f"Creating index '{INDEX_NAME}' with alias '{ALIAS_NAME}'...")
    es.indices.create(
        index=INDEX_NAME,
        body={
            "settings": {
                "analysis": {
                    "analyzer": {
                        "autocomplete_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "autocomplete_filter"],
                        },
                        "synonym_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "product_synonyms"],
                        },
                    },
                    "filter": {
                        "autocomplete_filter": {
                            "type": "edge_ngram",
                            "min_gram": 2,
                            "max_gram": 15,
                        },
                        "product_synonyms": {
                            "type": "synonym",
                            "synonyms_set": SYNONYM_SET_ID,
                            "updateable": True,
                        },
                    },
                },
            },
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "name": {
                        "type": "text",
                        "analyzer": "synonym_analyzer",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "autocomplete": {
                                "type": "text",
                                "analyzer": "autocomplete_analyzer",
                                "search_analyzer": "standard",
                            },
                        },
                    },
                    "description": {
                        "type": "text",
                        "analyzer": "synonym_analyzer",
                    },
                    "sku": {"type": "keyword"},
                    "slug": {"type": "keyword", "index": False},
                    "category_id": {"type": "integer"},
                    "price": {"type": "float"},
                    "stock_quantity": {"type": "integer"},
                    "status": {"type": "keyword"},
                    "attributes": {
                        "type": "nested",
                        "properties": {
                            "name": {"type": "keyword"},
                            "value": {"type": "keyword"},
                        },
                    },
                    "product_embedding": {
                        "type": "dense_vector",
                        "dims": 384,
                        "index": True,
                        "similarity": "cosine",
                    },
                    "name_suggest": {
                        "type": "completion",
                        "analyzer": "simple",
                    },
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                },
            },
            "aliases": {ALIAS_NAME: {}},
        },
    )
    print(f"  Done — index created with alias '{ALIAS_NAME}'")


def main():
    es = get_client()
    info = es.info()
    print(f"Connected to Elasticsearch {info['version']['number']}\n")

    create_inference_endpoint(es)
    create_synonym_set(es)
    create_ingest_pipeline(es)
    create_index(es)

    print("\nSetup complete! Next: run ingest_from_postgres.py to load your data.")


if __name__ == "__main__":
    main()
