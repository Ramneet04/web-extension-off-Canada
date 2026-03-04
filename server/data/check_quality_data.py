import duckdb

con = duckdb.connect("data/off_canada.duckdb")

result = con.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(nutriscore_grade) as has_nutriscore,
        COUNT(ingredients_text) as has_ingredients,
        COUNT(image_url) as has_image,
        COUNT(sodium_100g) as has_sodium,
        COUNT(categories_en) as has_categories
    FROM products
    WHERE product_name != ''
""").fetchdf()

print(result)