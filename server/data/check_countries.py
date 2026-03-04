import duckdb

con = duckdb.connect()

result = con.execute("""
    SELECT countries_en, COUNT(*) as count
    FROM read_csv_auto(
        'data/en.openfoodfacts.org.products.tsv',
        delim='\t',
        ignore_errors=True,
        strict_mode=false
    )
    WHERE countries_en ILIKE '%canada%'
    OR countries_en ILIKE '%canadian%'
    GROUP BY countries_en
    ORDER BY count DESC
    LIMIT 20
""").fetchdf()

print(result)