"""
Flask API for hybrid product search with Elasticsearch.

Endpoints:
  GET /search       — Hybrid keyword + semantic search with filters, facets, pagination
  GET /autocomplete — Product name suggestions as the user types
  GET /suggest      — "Did you mean" spelling corrections

Environment Variables:
  ES_CLOUD_ID, ES_API_KEY  (or ES_URL, ES_USER, ES_PASSWORD for self-managed)
"""

import os
from flask import Flask, request, jsonify
from elasticsearch import Elasticsearch

app = Flask(__name__)

ALIAS = "products"
INFERENCE_ID = "product-embedding-model"


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


es = get_es_client()


@app.route("/search", methods=["GET"])
def search():
    """Hybrid product search with filters, facets, and pagination.

    Query params:
      q          — search query (empty = browse mode)
      category_id — filter by category (integer)
      status     — filter by status ("active", "out_of_stock")
      min_price  — minimum price
      max_price  — maximum price
      in_stock   — "true" to show only in-stock products
      attr_*     — attribute filters (e.g. attr_color=Black)
      sort       — "relevance" (default), "price_asc", "price_desc", "newest"
      page       — page number (default 1)
      size       — results per page (default 20, max 100)
    """
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", type=int)
    status = request.args.get("status")
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    in_stock = request.args.get("in_stock")
    sort_by = request.args.get("sort", "relevance")
    page = request.args.get("page", 1, type=int)
    size = min(request.args.get("size", 20, type=int), 100)

    # --- Filters ---
    filters = []
    if category_id is not None:
        filters.append({"term": {"category_id": category_id}})
    if status:
        filters.append({"term": {"status": status}})
    if min_price is not None:
        filters.append({"range": {"price": {"gte": min_price}}})
    if max_price is not None:
        filters.append({"range": {"price": {"lte": max_price}}})
    if in_stock == "true":
        filters.append({"range": {"stock_quantity": {"gt": 0}}})

    # Dynamic attribute filters: ?attr_color=Black&attr_switch_type=Tactile+Brown
    for key, value in request.args.items():
        if key.startswith("attr_"):
            attr_name = key[5:]
            filters.append({
                "nested": {
                    "path": "attributes",
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"attributes.name": attr_name}},
                                {"term": {"attributes.value": value}},
                            ]
                        }
                    },
                }
            })

    # --- Query ---
    if q:
        search_body = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": q,
                                "fields": ["name^3", "description"],
                                "type": "best_fields",
                                "fuzziness": "AUTO",
                            }
                        },
                        {
                            "knn": {
                                "field": "product_embedding",
                                "query_vector_builder": {
                                    "text_embedding": {
                                        "model_id": INFERENCE_ID,
                                        "model_text": q,
                                    }
                                },
                                "k": 20,
                                "num_candidates": 100,
                            }
                        },
                    ],
                    "filter": filters,
                }
            },
            "rank": {
                "rrf": {
                    "window_size": 100,
                    "rank_constant": 60,
                }
            },
        }
    else:
        search_body = {
            "query": {
                "bool": {
                    "must": [{"match_all": {}}],
                    "filter": filters,
                }
            },
        }

    # --- Sort ---
    sort_options = {
        "relevance": [{"_score": "desc"}],
        "price_asc": [{"price": "asc"}],
        "price_desc": [{"price": "desc"}],
        "newest": [{"created_at": "desc"}],
    }
    if not q and sort_by == "relevance":
        search_body["sort"] = [{"created_at": "desc"}]
    elif sort_by != "relevance":
        search_body["sort"] = sort_options.get(sort_by, sort_options["relevance"])

    # --- Pagination ---
    search_body["from"] = (page - 1) * size
    search_body["size"] = size

    # --- Highlighting ---
    search_body["highlight"] = {
        "fields": {"name": {}, "description": {}},
        "pre_tags": ["<em>"],
        "post_tags": ["</em>"],
    }

    # --- Facets ---
    search_body["aggs"] = {
        "categories": {"terms": {"field": "category_id", "size": 50}},
        "statuses": {"terms": {"field": "status", "size": 10}},
        "price_stats": {"stats": {"field": "price"}},
        "price_ranges": {
            "range": {
                "field": "price",
                "ranges": [
                    {"to": 50, "key": "Under $50"},
                    {"from": 50, "to": 100, "key": "$50-$100"},
                    {"from": 100, "to": 200, "key": "$100-$200"},
                    {"from": 200, "to": 500, "key": "$200-$500"},
                    {"from": 500, "key": "$500+"},
                ],
            }
        },
    }

    # Exclude the embedding vector from response
    search_body["_source"] = {"excludes": ["product_embedding"]}

    resp = es.search(index=ALIAS, body=search_body)

    total = resp["hits"]["total"]["value"]
    return jsonify({
        "hits": [
            {
                "product": h["_source"],
                "score": h.get("_score"),
                "highlight": h.get("highlight", {}),
            }
            for h in resp["hits"]["hits"]
        ],
        "total": total,
        "facets": {
            "categories": [
                {"key": b["key"], "count": b["doc_count"]}
                for b in resp["aggregations"]["categories"]["buckets"]
            ],
            "statuses": [
                {"key": b["key"], "count": b["doc_count"]}
                for b in resp["aggregations"]["statuses"]["buckets"]
            ],
            "price_ranges": [
                {"key": b["key"], "count": b["doc_count"]}
                for b in resp["aggregations"]["price_ranges"]["buckets"]
            ],
            "price_stats": resp["aggregations"]["price_stats"],
        },
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
    })


@app.route("/autocomplete", methods=["GET"])
def autocomplete():
    """Suggest products as the user types.

    Query params:
      q — partial query (e.g. "lumi")
    """
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"suggestions": []})

    resp = es.search(
        index=ALIAS,
        body={
            "suggest": {
                "product-suggest": {
                    "prefix": q,
                    "completion": {
                        "field": "name_suggest",
                        "size": 8,
                        "skip_duplicates": True,
                        "fuzzy": {"fuzziness": "AUTO"},
                    },
                }
            },
            "_source": ["name", "sku", "price", "status"],
        },
    )

    options = resp["suggest"]["product-suggest"][0]["options"]
    return jsonify({
        "suggestions": [
            {
                "text": s["text"],
                "score": s["_score"],
                "product": s.get("_source", {}),
            }
            for s in options
        ]
    })


@app.route("/suggest", methods=["GET"])
def suggest():
    """'Did you mean' spelling corrections.

    Query params:
      q — potentially misspelled query (e.g. "mechancal keybord")
    """
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"suggestions": []})

    resp = es.search(
        index=ALIAS,
        body={
            "suggest": {
                "spelling": {
                    "text": q,
                    "phrase": {
                        "field": "name",
                        "size": 3,
                        "gram_size": 3,
                        "direct_generator": [
                            {"field": "name", "suggest_mode": "popular"}
                        ],
                    },
                }
            },
        },
    )

    options = resp["suggest"]["spelling"][0]["options"]
    return jsonify({
        "suggestions": [
            {"text": s["text"], "score": s["score"]}
            for s in options
        ]
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
