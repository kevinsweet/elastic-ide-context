"""
Pulls products from PostgreSQL and bulk-indexes into Elasticsearch.

Handles:
  - Attribute JSONB → nested name/value pairs transformation
  - Autocomplete suggestion generation
  - Batched server-side cursor for memory-efficient reads
  - Embedding generation via ingest pipeline (server-side)

Environment Variables
---------------------
Elasticsearch:
  ES_CLOUD_ID, ES_API_KEY  (or ES_URL, ES_USER, ES_PASSWORD for self-managed)

PostgreSQL:
  PG_HOST     — default: localhost
  PG_PORT     — default: 5432
  PG_DB       — database name (required)
  PG_USER     — default: postgres
  PG_PASSWORD — password (required)
  PG_TABLE    — table name (default: products)
"""

import os
import sys
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk, BulkIndexError
import psycopg2
import psycopg2.extras


BATCH_SIZE = 500
ALIAS = "products"
PIPELINE_ID = "product-embedding-pipeline"


def get_es_client():
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


def get_pg_connection():
    pg_db = os.environ.get("PG_DB")
    if not pg_db:
        print("Error: PG_DB environment variable is required")
        sys.exit(1)

    return psycopg2.connect(
        host=os.environ.get("PG_HOST", "localhost"),
        port=int(os.environ.get("PG_PORT", "5432")),
        dbname=pg_db,
        user=os.environ.get("PG_USER", "postgres"),
        password=os.environ.get("PG_PASSWORD", ""),
    )


def transform_attributes(attrs):
    """Convert JSONB dict to nested array of {name, value} pairs.

    {"color": "Black", "connectivity": ["USB-C", "Bluetooth"]}
    →
    [{"name": "color", "value": "Black"},
     {"name": "connectivity", "value": "USB-C"},
     {"name": "connectivity", "value": "Bluetooth"}]
    """
    if not attrs or not isinstance(attrs, dict):
        return []

    result = []
    for key, value in attrs.items():
        if isinstance(value, list):
            for v in value:
                result.append({"name": key, "value": str(v)})
        else:
            result.append({"name": key, "value": str(value)})
    return result


def generate_actions(cursor):
    """Yield bulk index actions from Postgres cursor."""
    for row in cursor:
        doc = dict(row)

        doc["attributes"] = transform_attributes(doc.get("attributes"))

        doc["name_suggest"] = {
            "input": [doc.get("name", "")],
            "weight": max(1, doc.get("stock_quantity", 1)),
        }

        # Convert datetime objects to ISO strings for Elasticsearch
        for date_field in ("created_at", "updated_at"):
            if doc.get(date_field) and hasattr(doc[date_field], "isoformat"):
                doc[date_field] = doc[date_field].isoformat()

        yield {
            "_index": ALIAS,
            "_id": doc.get("sku"),
            "pipeline": PIPELINE_ID,
            "_source": doc,
        }


def ingest():
    es = get_es_client()
    conn = get_pg_connection()

    table = os.environ.get("PG_TABLE", "products")

    print(f"Reading from PostgreSQL table '{table}'...")
    cursor = conn.cursor(
        cursor_factory=psycopg2.extras.RealDictCursor,
        name="product_cursor",
    )
    cursor.itersize = BATCH_SIZE
    cursor.execute(f"SELECT * FROM {table}")

    try:
        success, errors = bulk(
            es,
            generate_actions(cursor),
            chunk_size=BATCH_SIZE,
            raise_on_error=False,
            raise_on_exception=False,
        )
        print(f"\nIndexed {success} products into '{ALIAS}'")
        if errors:
            print(f"  {len(errors)} errors:")
            for err in errors[:5]:
                print(f"    {err}")
    except BulkIndexError as e:
        print(f"Bulk indexing errors: {len(e.errors)}")
        for err in e.errors[:5]:
            print(f"  {err}")
    finally:
        cursor.close()
        conn.close()
        print("Done.")


if __name__ == "__main__":
    ingest()
