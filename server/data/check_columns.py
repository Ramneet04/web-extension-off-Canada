import duckdb

con = duckdb.connect("data/off_v2.duckdb")

# All columns with types
print("=" * 50)
print("COLUMNS")
print("=" * 50)
cols = con.execute("DESCRIBE products").fetchdf()
for _, r in cols.iterrows():
    print(f"  {r['column_name']:<35} {r['column_type']}")

# Total count
total = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
print(f"\nTotal products: {total:,}")

# Sample row - see actual values
print("\n" + "=" * 50)
print("SAMPLE ROW (all columns)")
print("=" * 50)
row = con.execute("""
    SELECT * FROM products 
    WHERE product_name IS NOT NULL
      AND sodium_100g IS NOT NULL
      AND vitamins_tags IS NOT NULL
    LIMIT 1
""").fetchdf()

for col in row.columns:
    print(f"  {col:<35} {row[col].iloc[0]}")

# Check fill rates for nutrition columns
print("\n" + "=" * 50)
print("NUTRITION FILL RATES")
print("=" * 50)
nutrition_cols = [
    'energy_kcal_100g', 'fat_100g', 'saturated_fat_100g',
    'carbohydrates_100g', 'sugars_100g', 'fiber_100g',
    'proteins_100g', 'salt_100g', 'sodium_100g'
]
for col in nutrition_cols:
    count = con.execute(f"SELECT COUNT(*) FROM products WHERE {col} IS NOT NULL").fetchone()[0]
    print(f"  {col:<35} {count:>8,} / {total:,}  ({count/total*100:.1f}%)")

# Check fill rates for tag columns
print("\n" + "=" * 50)
print("TAG COLUMN FILL RATES")
print("=" * 50)
tag_cols = [
    'vitamins_tags', 'minerals_tags', 'labels_tags',
    'allergens_tags', 'nova_group', 'ecoscore_grade',
    'nutriscore_grade', 'categories_tags', 'food_groups_tags'
]
for col in tag_cols:
    count = con.execute(f"""
        SELECT COUNT(*) FROM products 
        WHERE {col} IS NOT NULL 
          AND CAST({col} AS VARCHAR) NOT IN ('', '[]', 'unknown')
    """).fetchone()[0]
    print(f"  {col:<35} {count:>8,} / {total:,}  ({count/total*100:.1f}%)")

# Sample nutrition values
print("\n" + "=" * 50)
print("SAMPLE NUTRITION VALUES")
print("=" * 50)
sample = con.execute("""
    SELECT product_name, sodium_100g, proteins_100g, 
           sugars_100g, fat_100g, nova_group, 
           nutriscore_grade, vitamins_tags, minerals_tags
    FROM products
    WHERE sodium_100g IS NOT NULL
      AND proteins_100g IS NOT NULL
    LIMIT 5
""").fetchdf()
print(sample.to_string(index=False))

con.close()