from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from api.query_parser2 import parse_query
import duckdb
import re
import math
import pandas as pd

def clean(val):
    if val is None:
        return None
    try:
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return None
    except Exception:
        pass
    return val

print("Loading embedding model...")
model  = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
qdrant = QdrantClient("localhost", port=6333, timeout=30)
print("✅ Model + Qdrant ready")

PRODUCT_FIELDS = """
    code,
    product_name,
    product_name_en,
    product_name_fr,
    brands,
    primary_country,
    lang,
    image_url,
    nutriscore_grade,
    nutriscore_score,
    nova_group,
    ecoscore_grade,
    categories_tags,
    labels_tags,
    allergens_tags,
    ingredients_text,
    energy_kcal_100g,
    fat_100g,
    saturated_fat_100g,
    carbohydrates_100g,
    sugars_100g,
    fiber_100g,
    proteins_100g,
    salt_100g,
    sodium_100g,
    product_quantity,
    serving_size,
    link,
    popularity_key,
    unique_scans_n
"""

def format_product(row: dict) -> dict:
    row = {k: clean(v) for k, v in row.items()}
    image_url = row.get("image_url")
    if image_url:
        image_url = f"https://images.openfoodfacts.org/images/products/{image_url}"
    return {
        "code":             row.get("code"),
        "product_name":     row.get("product_name"),
        "product_name_en":  row.get("product_name_en"),
        "product_name_fr":  row.get("product_name_fr"),
        "brands":           row.get("brands"),
        "primary_country":  row.get("primary_country"),
        "image_url":        image_url,
        "nutriscore_grade": row.get("nutriscore_grade"),
        "nutriscore_score": clean(row.get("nutriscore_score")),
        "nova_group":       clean(row.get("nova_group")),
        "ecoscore_grade":   row.get("ecoscore_grade"),
        "categories_tags":  row.get("categories_tags"),
        "labels_tags":      row.get("labels_tags"),
        "allergens_tags":   row.get("allergens_tags"),
        "ingredients_text": row.get("ingredients_text"),
        "nutrition": {
            "energy_kcal":   clean(row.get("energy_kcal_100g")),
            "fat":           clean(row.get("fat_100g")),
            "saturated_fat": clean(row.get("saturated_fat_100g")),
            "carbohydrates": clean(row.get("carbohydrates_100g")),
            "sugars":        clean(row.get("sugars_100g")),
            "fiber":         clean(row.get("fiber_100g")),
            "proteins":      clean(row.get("proteins_100g")),
            "salt":          clean(row.get("salt_100g")),
            "sodium":        clean(row.get("sodium_100g")),
        },
        "product_quantity": row.get("product_quantity"),
        "serving_size":     row.get("serving_size"),
        "link":             row.get("link"),
        "popularity_key":   clean(row.get("popularity_key")),
        "unique_scans_n":   clean(row.get("unique_scans_n")),
    }


def get_product_by_code(code: str, con: duckdb.DuckDBPyConnection) -> dict | None:
    result = con.execute(
        f"SELECT {PRODUCT_FIELDS} FROM products WHERE code = ?", [code]
    ).fetchdf()
    if result.empty:
        return None
    return format_product(result.to_dict("records")[0])


def get_similar_products(code: str, limit: int, con: duckdb.DuckDBPyConnection) -> dict:
    product = get_product_by_code(code, con)
    if not product:
        return {"explanation": "Product not found", "total": 0, "results": []}

    name    = product.get("product_name") or ""
    brands  = product.get("brands") or ""
    cats    = product.get("categories_tags") or ""
    labels  = product.get("labels_tags") or ""
    ns      = product.get("nutriscore_grade") or ""

    embed_text = f"{name} | {brands} | {cats} | {labels} | {ns}"
    vector     = model.encode(embed_text).tolist()

    qdrant_results = qdrant.query_points(
        collection_name="off_products",
        query=vector,
        limit=limit + 1
    ).points

    codes = [r.payload["code"] for r in qdrant_results if r.payload["code"] != code][:limit]

    if not codes:
        return {"explanation": "No similar products found", "total": 0, "results": []}

    placeholders = ",".join(["?" for _ in codes])
    df = con.execute(
        f"SELECT {PRODUCT_FIELDS} FROM products WHERE code IN ({placeholders})",
        codes
    ).fetchdf()

    products = [format_product(row) for row in df.to_dict("records")]
    return {
        "explanation": f"Products similar to {name}",
        "total":       len(products),
        "results":     products
    }


def build_duckdb_filter(filters: dict) -> tuple[str, list]:
    conditions = []
    params     = []

    if filters.get("nutriscore_grade"):
        placeholders = ",".join(["?" for _ in filters["nutriscore_grade"]])
        conditions.append(f"nutriscore_grade IN ({placeholders}) AND nutriscore_grade != 'unknown'")
        params.extend(filters["nutriscore_grade"])

    if filters.get("nova_group"):
        placeholders = ",".join(["?" for _ in filters["nova_group"]])
        conditions.append(f"nova_group IN ({placeholders})")
        params.extend(filters["nova_group"])

    if filters.get("max_sodium_100g") is not None:
        conditions.append("sodium_100g <= ?")
        params.append(filters["max_sodium_100g"])

    if filters.get("max_sugars_100g") is not None:
        conditions.append("sugars_100g <= ?")
        params.append(filters["max_sugars_100g"])

    if filters.get("max_fat_100g") is not None:
        conditions.append("fat_100g <= ?")
        params.append(filters["max_fat_100g"])

    if filters.get("min_proteins_100g") is not None:
        conditions.append("proteins_100g >= ?")
        params.append(filters["min_proteins_100g"])

    if filters.get("min_fiber_100g") is not None:
        conditions.append("fiber_100g >= ?")
        params.append(filters["min_fiber_100g"])

    if filters.get("max_energy_kcal_100g") is not None:
        conditions.append("energy_kcal_100g <= ?")
        params.append(filters["max_energy_kcal_100g"])

    if filters.get("label"):
        conditions.append("labels_tags ILIKE ?")
        params.append(f"%{filters['label']}%")

    if filters.get("country"):
        conditions.append("primary_country = ?")
        params.append(filters["country"])

    where = "AND " + " AND ".join(conditions) if conditions else ""
    return where, params


def extract_barcodes_from_query(query: str) -> list[str]:
    return re.findall(r'\b\d{8,14}\b', query)


def search_products(
    query: str,
    limit: int,
    con: duckdb.DuckDBPyConnection,
    offset: int = 0,
    country: str = None,
    filters: dict = None
) -> dict:
    barcodes = extract_barcodes_from_query(query)
    if barcodes:
        if len(barcodes) > 1:
            return compare_by_codes(barcodes, con)
        else:
            product = get_product_by_code(barcodes[0], con)
            if product:
                return {
                    "explanation": f"Found product with barcode {barcodes[0]}",
                    "total": 1,
                    "results": [product]
                }

    print(f"Parsing query: {query}")
    parsed = parse_query(query)

    # Merge parsed filters with any session filters passed in
    parsed_filters = parsed.get("filters", {}) or {}
    if filters:
        parsed_filters.update(filters)

    if country:
        parsed_filters["country"] = country

    print(f"Parsed: {parsed}")

    vector = model.encode(parsed["semantic_query"]).tolist()

    fetch_limit = min(max((limit + offset) * 50, 500), 2000)
    results = qdrant.query_points(
        collection_name="off_products",
        query=vector,
        limit=fetch_limit
    ).points

    if not results:
        return {"explanation": parsed["explanation"], "total": 0, "results": []}

    code_score   = {r.payload["code"]: r.score for r in results}
    codes        = list(code_score.keys())
    placeholders = ",".join(["?" for _ in codes])

    where_filter, params = build_duckdb_filter(parsed_filters)

    df = con.execute(
        f"SELECT {PRODUCT_FIELDS} FROM products WHERE code IN ({placeholders}) {where_filter}",
        codes + params
    ).fetchdf()

    if df.empty and where_filter:
        print("Qdrant pool too small for filters — falling back to DuckDB direct query")
        df = con.execute(
            f"SELECT {PRODUCT_FIELDS} FROM products WHERE 1=1 {where_filter} ORDER BY popularity_key DESC LIMIT ?",
            params + [limit]
        ).fetchdf()
        if df.empty:
            return {"explanation": parsed["explanation"], "total": 0, "results": []}
        df = df.where(df.notna(), other=None)
        df["score"] = 0.0

    df = df.where(df.notna(), other=None)
    if "score" not in df.columns:
        df["score"] = df["code"].map(code_score).fillna(0.0)
    df = df.sort_values("score", ascending=False)

    total_found = len(df)
    df = df.iloc[offset:offset + limit]

    products = []
    for row in df.to_dict("records"):
        p = format_product(row)
        p["score"] = round(float(row.get("score", 0)), 4)
        products.append(p)

    return {
        "explanation": parsed["explanation"],
        "total":       total_found,
        "returned":    len(products),
        "offset":      offset,
        "results":     products
    }


def compare_by_codes(codes: list[str], con: duckdb.DuckDBPyConnection) -> dict:
    products = []
    for code in codes:
        p = get_product_by_code(code, con)
        if p:
            products.append(p)
    return {
        "explanation": f"Comparing {len(products)} products",
        "total":       len(products),
        "results":     products
    }


def compare_by_names(query: str, con: duckdb.DuckDBPyConnection) -> dict:
    # Split on compare keywords to extract individual product names
    cleaned = re.sub(
        r'\b(compare|vs|versus|comparer|différence entre|difference between)\b',
        '|', query, flags=re.IGNORECASE
    )
    parts = [p.strip() for p in cleaned.split('|') if p.strip()]

    if len(parts) < 2:
        return {
            "explanation": "Could not extract product names to compare",
            "total":       0,
            "results":     []
        }

    products = []
    for name in parts:
        vector = model.encode(name).tolist()
        qdrant_results = qdrant.query_points(
            collection_name="off_products",
            query=vector,
            limit=1
        ).points
        if qdrant_results:
            code = qdrant_results[0].payload["code"]
            p = get_product_by_code(code, con)
            if p:
                products.append(p)

    return {
        "explanation": f"Comparing: {' vs '.join(parts)}",
        "total":       len(products),
        "results":     products
    }