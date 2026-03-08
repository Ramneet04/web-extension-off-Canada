import duckdb

con = duckdb.connect("data/off_v2.duckdb")


print("Total products:", con.execute("SELECT COUNT(*) FROM products").fetchone()[0])


print("\nColumns:")
print(con.execute("DESCRIBE products").fetchdf().to_string())


print("\nSample:")
print(con.execute("""
    SELECT code, product_name, brands, primary_country, 
           nutriscore_grade, image_url
    FROM products 
    ORDER BY popularity_key DESC 
    LIMIT 5
""").fetchdf().to_string())

# Check image URLs look right
print("\nSample image URLs:")
print(con.execute("""
    SELECT image_url FROM products 
    WHERE image_url IS NOT NULL 
    LIMIT 5
""").fetchdf().to_string())

con.close()