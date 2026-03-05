from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny, MatchValue, Range, MatchText
from sentence_transformers import SentenceTransformer
from api.query_parser import parse_query

print("Loading embedding model...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
qdrant = QdrantClient("localhost", port=6333)

def build_filter(filters: dict):
    conditions = []


    if filters.get("nutriscore_grade"):
        conditions.append(FieldCondition(
            key="nutriscore_grade",
            match=MatchAny(any=filters["nutriscore_grade"])
        ))

    
    if filters.get("max_sodium_100g") is not None:
        conditions.append(FieldCondition(
            key="sodium_100g",
            range=Range(lte=filters["max_sodium_100g"])
        ))

    
    if filters.get("max_sugars_100g") is not None:
        conditions.append(FieldCondition(
            key="sugars_100g",
            range=Range(lte=filters["max_sugars_100g"])
        ))

    
    if filters.get("max_fat_100g") is not None:
        conditions.append(FieldCondition(
            key="fat_100g",
            range=Range(lte=filters["max_fat_100g"])
        ))


    if filters.get("min_proteins_100g") is not None:
        conditions.append(FieldCondition(
            key="proteins_100g",
            range=Range(gte=filters["min_proteins_100g"])
        ))

    if filters.get("min_fiber_100g") is not None:
        conditions.append(FieldCondition(
            key="fiber_100g",
            range=Range(gte=filters["min_fiber_100g"])
        ))
    if filters.get("label"):
        label_value = filters["label"]
        if "," in str(label_value):
            label_value = label_value.split(",")[0].strip()
        conditions.append(FieldCondition(
            key="labels_en",
            match=MatchText(text=label_value)
        ))

    return Filter(must=conditions) if conditions else None

def search_products(query: str, limit: int = 20) -> dict:

    print(f"Parsing query: {query}")
    parsed = parse_query(query)
    print(f"Parsed: {parsed}")

    vector = model.encode(parsed["semantic_query"]).tolist()

    qdrant_filter = build_filter(parsed.get("filters", {}))
    results = qdrant.query_points(
    collection_name="off_products",
    query=vector,
    query_filter=qdrant_filter,
    limit=limit
    ).points

    
    products = []
    for r in results:
        p = r.payload
        products.append({
            "code": p.get("code"),
            "product_name": p.get("product_name"),
            "brands": p.get("brands"),
            "nutriscore_grade": p.get("nutriscore_grade"),
            "nova_group": p.get("nova_group"),
            "labels_en": p.get("labels_en"),
            "image_url": p.get("image_url"),
            "sodium_100g": p.get("sodium_100g"),
            "sugars_100g": p.get("sugars_100g"),
            "fat_100g": p.get("fat_100g"),
            "proteins_100g": p.get("proteins_100g"),
            "url": p.get("url"),
            "score": r.score
        })

    return {
        "explanation": parsed["explanation"],
        "total": len(products),
        "results": products
    }

if __name__ == "__main__":
    import json
    result = search_products("healthy low sodium vegan snacks")
    print(f"\nExplanation: {result['explanation']}")
    print(f"Total results: {result['total']}")
    print("\nTop 3 results:")
    for p in result["results"][:3]:
        print(f"  - {p['product_name']} | {p['brands']} | nutriscore: {p['nutriscore_grade']} | sodium: {p['sodium_100g']}")