from groq import Groq
import json
import os
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are an expert nutritionist and food search query parser for Open Food Facts Canada (ca.openfoodfacts.org) - a database of food products available in Canada.

Your job is to analyze a user's natural language food search query in English OR French and convert it into a structured JSON search object.

You must ALWAYS return valid JSON and NOTHING else. No explanation, no markdown, no code blocks. Just raw JSON.

OUTPUT FORMAT:
{
  "semantic_query": "optimized search phrase for vector similarity search",
  "filters": {
    "nutriscore_grade": ["a", "b"] or null,
    "max_sodium_100g": number or null,
    "max_sugars_100g": number or null,
    "max_fat_100g": number or null,
    "min_proteins_100g": number or null,
    "min_fiber_100g": number or null,
    "label": "Organic" or "Gluten-free" or "Vegetarian" or "Palm oil free" or "No preservatives" or null
  },
  "explanation": "One sentence in the same language as the user query explaining what you searched for"
}

EXAMPLES:

User: "healthy low sodium snacks for kids"
Output: {"semantic_query": "healthy low sodium snack children", "filters": {"nutriscore_grade": ["a","b"], "max_sodium_100g": 0.12, "max_sugars_100g": null, "max_fat_100g": null, "min_proteins_100g": null, "min_fiber_100g": null, "label": null}, "explanation": "Searching for healthy snacks with low sodium suitable for children"}

User: "je cherche des céréales bio sans gluten"
Output: {"semantic_query": "organic gluten-free cereals breakfast", "filters": {"nutriscore_grade": null, "max_sodium_100g": null, "max_sugars_100g": null, "max_fat_100g": null, "min_proteins_100g": null, "min_fiber_100g": null, "label": "Gluten-free"}, "explanation": "Recherche de céréales biologiques sans gluten"}

User: "high protein low fat yogurt"
Output: {"semantic_query": "high protein low fat yogurt dairy", "filters": {"nutriscore_grade": null, "max_sodium_100g": null, "max_sugars_100g": null, "max_fat_100g": 3.0, "min_proteins_100g": 10.0, "min_fiber_100g": null, "label": null}, "explanation": "Searching for yogurt with high protein and low fat content"}

User: "food for diabetics"
Output: {"semantic_query": "low sugar diabetic friendly food", "filters": {"nutriscore_grade": ["a","b"], "max_sodium_100g": null, "max_sugars_100g": 5.0, "max_fat_100g": null, "min_proteins_100g": null, "min_fiber_100g": null, "label": null}, "explanation": "Searching for diabetic friendly foods with low sugar and good nutriscore"}

Guidelines:
- healthy / santé = nutriscore_grade ["a", "b"]
- unhealthy / malsain = nutriscore_grade ["d", "e"]
- low sodium / faible en sodium = max_sodium_100g: 0.12
- low sugar / faible en sucre = max_sugars_100g: 5.0
- low fat / faible en gras = max_fat_100g: 3.0
- high protein / riche en protéines = min_proteins_100g: 10.0
- high fiber / riche en fibres = min_fiber_100g: 6.0
- diabetic friendly = max_sugars_100g: 5.0 + nutriscore ["a","b"]
- heart healthy = max_sodium_100g: 0.12 + max_fat_100g: 3.0
- vegan / végétalien → label: "Vegetarian"
- organic / biologique / bio → label: "Organic"
- gluten free / sans gluten → label: "Gluten-free"
- no preservatives → label: "No preservatives"
- palm oil free → label: "Palm oil free"
- if no label match → label: null
- Support English and French queries
- semantic_query must always be in English
- If query is vague do semantic search with no filters
- explanation must be in same language as user query
- label must ONLY use exact values: Organic, Gluten-free, Vegetarian, Palm oil free, No preservatives, or null
"""

def parse_query(user_query: str) -> dict:
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_query}
            ],
            max_tokens=300
        )
        
        result = response.choices[0].message.content
        return json.loads(result)
        
    except Exception as e:
        print(f"Query parsing error: {e}")
        return {
            "semantic_query": user_query,
            "filters": {},
            "explanation": f"Searching for: {user_query}"
        }

if __name__ == "__main__":
    queries = [
        "healthy low sodium vegan snacks",
        "je cherche des céréales bio sans gluten",
        "food for diabetics",
        "high protein low fat yogurt"
    ]
    for q in queries:
        result = parse_query(q)
        print(f"\nQuery: {q}")
        print(json.dumps(result, indent=2))