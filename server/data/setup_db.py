import duckdb

def setup_database():
    print("Connecting to DuckDB...")
    con = duckdb.connect("data/off_canada.duckdb")

    print("Loading products from TSV...")
    con.execute("DROP TABLE IF EXISTS products")

    con.execute("""
        CREATE TABLE products AS
        SELECT
            code,
            product_name,
            brands,
            categories_en,
            ingredients_text,
            nutrition_grade_fr AS nutriscore_grade,
            labels_en,
            countries_en,
            image_url,
            TRY_CAST(energy_100g AS FLOAT) as energy_100g,
            TRY_CAST(fat_100g AS FLOAT) as fat_100g,
            TRY_CAST(sugars_100g AS FLOAT) as sugars_100g,
            TRY_CAST(sodium_100g AS FLOAT) as sodium_100g,
            TRY_CAST(proteins_100g AS FLOAT) as proteins_100g,
            TRY_CAST(fiber_100g AS FLOAT) as fiber_100g,
            url
        FROM read_csv_auto(
            'data/en.openfoodfacts.org.products.tsv',
            delim='\t',
            ignore_errors=True,
            strict_mode=false
        )
        WHERE (
            countries_en ILIKE '%canada%'
            OR countries_en ILIKE '%united states%'
            OR countries_en ILIKE '%mexico%'
            OR countries_en ILIKE '%united kingdom%'
            OR countries_en ILIKE '%france%'
            OR countries_en ILIKE '%germany%'
        )
        AND product_name IS NOT NULL
        AND product_name != ''
        AND ingredients_text IS NOT NULL
        AND sodium_100g IS NOT NULL
        AND nutriscore_grade IS NOT NULL
        ORDER BY 
            CASE WHEN image_url IS NOT NULL THEN 0 ELSE 1 END
        LIMIT 50000
    """)

    count = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    print(f"Total products loaded: {count}")

    sample = con.execute("""
        SELECT code, product_name, brands, nutriscore_grade, sodium_100g
        FROM products
        LIMIT 5
    """).fetchdf()

    print("\nSample:")
    print(sample)

    con.close()
    print("\nDatabase ready!")

if __name__ == "__main__":
    setup_database()