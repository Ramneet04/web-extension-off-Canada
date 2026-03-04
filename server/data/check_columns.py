import duckdb

con = duckdb.connect("data/off_canada.duckdb")
result = con.execute("SELECT * FROM products LIMIT 1").fetchdf()
print("All columns:", list(result.columns))
print("\nValues:")
for col in result.columns:
    print(f"{col}: {result.iloc[0][col]}")
con.close()