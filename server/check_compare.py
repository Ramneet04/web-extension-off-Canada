import duckdb, json

con = duckdb.connect('data/off_v2.duckdb', read_only=True)

# Search for Coca Cola
print("=== Coca Cola ===")
df = con.execute("""
    SELECT code, product_name, brands, energy_kcal_100g, fat_100g, sugars_100g, proteins_100g, sodium_100g
    FROM products
    WHERE product_name ILIKE '%coca cola%' OR brands ILIKE '%coca cola%'
    ORDER BY popularity_key DESC
    LIMIT 5
""").fetchdf()
print(df.to_string())

# Search for Pepsi
print("\n=== Pepsi ===")
df2 = con.execute("""
    SELECT code, product_name, brands, energy_kcal_100g, fat_100g, sugars_100g, proteins_100g, sodium_100g
    FROM products
    WHERE product_name ILIKE '%pepsi%' OR brands ILIKE '%pepsi%'
    ORDER BY popularity_key DESC
    LIMIT 5
""").fetchdf()
print(df2.to_string())

# Search for Coke
print("\n=== Coke ===")
df3 = con.execute("""
    SELECT code, product_name, brands, energy_kcal_100g, fat_100g, sugars_100g, proteins_100g, sodium_100g
    FROM products
    WHERE product_name ILIKE '%coke%' OR brands ILIKE '%coke%'
    ORDER BY popularity_key DESC
    LIMIT 5
""").fetchdf()
print(df3.to_string())
