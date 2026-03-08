from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
import duckdb

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
qdrant = QdrantClient('localhost', port=6333, timeout=30)
con = duckdb.connect('data/off_v2.duckdb', read_only=True)

vector = model.encode('healthy low sodium snack').tolist()
results = qdrant.query_points(collection_name='off_products', query=vector, limit=20).points
print(f"Qdrant returned {len(results)} results")

if results:
    codes = [r.payload['code'] for r in results]
    print("First 5 codes:", codes[:5])
    placeholders = ','.join(['?' for _ in codes])

    # Without filters
    df = con.execute(
        f"SELECT code, product_name, nutriscore_grade, sodium_100g FROM products WHERE code IN ({placeholders})",
        codes
    ).fetchdf()
    print(f"DuckDB matched (no filter): {len(df)} rows")
    print(df.head())

    # With nutriscore filter only
    df2 = con.execute(
        f"SELECT code, product_name, nutriscore_grade, sodium_100g FROM products WHERE code IN ({placeholders}) AND nutriscore_grade IN ('a','b') AND nutriscore_grade != 'unknown'",
        codes
    ).fetchdf()
    print(f"\nAfter nutriscore filter: {len(df2)} rows")

    # With sodium filter only
    df3 = con.execute(
        f"SELECT code, product_name, nutriscore_grade, sodium_100g FROM products WHERE code IN ({placeholders}) AND sodium_100g <= 0.12",
        codes
    ).fetchdf()
    print(f"After sodium filter: {len(df3)} rows")

    # With both
    df4 = con.execute(
        f"SELECT code, product_name, nutriscore_grade, sodium_100g FROM products WHERE code IN ({placeholders}) AND nutriscore_grade IN ('a','b') AND nutriscore_grade != 'unknown' AND sodium_100g <= 0.12",
        codes
    ).fetchdf()
    print(f"After both filters: {len(df4)} rows")

    # Check what nutriscore values exist
    print("\nNutriscore distribution in matched products:")
    print(con.execute(
        f"SELECT nutriscore_grade, COUNT(*) as cnt FROM products WHERE code IN ({placeholders}) GROUP BY nutriscore_grade",
        codes
    ).fetchdf())

    # Check sodium values
    print("\nSodium stats in matched products:")
    print(con.execute(
        f"SELECT MIN(sodium_100g), MAX(sodium_100g), AVG(sodium_100g) FROM products WHERE code IN ({placeholders})",
        codes
    ).fetchdf())
