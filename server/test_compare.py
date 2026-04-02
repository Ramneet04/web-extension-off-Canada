import requests, json

d = r.json()

print(f"Type: {d['type']}, Total: {d['total']}")
print(f"Explanation: {d['explanation']}\n")

for p in d['results']:
    n = p['nutrition']
    print(f"{p['product_name']} ({p['brands']})")
    print(f"  energy_kcal: {n['energy_kcal']}")
    print(f"  fat:         {n['fat']}")
    print(f"  sugars:      {n['sugars']}")
    print(f"  proteins:    {n['proteins']}")
    print(f"  sodium:      {n['sodium']}")
    print()
