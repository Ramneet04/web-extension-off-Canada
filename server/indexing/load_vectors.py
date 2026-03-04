from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import json

print("Loading vectors from file...")
with open("data/vectors.json", "r") as f:
    all_vectors = json.load(f)

print(f"Loaded {len(all_vectors)} vectors")

qdrant = QdrantClient("localhost", port=6333)

qdrant.recreate_collection(
    collection_name="off_products",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
)

print("Collection created")

# Upload in batches
batch_size = 500
total = len(all_vectors)

for i in range(0, total, batch_size):
    batch = all_vectors[i:i+batch_size]
    points = [
        PointStruct(
            id=v["id"],
            vector=v["vector"],
            payload=v["payload"]
        )
        for v in batch
    ]
    qdrant.upsert(collection_name="off_products", points=points)
    print(f"Uploaded {min(i+batch_size, total)}/{total}")

print("Done! All vectors loaded into Qdrant")