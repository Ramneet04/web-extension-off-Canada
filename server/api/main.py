from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import duckdb
import math
import json

from fastapi import Request
from typing import Optional

def safe_json(obj):
    if isinstance(obj, dict):
        return {k: safe_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [safe_json(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj
from api.search2 import (
    search_products,
    get_product_by_code,
    get_similar_products,
    compare_by_codes,
    compare_by_names,
    extract_barcodes_from_query
)

app = FastAPI(title="OFF AI Search API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

con = duckdb.connect("data/off_v2.duckdb", read_only=True)

# In-memory session context (per session id)
session_contexts = {}

def get_session_id(request: Request) -> str:
    sid = request.headers.get("x-session-id")
    if not sid:
        sid = "default"
    return sid

class SearchRequest(BaseModel):
    query: str
    limit: int = 20
    offset: int = 0
    country: str = None

class CompareRequest(BaseModel):
    codes: list[str]

class ContextRequest(BaseModel):
    context: dict

class DietProfileRequest(BaseModel):
    product_name: str
    context: Optional[dict] = None

@app.post("/api/search")
async def search(req: SearchRequest, request: Request):
    query = req.query.strip()

    sid = get_session_id(request)
    ctx = session_contexts.setdefault(sid, {"history": [], "filters": {}})
    ctx["history"].append(query)

    clean = query.replace(" ", "")
    if clean.isdigit() and 8 <= len(clean) <= 14:
        product = get_product_by_code(clean, con)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return JSONResponse(content=safe_json({"type": "barcode", "total": 1, "results": [product]}))

    compare_keywords = ["compare", "vs", "versus", "comparer", "différence entre", "difference between"]
    if any(kw in query.lower() for kw in compare_keywords):
        barcodes = extract_barcodes_from_query(query)
        if barcodes:
            result = compare_by_codes(barcodes, con)
        else:
            result = compare_by_names(query, con)
        return {"type": "compare", **result, "history": ctx["history"]}

    # Detect meal plan/diet profile intent
    meal_keywords = [
        "full day meal", "meal plan", "diet plan", "breakfast, lunch, snacks, dinner", "healthy meal for a day", "what to eat in a day", "make me a diet", "suggest a day of meals", "full day healthy meal"
    ]
    meal_trigger = any(kw in query.lower() for kw in meal_keywords)

    # Detect advice/usage intent (simple keyword-based for now)
    advice_keywords = [
        "how can i use", "how do i use", "usage", "ways to use", "how to include", "how to add", "how to incorporate", "daily routine", "suggest simple ways", "diet advice", "meal ideas", "snack ideas"
    ]
    advice_trigger = any(kw in query.lower() for kw in advice_keywords)

    # Merge filters: if query is a refinement (e.g., 'only vegan'), combine with previous filters

    prev_filters = ctx.get("filters", {})
    prev_history = ctx.get("history", [])
    prev_query = prev_history[-2] if len(prev_history) > 1 else None
    parsed = None
    try:
        from api.query_parser2 import parse_query
        parsed = parse_query(query)
    except Exception:
        pass
    new_filters = parsed.get("filters", {}) if parsed else {}
    # If the new query is a refinement (e.g., only adds a filter), merge with previous
    merged_filters = {**prev_filters, **{k: v for k, v in new_filters.items() if v is not None}}
    # If the new query is a broad search (e.g., contains 'snack', 'search', 'find'), reset filters
    broad_keywords = ["search", "find", "show", "snack", "breakfast", "lunch", "dinner", "meal", "food"]
    is_broad = any(kw in query.lower() for kw in broad_keywords)
    filters = merged_filters if not is_broad or not new_filters else new_filters
    ctx["filters"] = filters

    # If this is a refinement (not a broad search), combine previous query and new query for semantic search
    combined_query = query
    if not is_broad and prev_query:
        # Combine previous query and new query for embedding
        combined_query = prev_query.strip() + ", " + query.strip()

    # If meal plan intent, build a meal plan from healthy products
    if meal_trigger:
        # Helper to get healthy products for a meal
        def get_healthy_products(meal_query, n=2):
            res = search_products(meal_query, n, con, 0, req.country, filters={"nutriscore_grade": ["a", "b"]})
            return res["results"] if res and "results" in res else []

        meal_plan = {
            "breakfast": get_healthy_products("healthy breakfast"),
            "lunch": get_healthy_products("healthy lunch"),
            "snack": get_healthy_products("healthy snack"),
            "dinner": get_healthy_products("healthy dinner")
        }
        advice = "Here's a full day healthy meal plan with real product suggestions for breakfast, lunch, snack, and dinner. Choose any you like!"
        return {
            "type": "meal_plan",
            "meal_plan": meal_plan,
            "advice": advice,
            "history": ctx["history"]
        }

    # Otherwise, normal search/advice
    result = search_products(query, req.limit, con, req.offset, req.country, filters=filters)

    # If advice intent, add usage_suggestions (demo: oat/almond milk, else generic)
    usage_suggestions = None
    if advice_trigger:
        ql = query.lower()
        if "oat milk" in ql or "almond milk" in ql:
            usage_suggestions = [
                "Add to breakfast cereal or oatmeal.",
                "Blend in smoothies.",
                "Use as a post-workout drink.",
                "Pour in coffee or tea.",
                "Use in baking recipes."
            ]
        elif "yogurt" in ql:
            usage_suggestions = [
                "Top with fruit and granola for breakfast.",
                "Blend into smoothies.",
                "Use as a base for dips or dressings.",
                "Enjoy as a snack with honey or nuts."
            ]
        else:
            usage_suggestions = [
                "Try adding this product to your breakfast, lunch, or snacks.",
                "Incorporate into smoothies, salads, or as a topping.",
                "Use as a healthy substitute in recipes.",
                "Enjoy post-workout or as a quick snack."
            ]
    return {"type": "search", **result, "history": ctx["history"], "usage_suggestions": usage_suggestions}
@app.post("/api/session/context")
async def update_session_context(req: ContextRequest, request: Request):
    sid = get_session_id(request)
    ctx = session_contexts.setdefault(sid, {"history": [], "filters": {}})
    ctx["filters"].update(req.context)
    return {"status": "ok", "context": ctx}

@app.get("/api/session/context")
async def get_session_context(request: Request):
    sid = get_session_id(request)
    ctx = session_contexts.get(sid, {"history": [], "filters": {}})
    # Always return full history and filters
    return {"history": ctx.get("history", []), "filters": ctx.get("filters", {})}

# Diet profile and usage suggestion endpoint
@app.post("/api/diet_profile")
async def diet_profile(req: DietProfileRequest):
    # For demo: hardcoded protein comparison and usage suggestion
    name = req.product_name.lower()
    protein_map = {"almond milk": 1, "oat milk": 3}
    protein = protein_map.get(name, 0)
    compare = None
    if "almond" in name or "oat" in name:
        compare = "Oat milk has more protein than almond milk." if protein_map["oat milk"] > protein_map["almond milk"] else "Almond milk has more protein than oat milk."
    usage = []
    if "milk" in name:
        usage = [
            "Add to breakfast cereal or oatmeal.",
            "Blend in smoothies.",
            "Use as a post-workout drink.",
            "Pour in coffee or tea.",
            "Use in baking recipes."
        ]
    return {"product": name, "protein_g": protein, "compare": compare, "usage": usage}


@app.get("/api/product/{code}")
async def get_product(code: str):
    product = get_product_by_code(code, con)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return JSONResponse(content=safe_json(product))


@app.get("/api/product/{code}/similar")
async def similar_products(code: str, limit: int = Query(default=10, le=30)):
    result = get_similar_products(code, limit, con)
    return JSONResponse(content=safe_json({"type": "similar", **result}))


@app.post("/api/compare")
async def compare(req: CompareRequest):
    if not req.codes:
        raise HTTPException(status_code=400, detail="No codes provided")
    result = compare_by_codes(req.codes, con)
    if result["total"] == 0:
        raise HTTPException(status_code=404, detail="No products found")
    return JSONResponse(content=safe_json({"type": "compare", **result}))


@app.get("/health")
async def health():
    count = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    return {"status": "ok", "products": count}