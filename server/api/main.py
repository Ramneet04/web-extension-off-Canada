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
from api.recommendation import get_recommendation

app = FastAPI(title="OFF AI Search API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

con = duckdb.connect("data/off_v2.duckdb", read_only=True)


session_contexts = {}

def get_session_id(request: Request) -> str:
    sid = request.headers.get("x-session-id")
    if not sid:
        sid = "default"
    return sid



REFINE_PHRASES = [
    "now only", "only ", "also ", "but ", "and also", "make it",
    "filter by", "add filter", "with only", "that are also",
    "change to", "narrow", "refine", "même chose mais", "aussi",
    "maintenant seulement", "mais aussi"
]

RESET_PHRASES = [
    "start over", "clear filters", "reset", "new search", "forget",
    "recommencer", "effacer", "nouvelle recherche"
]

def detect_intent(query: str, has_history: bool) -> str:
    q = query.lower().strip()

    if any(p in q for p in RESET_PHRASES):
        return "reset"

    if has_history and any(q.startswith(p) or p in q for p in REFINE_PHRASES):
        return "refine"

    
    word_count = len(q.split())
    if has_history and word_count <= 3:
        return "refine"

    return "new_search"



MEAL_KEYWORDS = [
    "full day meal", "meal plan", "diet plan", "healthy meal for a day",
    "what to eat in a day", "make me a diet", "suggest a day of meals",
    "full day healthy meal", "breakfast lunch", "breakfast, lunch"
]

RECOMMENDATION_KEYWORDS = [
    "how can i use", "how do i use", "usage", "ways to use",
    "how to include", "how to add", "how to incorporate",
    "daily routine", "suggest simple ways", "diet advice",
    "meal ideas", "snack ideas", "recommend", "which has more",
    "which is better", "which one has", "compare nutrition",
    "how should i use", "what can i do with", "recipe",
    "lequel a plus", "comment utiliser", "routine quotidienne"
]

def is_meal_plan_query(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in MEAL_KEYWORDS)

def is_recommendation_query(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in RECOMMENDATION_KEYWORDS)



class SearchRequest(BaseModel):
    query: str
    limit: int = 20
    offset: int = 0
    country: str = None

class CompareRequest(BaseModel):
    codes: list[str]

class ContextRequest(BaseModel):
    context: dict

class RecommendRequest(BaseModel):
    query: str
    product_name: Optional[str] = None   
    product_code: Optional[str] = None   



@app.post("/api/search")
async def search(req: SearchRequest, request: Request):
    query = req.query.strip()

    sid = get_session_id(request)
    ctx = session_contexts.setdefault(sid, {"history": [], "filters": {}, "last_results": []})

    
    clean_q = query.replace(" ", "")
    if clean_q.isdigit() and 8 <= len(clean_q) <= 14:
        product = get_product_by_code(clean_q, con)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return JSONResponse(content=safe_json({"type": "barcode", "total": 1, "results": [product]}))

    
    compare_keywords = ["compare", "vs", "versus", "comparer", "différence entre", "difference between"]
    if any(kw in query.lower() for kw in compare_keywords):
        barcodes = extract_barcodes_from_query(query)
        result = compare_by_codes(barcodes, con) if barcodes else compare_by_names(query, con)
        ctx["history"].append(query)
        return {"type": "compare", **result, "history": ctx["history"]}

    if is_recommendation_query(query):
        ctx["history"].append(query)
        
        last_product = ctx.get("last_product_name")
        rec = await get_recommendation(query, last_product, None, con)
        return {"type": "recommendation", **rec, "history": ctx["history"]}

    
    if is_meal_plan_query(query):
        ctx["history"].append(query)

        def get_healthy_products(meal_query, n=2):
            res = search_products(meal_query, n, con, 0, req.country, filters={"nutriscore_grade": ["a", "b"]})
            return res["results"] if res and "results" in res else []

        meal_plan = {
            "breakfast": get_healthy_products("healthy breakfast"),
            "lunch":     get_healthy_products("healthy lunch"),
            "snack":     get_healthy_products("healthy snack"),
            "dinner":    get_healthy_products("healthy dinner")
        }
        return {
            "type":      "meal_plan",
            "meal_plan": meal_plan,
            "advice":    "Here's a full day healthy meal plan with real product suggestions!",
            "history":   ctx["history"]
        }

    
    has_history = len(ctx["history"]) > 0
    intent = detect_intent(query, has_history)

    prev_filters = ctx.get("filters", {})

    
    parsed = None
    try:
        from api.query_parser2 import parse_query
        parsed = parse_query(query)
    except Exception:
        pass

    new_filters = parsed.get("filters", {}) if parsed else {}
    new_filters_clean = {k: v for k, v in new_filters.items() if v is not None}

    if intent == "reset":

        ctx["filters"] = {}
        ctx["history"] = []
        active_filters = {}
        search_query = query
    elif intent == "refine":
        
        active_filters = {**prev_filters, **new_filters_clean}
        ctx["filters"] = active_filters
        
        prev_query = ctx["history"][-1] if ctx["history"] else ""
        search_query = (prev_query + ", " + query).strip() if prev_query else query
    else:
        
        active_filters = new_filters_clean
        ctx["filters"] = active_filters
        search_query = query

    ctx["history"].append(query)

    if req.country:
        active_filters["country"] = req.country

    result = search_products(search_query, req.limit, con, req.offset, req.country, filters=active_filters)

    
    if result.get("results"):
        ctx["last_product_name"] = result["results"][0].get("product_name", "")

    filter_summary = _build_filter_summary(active_filters, intent, len(result.get("results", [])))

    return {
        "type":           "search",
        "intent":         intent,
        "filter_summary": filter_summary,
        "active_filters": active_filters,
        **result,
        "history": ctx["history"]
    }


def _build_filter_summary(filters: dict, intent: str, count: int) -> str:
    """Returns a human-readable summary like 'Filtered to 8 vegan healthy snacks'"""
    parts = []
    if filters.get("nutriscore_grade") and set(filters["nutriscore_grade"]) <= {"a", "b"}:
        parts.append("healthy")
    if filters.get("label"):
        parts.append(filters["label"])
    if filters.get("max_sodium_100g") is not None:
        parts.append("low sodium")
    if filters.get("max_sugars_100g") is not None:
        parts.append("low sugar")
    if filters.get("min_proteins_100g") is not None:
        parts.append("high protein")
    if filters.get("max_fat_100g") is not None:
        parts.append("low fat")
    if filters.get("nova_group"):
        parts.append("unprocessed")

    if not parts:
        return f"Found {count} results"

    label = " ".join(parts)
    if intent == "refine":
        return f"Filtered to {count} {label} products"
    return f"Found {count} {label} products"


@app.post("/api/recommend")
async def recommend(req: RecommendRequest, request: Request):
    sid = get_session_id(request)
    ctx = session_contexts.get(sid, {"history": [], "filters": {}, "last_product_name": None})

   
    product_name = req.product_name or ctx.get("last_product_name")

    rec = await get_recommendation(req.query, product_name, req.product_code, con)

    ctx.setdefault("history", []).append(req.query)
    session_contexts[sid] = ctx

    return {"type": "recommendation", **rec}



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
    return {
        "history":        ctx.get("history", []),
        "filters":        ctx.get("filters", {}),
        "last_product":   ctx.get("last_product_name")
    }

@app.delete("/api/session/context")
async def clear_session_context(request: Request):
    sid = get_session_id(request)
    session_contexts[sid] = {"history": [], "filters": {}, "last_product_name": None}
    return {"status": "cleared"}


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