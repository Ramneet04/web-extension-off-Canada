from groq import Groq
from typing import Optional
import duckdb
import json
import os
import math
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))



def clean(val):
    if val is None:
        return None
    try:
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return None
    except Exception:
        pass
    return val


def _get_product_nutrition(product_name: str, con: duckdb.DuckDBPyConnection) -> Optional[dict]:
    try:
        result = con.execute("""
            SELECT
                product_name,
                brands,
                proteins_100g,
                fat_100g,
                sugars_100g,
                fiber_100g,
                energy_kcal_100g,
                sodium_100g,
                nutriscore_grade,
                nova_group,
                categories_tags,
                labels_tags
            FROM products
            WHERE product_name ILIKE ?
            ORDER BY popularity_key DESC
            LIMIT 1
        """, [f"%{product_name}%"]).fetchdf()

        if result.empty:
            return None

        row = result.to_dict("records")[0]
        return {k: clean(v) for k, v in row.items()}
    except Exception as e:
        print(f"Nutrition fetch error: {e}")
        return None


def _get_products_by_nutrition(
    min_protein: Optional[float] = None,
    max_sugar: Optional[float] = None,
    max_fat: Optional[float] = None,
    label: Optional[str] = None,
    category_hint: Optional[str] = None,
    limit: int = 4,
    con: duckdb.DuckDBPyConnection = None
) -> list[dict]:
    """Fetch recommended products based on nutrition constraints."""
    try:
        conditions = ["nutriscore_grade IN ('a', 'b')", "product_name IS NOT NULL"]
        params = []

        if min_protein is not None:
            conditions.append("proteins_100g >= ?")
            params.append(min_protein)
        if max_sugar is not None:
            conditions.append("sugars_100g <= ?")
            params.append(max_sugar)
        if max_fat is not None:
            conditions.append("fat_100g <= ?")
            params.append(max_fat)
        if label:
            conditions.append("labels_tags ILIKE ?")
            params.append(f"%{label}%")
        if category_hint:
            conditions.append("categories_tags ILIKE ?")
            params.append(f"%{category_hint}%")

        where = " AND ".join(conditions)
        params.append(limit)

        result = con.execute(f"""
            SELECT
                code,
                product_name,
                brands,
                proteins_100g,
                fat_100g,
                sugars_100g,
                energy_kcal_100g,
                nutriscore_grade,
                image_url
            FROM products
            WHERE {where}
            ORDER BY popularity_key DESC
            LIMIT ?
        """, params).fetchdf()

        if result.empty:
            return []

        products = []
        for row in result.to_dict("records"):
            row = {k: clean(v) for k, v in row.items()}
            img = row.get("image_url")
            if img:
                row["image_url"] = f"https://images.openfoodfacts.org/images/products/{img}"
            products.append(row)
        return products

    except Exception as e:
        print(f"Product fetch error: {e}")
        return []



INTENT_SYSTEM = """You are a food query intent classifier. Given a user message, return ONLY a JSON object with these fields:

{
  "intent": "usage" | "comparison" | "general",
  "product_a": "product name or null",
  "product_b": "product name or null",
  "nutrient_focus": "protein" | "sugar" | "fat" | "calories" | "fiber" | "sodium" | null,
  "meal_slot": "breakfast" | "lunch" | "dinner" | "snack" | "post-workout" | "any" | null,
  "language": "en" | "fr"
}

Rules:
- "usage"      → user asking how to use/incorporate a product in daily life
- "comparison" → user asking which of two things has more/less of something
- "general"    → anything else (diet advice, meal ideas, general nutrition)
- Extract product names exactly as mentioned
- No markdown, no explanation. Raw JSON only."""


def _classify_intent(query: str) -> dict:
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": INTENT_SYSTEM},
                {"role": "user", "content": query}
            ],
            max_tokens=150
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        print(f"Intent classification error: {e}")
        return {
            "intent": "general",
            "product_a": None,
            "product_b": None,
            "nutrient_focus": None,
            "meal_slot": None,
            "language": "en"
        }



RESPONSE_SYSTEM = """You are a friendly, practical nutritionist assistant for Open Food Facts.

Given a user query + real product nutrition data, generate helpful, practical suggestions.

Return ONLY a valid JSON object with this structure:
{
  "advice": "1-2 sentence friendly summary",
  "comparison_insight": "string or null — only fill if comparing two products",
  "daily_use_suggestions": [
    {"slot": "Breakfast", "idea": "practical suggestion"},
    {"slot": "Smoothie", "idea": "practical suggestion"},
    {"slot": "Post-workout", "idea": "practical suggestion"},
    {"slot": "Snack", "idea": "practical suggestion"}
  ],
  "recommended_search_query": "a short search phrase to find similar/complementary products"
}

Rules:
- Keep suggestions SHORT and PRACTICAL (one sentence each)
- Base suggestions on the actual nutrition data provided
- If protein is high → emphasize post-workout, muscle building
- If fiber is high → emphasize digestion, gut health
- If low sugar → good for diabetics, weight management
- recommended_search_query should help find good complementary products
- Respond in the same language as the user query
- No markdown, no explanation. Raw JSON only."""


def _generate_response(query: str, intent: dict, product_data: Optional[dict], product_b_data: Optional[dict]) -> dict:
    
    context_parts = [f"User query: {query}", f"Intent: {intent.get('intent')}"]

    if product_data:
        context_parts.append(f"""
Product A: {product_data.get('product_name')} ({product_data.get('brands', '')})
- Protein: {product_data.get('proteins_100g')}g per 100g
- Fat: {product_data.get('fat_100g')}g per 100g
- Sugar: {product_data.get('sugars_100g')}g per 100g
- Fiber: {product_data.get('fiber_100g')}g per 100g
- Calories: {product_data.get('energy_kcal_100g')} kcal per 100g
- Nutriscore: {product_data.get('nutriscore_grade', 'unknown').upper()}
- Category: {product_data.get('categories_tags', '')}
""")

    if product_b_data:
        context_parts.append(f"""
Product B: {product_b_data.get('product_name')} ({product_b_data.get('brands', '')})
- Protein: {product_b_data.get('proteins_100g')}g per 100g
- Fat: {product_b_data.get('fat_100g')}g per 100g
- Sugar: {product_b_data.get('sugars_100g')}g per 100g
- Fiber: {product_b_data.get('fiber_100g')}g per 100g
- Calories: {product_b_data.get('energy_kcal_100g')} kcal per 100g
- Nutriscore: {product_b_data.get('nutriscore_grade', 'unknown').upper()}
""")

    if intent.get("nutrient_focus"):
        context_parts.append(f"User is asking specifically about: {intent['nutrient_focus']}")

    context = "\n".join(context_parts)

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": RESPONSE_SYSTEM},
                {"role": "user", "content": context}
            ],
            max_tokens=500
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        print(f"Response generation error: {e}")
        return {
            "advice": "Here are some practical ways to use this product in your daily routine.",
            "comparison_insight": None,
            "daily_use_suggestions": [
                {"slot": "Breakfast", "idea": "Add to your morning meal for a nutritious start."},
                {"slot": "Smoothie", "idea": "Blend with fruits for a quick smoothie."},
                {"slot": "Snack", "idea": "Enjoy as a healthy mid-day snack."},
                {"slot": "Post-workout", "idea": "Good source of nutrients after exercise."}
            ],
            "recommended_search_query": "healthy products"
        }


async def get_recommendation(
    query: str,
    product_name: Optional[str],
    product_code: Optional[str],
    con: duckdb.DuckDBPyConnection
) -> dict:
    """
    Full recommendation pipeline:
    1. Classify intent
    2. Fetch real product data
    3. Generate LLM response
    4. Fetch recommended products from DB
    """

    
    intent = _classify_intent(query)
    print(f"[Recommend] Intent: {intent}")

    
    product_a_data = None
    product_b_data = None

    
    name_a = intent.get("product_a") or product_name
    name_b = intent.get("product_b")

    if product_code:
        
        from api.search2 import get_product_by_code
        p = get_product_by_code(product_code, con)
        if p:
            product_a_data = {
                "product_name":    p.get("product_name"),
                "brands":          p.get("brands"),
                "proteins_100g":   p.get("nutrition", {}).get("proteins"),
                "fat_100g":        p.get("nutrition", {}).get("fat"),
                "sugars_100g":     p.get("nutrition", {}).get("sugars"),
                "fiber_100g":      p.get("nutrition", {}).get("fiber"),
                "energy_kcal_100g": p.get("nutrition", {}).get("energy_kcal"),
                "nutriscore_grade": p.get("nutriscore_grade"),
                "categories_tags": p.get("categories_tags"),
            }

    if not product_a_data and name_a:
        product_a_data = _get_product_nutrition(name_a, con)

    if name_b:
        product_b_data = _get_product_nutrition(name_b, con)

    
    llm_response = _generate_response(query, intent, product_a_data, product_b_data)

    
    recommended_products = []

    if product_a_data:
        protein = product_a_data.get("proteins_100g") or 0
        sugar   = product_a_data.get("sugars_100g")
        fat     = product_a_data.get("fat_100g")

        
        cats = product_a_data.get("categories_tags") or ""
        category_hint = None
        for cat in ["milk", "yogurt", "cereal", "snack", "bread", "juice", "cheese"]:
            if cat in cats.lower():
                category_hint = cat
                break

        recommended_products = _get_products_by_nutrition(
            min_protein = round(protein * 0.7, 1) if protein > 3 else None,
            max_sugar   = round(sugar * 1.2, 1) if sugar and sugar < 10 else None,
            category_hint = category_hint,
            limit       = 4,
            con         = con
        )
    else:
        
        search_q = llm_response.get("recommended_search_query", "healthy products")
        recommended_products = _get_products_by_nutrition(limit=4, con=con)

    return {
        "query":                  query,
        "intent":                 intent.get("intent"),
        "language":               intent.get("language", "en"),
        "product_a":              product_a_data,
        "product_b":              product_b_data,
        "advice":                 llm_response.get("advice"),
        "comparison_insight":     llm_response.get("comparison_insight"),
        "daily_use_suggestions":  llm_response.get("daily_use_suggestions", []),
        "recommended_products":   recommended_products,
    }