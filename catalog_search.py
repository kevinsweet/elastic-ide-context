"""
Catalog search API powered by Elasticsearch.

Provides product search with fuzzy matching, faceted navigation,
autocomplete, geo-distance filtering, and merchandising boosts
across millions of SKUs.

Docs: https://www.elastic.co/docs/solutions/search
"""

from elasticsearch import Elasticsearch, helpers
from flask import Flask, request, jsonify

# --- Connection -----------------------------------------------------------
# Cloud: Elasticsearch(cloud_id="deployment:...", api_key="your-api-key")
# Self-managed: Elasticsearch("http://localhost:9200")
es = Elasticsearch(cloud_id="YOUR_CLOUD_ID", api_key="YOUR_API_KEY")

INDEX = "products"

# --- Index Mapping --------------------------------------------------------

MAPPING = {
    "settings": {
        "number_of_replicas": 1,
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
                    "synonyms": [
                        "boots, shoes => boots",
                        "hiking, trekking, trail => hiking",
                        "jacket, coat, parka => jacket",
                        "waterproof, water-resistant => waterproof",
                    ],
                },
            },
        },
    },
    "mappings": {
        "properties": {
            "product_id": {"type": "keyword"},
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
            "description": {"type": "text", "analyzer": "synonym_analyzer"},
            "category": {"type": "keyword"},
            "price": {"type": "float"},
            "stock_level": {"type": "integer"},
            "tags": {"type": "keyword"},
            "location": {"type": "geo_point"},
            "name_suggest": {
                "type": "completion",
                "analyzer": "simple",
            },
        },
    },
}


def create_index():
    """Create the products index. Safe to call repeatedly — skips if it exists."""
    if not es.indices.exists(index=INDEX):
        es.indices.create(index=INDEX, body=MAPPING)
        print(f"Created index '{INDEX}'")
    else:
        print(f"Index '{INDEX}' already exists")


# --- Ingestion ------------------------------------------------------------


def index_products(products: list[dict]) -> tuple[int, list]:
    """
    Bulk-index a list of product dicts.

    Uses product_id as the document _id so re-indexing updates in place.
    For catalogs >100K products, call this in batches of 1,000–5,000.
    """
    actions = []
    for product in products:
        doc = dict(product)
        doc["name_suggest"] = {
            "input": [doc.get("name", ""), *doc.get("tags", [])],
            "weight": max(1, doc.get("stock_level", 1)),
        }
        actions.append({
            "_index": INDEX,
            "_id": doc.get("product_id"),
            "_source": doc,
        })

    success, errors = helpers.bulk(
        es, actions, raise_on_error=False, raise_on_exception=False
    )
    return success, errors


# --- Flask API ------------------------------------------------------------

app = Flask(__name__)


@app.route("/search", methods=["GET"])
def product_search():
    """
    Full product search with filters, facets, geo-distance, and sorting.

    Query params:
        q           — search text (fuzzy multi-match across name, description, tags)
        category    — exact category filter (repeatable)
        tag         — exact tag filter (repeatable)
        min_price   — minimum price
        max_price   — maximum price
        in_stock    — if "true", only stock_level > 0 (default: true)
        lat / lon / distance — geo-distance filter (e.g. lat=48.85&lon=2.35&distance=50km)
        sort        — relevance | price_asc | price_desc | newest | distance
        page        — page number (1-based)
        size        — results per page (default 20, max 100)
    """
    q = request.args.get("q", "")
    categories = request.args.getlist("category")
    tags = request.args.getlist("tag")
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    in_stock = request.args.get("in_stock", "true").lower() == "true"
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    distance = request.args.get("distance", "50km")
    sort_by = request.args.get("sort", "relevance")
    page = request.args.get("page", 1, type=int)
    size = min(request.args.get("size", 20, type=int), 100)

    # --- Build query ---
    must = []
    if q:
        must.append({
            "multi_match": {
                "query": q,
                "fields": ["name^3", "description", "tags^2"],
                "type": "best_fields",
                "fuzziness": "AUTO",
            }
        })

    filters = []
    if in_stock:
        filters.append({"range": {"stock_level": {"gt": 0}}})
    for cat in categories:
        filters.append({"term": {"category": cat}})
    for tag in tags:
        filters.append({"term": {"tags": tag}})
    if min_price is not None:
        filters.append({"range": {"price": {"gte": min_price}}})
    if max_price is not None:
        filters.append({"range": {"price": {"lte": max_price}}})
    if lat is not None and lon is not None:
        filters.append({
            "geo_distance": {
                "distance": distance,
                "location": {"lat": lat, "lon": lon},
            }
        })

    # --- Sorting ---
    sort_options = {
        "relevance": [{"_score": "desc"}, {"stock_level": "desc"}],
        "price_asc": [{"price": "asc"}],
        "price_desc": [{"price": "desc"}],
        "newest": [{"_score": "desc"}],
    }
    sort = sort_options.get(sort_by, sort_options["relevance"])

    if sort_by == "distance" and lat is not None and lon is not None:
        sort = [{
            "_geo_distance": {
                "location": {"lat": lat, "lon": lon},
                "order": "asc",
                "unit": "km",
            }
        }]

    # --- Assemble request body ---
    body = {
        "query": {
            "bool": {
                "must": must if must else [{"match_all": {}}],
                "filter": filters,
            }
        },
        "from": (page - 1) * size,
        "size": size,
        "sort": sort,
        "highlight": {
            "fields": {
                "name": {},
                "description": {"fragment_size": 120, "number_of_fragments": 2},
            }
        },
        "aggs": {
            "categories": {"terms": {"field": "category", "size": 30}},
            "tags": {"terms": {"field": "tags", "size": 30}},
            "price_ranges": {
                "range": {
                    "field": "price",
                    "ranges": [
                        {"to": 25, "key": "Under $25"},
                        {"from": 25, "to": 50, "key": "$25–$50"},
                        {"from": 50, "to": 100, "key": "$50–$100"},
                        {"from": 100, "to": 200, "key": "$100–$200"},
                        {"from": 200, "key": "$200+"},
                    ],
                }
            },
            "price_stats": {"stats": {"field": "price"}},
            "stock_status": {
                "range": {
                    "field": "stock_level",
                    "ranges": [
                        {"from": 1, "key": "In Stock"},
                        {"to": 1, "key": "Out of Stock"},
                    ],
                }
            },
        },
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
        } if q else {},
    }

    resp = es.search(index=INDEX, body=body)

    hits = resp["hits"]["hits"]
    total = resp["hits"]["total"]["value"]

    suggestions = []
    if q and "suggest" in resp and "spelling" in resp["suggest"]:
        for option in resp["suggest"]["spelling"][0].get("options", []):
            suggestions.append(option["text"])

    return jsonify({
        "results": [
            {
                "product": h["_source"],
                "score": h["_score"],
                "highlight": h.get("highlight", {}),
                "sort": h.get("sort"),
            }
            for h in hits
        ],
        "total": total,
        "facets": {
            "categories": [
                {"key": b["key"], "count": b["doc_count"]}
                for b in resp["aggregations"]["categories"]["buckets"]
            ],
            "tags": [
                {"key": b["key"], "count": b["doc_count"]}
                for b in resp["aggregations"]["tags"]["buckets"]
            ],
            "price_ranges": [
                {"key": b["key"], "count": b["doc_count"]}
                for b in resp["aggregations"]["price_ranges"]["buckets"]
            ],
            "price_stats": resp["aggregations"]["price_stats"],
            "stock_status": [
                {"key": b["key"], "count": b["doc_count"]}
                for b in resp["aggregations"]["stock_status"]["buckets"]
            ],
        },
        "suggestions": suggestions,
        "page": page,
        "pages": (total + size - 1) // size,
    })


@app.route("/autocomplete", methods=["GET"])
def autocomplete():
    """
    Fast typeahead: returns product name suggestions as the user types.

    Query params:
        q — prefix text (min 2 chars for useful results)
    """
    q = request.args.get("q", "")

    resp = es.search(
        index=INDEX,
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
            "_source": ["name", "product_id", "price", "category"],
        },
    )

    options = resp["suggest"]["product-suggest"][0]["options"]
    return jsonify({
        "suggestions": [
            {
                "text": s["text"],
                "product_id": s["_source"].get("product_id"),
                "price": s["_source"].get("price"),
                "category": s["_source"].get("category"),
            }
            for s in options
        ]
    })


# --- Entrypoint -----------------------------------------------------------

if __name__ == "__main__":
    create_index()
    print(f"Index '{INDEX}' is ready.")

    # Example: index a single product
    sample = {
        "product_id": "HB-900X",
        "name": "Pro-Hiker Leather Boots",
        "description": "Waterproof brown leather boots with reinforced soles for rugged terrain.",
        "category": ["Footwear", "Outdoor"],
        "price": 149.99,
        "stock_level": 42,
        "tags": ["waterproof", "leather", "hiking"],
        "location": {"lat": 48.8566, "lon": 2.3522},
    }
    success, errors = index_products([sample])
    print(f"Indexed {success} product(s)")

    app.run(debug=True, port=5000)
