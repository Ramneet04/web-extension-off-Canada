"""
Step 1: Run this FIRST to inspect the parquet file structure.
Usage: python inspect_parquet.py
"""

import duckdb

con = duckdb.connect()

print("=" * 60)
print("INSPECTING PARQUET FILE: data/0000.parquet")
print("=" * 60)

try:
    total = con.execute("""
        SELECT COUNT(*) FROM read_parquet('data/0000.parquet')
    """).fetchone()[0]
    print(f"\nTotal rows: {total:,}")
except Exception as e:
    print(f"Error reading file: {e}")
    exit(1)

result = con.execute("""
    DESCRIBE SELECT * FROM read_parquet('data/0000.parquet')
""").fetchdf()

print(f"\nTotal columns: {len(result)}")
print("\nAll columns + types:")
for _, row in result.iterrows():
    print(f"  {row['column_name']:<45} {row['column_type']}")

raw = con.execute("""
    SELECT * FROM read_parquet('data/0000.parquet') LIMIT 1
""").fetchdf()

target_columns = [
    "code", "product_name", "brands", "generic_name", "lang",
    "nutriscore_grade", "nutriscore_score",
    "nova_group", "nova_groups_tags", "nova_groups",
    "ecoscore_grade", "ecoscore_score",
    "ingredients_text", "ingredients_analysis_tags",
    "ingredients_n", "additives_n", "additives_tags",
    "with_sweeteners", "with_non_nutritive_sweeteners",
    "ingredients_from_palm_oil_n",
    "categories_tags", "food_groups_tags",
    "labels_tags", "labels",
    "allergens_tags", "traces_tags",
    "countries_tags",
    "completeness", "popularity_key", "unique_scans_n",
    "nutriments", "images", "link",
]

print("\n--- TARGET COLUMN CHECK ---")
available = []
missing = []
for col in target_columns:
    if col in raw.columns:
        available.append(col)
        print(f"  ✅  {col}")
    else:
        missing.append(col)
        print(f"  ❌  {col}  (MISSING)")

print(f"\nAvailable: {len(available)}/{len(target_columns)}")
print(f"Missing:   {len(missing)}/{len(target_columns)}")

if "countries_tags" in raw.columns:
    print("\n--- SAMPLE countries_tags (10 rows) ---")
    s = con.execute("""
        SELECT countries_tags FROM read_parquet('data/0000.parquet')
        WHERE countries_tags IS NOT NULL LIMIT 10
    """).fetchdf()
    for v in s["countries_tags"]:
        print(" ", v)

if "nutriments" in raw.columns:
    print("\n--- SAMPLE nutriments (3 rows) ---")
    s = con.execute("""
        SELECT nutriments FROM read_parquet('data/0000.parquet')
        WHERE nutriments IS NOT NULL LIMIT 3
    """).fetchdf()
    for v in s["nutriments"]:
        print(" ", str(v)[:300])

if "product_name" in raw.columns:
    print("\n--- SAMPLE product_name (5 rows) ---")
    s = con.execute("""
        SELECT product_name FROM read_parquet('data/0000.parquet')
        WHERE product_name IS NOT NULL LIMIT 5
    """).fetchdf()
    for v in s["product_name"]:
        print(" ", v)

if "ingredients_text" in raw.columns:
    print("\n--- SAMPLE ingredients_text (3 rows) ---")
    s = con.execute("""
        SELECT ingredients_text FROM read_parquet('data/0000.parquet')
        WHERE ingredients_text IS NOT NULL LIMIT 3
    """).fetchdf()
    for v in s["ingredients_text"]:
        print(" ", str(v)[:200])

print("\n--- COUNTRY DISTRIBUTION (top 30) ---")
if "countries_tags" in raw.columns:
    try:
        s = con.execute("""
            SELECT
                UNNEST(countries_tags) AS country,
                COUNT(*) AS product_count
            FROM read_parquet('data/0000.parquet')
            WHERE countries_tags IS NOT NULL
            GROUP BY country
            ORDER BY product_count DESC
            LIMIT 30
        """).fetchdf()
        print(s.to_string(index=False))

        print("\n--- OUR TARGET COUNTRIES ---")
        targets = ['en:canada', 'en:france', 'en:india', 'en:united-states', 'en:united-kingdom', 'en:germany']
        for t in targets:
            try:
                count = con.execute(f"""
                    SELECT COUNT(*) FROM read_parquet('data/0000.parquet')
                    WHERE list_contains(countries_tags, '{t}')
                """).fetchone()[0]
                print(f"  {t:<30} {count:>10,} products")
            except Exception as e:
                print(f"  {t:<30} ERROR: {e}")
    except Exception as e:
        print(f"  UNNEST failed ({e}), trying string match...")
        for t in ['canada', 'france', 'india', 'united-states', 'united-kingdom']:
            count = con.execute(f"""
                SELECT COUNT(*) FROM read_parquet('data/0000.parquet')
                WHERE CAST(countries_tags AS VARCHAR) ILIKE '%{t}%'
            """).fetchone()[0]
            print(f"  {t:<30} {count:>10,} products")
else:
    print("  countries_tags column not found!")

con.close()
print("\n✅ Inspection complete! Share this output and we'll build setup_db2.py exactly right.")