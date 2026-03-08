import duckdb

con = duckdb.connect('data/off_v2.duckdb', read_only=True)

# Check the product that showed 0 cal (water - expected to be 0)
print("=== Water product (0 cal expected) ===")
print(con.execute("SELECT code, product_name, energy_kcal_100g, fat_100g, sugars_100g, proteins_100g, sodium_100g FROM products WHERE code = '3274080005003'").fetchdf().to_string())

# Check some random products with actual nutrition
print("\n=== Products with non-null energy ===")
print(con.execute("SELECT code, product_name, energy_kcal_100g, fat_100g, proteins_100g, sodium_100g FROM products WHERE energy_kcal_100g > 0 LIMIT 10").fetchdf().to_string())

# Check how many products have NULL nutrition
print("\n=== Nutrition data coverage ===")
total = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
has_kcal = con.execute("SELECT COUNT(*) FROM products WHERE energy_kcal_100g IS NOT NULL").fetchone()[0]
has_kcal_gt0 = con.execute("SELECT COUNT(*) FROM products WHERE energy_kcal_100g > 0").fetchone()[0]
null_kcal = con.execute("SELECT COUNT(*) FROM products WHERE energy_kcal_100g IS NULL").fetchone()[0]
zero_kcal = con.execute("SELECT COUNT(*) FROM products WHERE energy_kcal_100g = 0").fetchone()[0]
print(f"Total products: {total}")
print(f"Has energy_kcal: {has_kcal} ({100*has_kcal/total:.1f}%)")
print(f"Energy > 0: {has_kcal_gt0} ({100*has_kcal_gt0/total:.1f}%)")
print(f"Energy = NULL: {null_kcal} ({100*null_kcal/total:.1f}%)")
print(f"Energy = 0: {zero_kcal} ({100*zero_kcal/total:.1f}%)")

# Check the barcode product
print("\n=== Barcode 8992760221028 ===")
print(con.execute("SELECT code, product_name, energy_kcal_100g, fat_100g, proteins_100g, sodium_100g FROM products WHERE code = '8992760221028'").fetchdf().to_string())
