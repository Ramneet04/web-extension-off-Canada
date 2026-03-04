from groq import Groq
import json
import os
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a food search query parser for a Canadian food database.
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
    "label": "vegan" or "organic" or "gluten-free" or null
  },
  "explanation": "One sentence in the same language as the user query explaining what you searched for"
}
EXAMPLES:

User: "healthy low sodium snacks for kids"
Output: {"semantic_query": "healthy low sodium snack children", "filters": {"nutriscore_grade": ["a","b"], "max_sodium_100g": 0.12, "max_sugars_100g": null, "max_fat_100g": null, "min_proteins_100g": null, "min_fiber_100g": null, "label": null}, "explanation": "Searching for healthy snacks with low sodium suitable for children"}

User: "je cherche des céréales bio sans gluten"
Output: {"semantic_query": "organic gluten-free cereals breakfast", "filters": {"nutriscore_grade": null, "max_sodium_100g": null, "max_sugars_100g": null, "max_fat_100g": null, "min_proteins_100g": null, "min_fiber_100g": null, "label": "gluten-free"}, "explanation": "Recherche de céréales biologiques sans gluten"}

User: "high protein low fat yogurt"
Output: {"semantic_query": "high protein low fat yogurt dairy", "filters": {"nutriscore_grade": null, "max_sodium_100g": null, "max_sugars_100g": null, "max_fat_100g": 3.0, "min_proteins_100g": 10.0, "min_fiber_100g": null, "label": null}, "explanation": "Searching for yogurt with high protein and low fat content"}

User: "food for diabetics"
Output: {"semantic_query": "low sugar diabetic friendly food", "filters": {"nutriscore_grade": ["a","b"], "max_sodium_100g": null, "max_sugars_100g": 5.0, "max_fat_100g": null, "min_proteins_100g": null, "min_fiber_100g": null, "label": null}, "explanation": "Searching for diabetic friendly foods with low sugar and good nutriscore"}

Guidelines:
- healthy = nutriscore a or b
- low sodium = max_sodium_100g 0.12
- low sugar = max_sugars_100g 5
- vegan/organic/gluten-free go in label field
- Support English and French queries
- semantic_query must always be in English
- If the user query is vague, make your best guess and explain it in the explanation field
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