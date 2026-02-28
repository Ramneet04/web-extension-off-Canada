import requests
import json
import os

def fetch_canadian_products(pages=5):
    all_products = []
    
    for page in range(1, pages + 1):
        print(f"Fetching page {page} of {pages}...")
        
        try:
            response = requests.get(
                "https://world.openfoodfacts.org/cgi/search.pl",
                params={
                    "action": "process",
                    "tagtype_0": "countries",
                    "tag_contains_0": "contains",
                    "tag_0": "canada",
                    "json": 1,
                    "page_size": 200,
                    "page": page
                },
                timeout=30
            )
            
            data = response.json()
            products = data.get("products", [])
            
            if not products:
                print("No more products found")
                break
                
            all_products.extend(products)
            print(f"  Got {len(products)} products | Total so far: {len(all_products)}")
            
        except Exception as e:
            print(f"  Error on page {page}: {e}")
            continue
    
    os.makedirs("data", exist_ok=True)
    with open("data/raw_products.json", "w", encoding="utf-8") as f:
        json.dump(all_products, f, ensure_ascii=False)
    
    print(f"\nDone! Saved {len(all_products)} products to data/raw_products.json")
    return all_products

if __name__ == "__main__":
    fetch_canadian_products(pages=5)