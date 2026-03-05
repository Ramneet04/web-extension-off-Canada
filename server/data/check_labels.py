import duckdb
con = duckdb.connect("data/off_canada.duckdb")
result = con.execute("""
    SELECT labels_en, COUNT(*) as count
    FROM products
    WHERE labels_en IS NOT NULL
    AND labels_en != ''
    GROUP BY labels_en
    ORDER BY count DESC
    LIMIT 20
""").fetchdf()
print(result)
con.close()