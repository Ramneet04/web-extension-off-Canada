from api.search2 import compare_by_names
import duckdb, json

con = duckdb.connect('data/off_v2.duckdb', read_only=True)
result = compare_by_names('compare coke and pepsi', con)

for p in result['results']:
    print(f"\n{p['product_name']} ({p['brands']})")
    print(f"  Energy: {p['nutrition']['energy_kcal']} kcal")
    print(f"  Fat: {p['nutrition']['fat']}g")
    print(f"  Sugars: {p['nutrition']['sugars']}g")
    print(f"  Proteins: {p['nutrition']['proteins']}g")
    print(f"  Sodium: {p['nutrition']['sodium']}g")
