from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import duckdb
import uuid

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
qdrant = QdrantClient("localhost", port=6333)

def build_product_text(row: dict) -> str:
    parts = []
    if row.get("product_name"): parts.append(f"Product: {row['product_name']}")
    if row.get("brands"): parts.append(f"Brand: {row['brands']}")
    if row.get("categories_en"): parts.append(f"Category: {row['categories_en']}")
    if row.get("ingredients_text"): parts.append(f"Ingredients: {str(row['ingredients_text'])[:300]}")
    if row.get("labels_en"): parts.append(f"Labels: {row['labels_en']}")
    if row.get("nutriscore_grade"): parts.append(f"Nutriscore: {row['nutriscore_grade']}")
    return " | ".join(parts)

def index_products():
    print("Loading products from DuckDB...")
    con = duckdb.connect("data/off_canada.duckdb")
    products = con.execute("SELECT * FROM products").fetchdf()
    products = products.fillna("")
    con.close()
    print(f"Loaded {len(products)} products")

    # Create Qdrant collection
    qdrant.recreate_collection(
        collection_name="off_products",
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )
    print("Qdrant collection created")

    # Build texts
    texts = [build_product_text(row.to_dict()) for _, row in products.iterrows()]

    print("Generating embeddings... this will take 15-20 minutes for 50k products")
    
    batch_size = 64
    total = len(products)

    for i in range(0, total, batch_size):
        batch_texts = texts[i:i+batch_size]
        batch_products = products.iloc[i:i+batch_size]

        # Generate embeddings for this batch
        embeddings = model.encode(batch_texts, show_progress_bar=False)

        # Create points
        points = [
            PointStruct(
                id=i + j,
                vector=embeddings[j].tolist(),
                payload=batch_products.iloc[j].to_dict()
            )
            for j in range(len(batch_products))
        ]

        # Upload to Qdrant
        qdrant.upsert(collection_name="off_products", points=points)

        # Progress update every 1000 products
        if (i + batch_size) % 1000 == 0:
            print(f"Progress: {min(i+batch_size, total)}/{total} products indexed")

    print(f"\nDone! {total} products indexed into Qdrant")

if __name__ == "__main__":
    index_products()