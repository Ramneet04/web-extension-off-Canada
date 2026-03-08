"""
upload_to_qdrant.py — Upload embeddings to local Qdrant

Steps before running:
  1. Start Qdrant:
     docker run -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
  2. Put embeddings.npz in your data/ folder
  3. Run: python upload_to_qdrant.py

Usage: python upload_to_qdrant.py
"""

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import time

EMBEDDINGS_PATH = "data/embeddings.npz"
COLLECTION_NAME = "off_products"
QDRANT_HOST     = "localhost"
QDRANT_PORT     = 6333
BATCH_SIZE      = 100

def upload():
    start = time.time()
    print("=" * 50)
    print("UPLOADING EMBEDDINGS TO QDRANT")
    print("=" * 50)

    # ----------------------------------------------------------------
    # Load embeddings.npz
    # ----------------------------------------------------------------
    print(f"\nLoading {EMBEDDINGS_PATH}...")
    data       = np.load(EMBEDDINGS_PATH, allow_pickle=True)
    codes      = data['codes'].tolist()
    countries  = data['countries'].tolist()
    embeddings = data['embeddings']

    total = len(codes)
    dims  = embeddings.shape[1]
    print(f"  Products:   {total:,}")
    print(f"  Dimensions: {dims}")

    # ----------------------------------------------------------------
    # Connect to Qdrant
    # ----------------------------------------------------------------
    print(f"\nConnecting to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}...")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=60)
    print("  ✅ Connected")

    # ----------------------------------------------------------------
    # Create collection
    # ----------------------------------------------------------------
    print(f"\nCreating collection '{COLLECTION_NAME}'...")
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=dims,
            distance=Distance.COSINE
        )
    )
    print("  ✅ Collection created")

    # ----------------------------------------------------------------
    # Upload in batches
    # ----------------------------------------------------------------
    print(f"\nUploading {total:,} vectors in batches of {BATCH_SIZE}...")

    for i in range(0, total, BATCH_SIZE):
        batch_codes      = codes[i:i+BATCH_SIZE]
        batch_countries  = countries[i:i+BATCH_SIZE]
        batch_embeddings = embeddings[i:i+BATCH_SIZE]

        points = [
            PointStruct(
                id=i + j,
                vector=batch_embeddings[j].tolist(),
                payload={
                    "code":            batch_codes[j],
                    "primary_country": batch_countries[j],
                }
            )
            for j in range(len(batch_codes))
        ]

        client.upsert(collection_name=COLLECTION_NAME, points=points)

        if (i // BATCH_SIZE) % 10 == 0:
            elapsed  = time.time() - start
            progress = (i + BATCH_SIZE) / total
            eta      = (elapsed / progress - elapsed) if progress > 0 else 0
            print(f"  {min(i+BATCH_SIZE, total):>7,} / {total:,}  ({progress*100:.1f}%)  ETA: {eta/60:.1f} min")

    elapsed = time.time() - start
    print(f"\n✅ Upload complete in {elapsed:.0f}s")

    # ----------------------------------------------------------------
    # Verify
    # ----------------------------------------------------------------
    info = client.get_collection(COLLECTION_NAME)
    print(f"\nCollection info:")
    print(f"  Vectors count: {info.vectors_count:,}")
    print(f"  Points count:  {info.points_count:,}")
    print(f"  Status:        {info.status}")

    # Test search
    print("\nTest search...")
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=embeddings[0].tolist(),
        limit=3
    )
    print("  Top 3 similar to first product:")
    for r in results:
        print(f"    score={r.score:.4f}  code={r.payload['code']}  country={r.payload['primary_country']}")

    print(f"\n✅ Qdrant ready!")

if __name__ == "__main__":
    upload()