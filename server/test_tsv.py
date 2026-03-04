import duckdb

con = duckdb.connect()
result = con.execute("""
    SELECT *
    FROM read_csv_auto('data/en.openfoodfacts.org.products.tsv',
        delim='\t',
        ignore_errors=True)
    LIMIT 1
""").fetchdf()

print('Total columns:', len(result.columns))
print('Columns:', list(result.columns))