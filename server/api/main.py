from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import duckdb
import math
import json

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

class SearchRequest(BaseModel):
    query: str
    limit: int = 20
    offset: int = 0
    country: str = None

class CompareRequest(BaseModel):
    codes: list[str]

@app.post("/api/search")
async def search(req: SearchRequest):
    query = req.query.strip()

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
        return {"type": "compare", **result}

    result = search_products(query, req.limit, con, req.offset, req.country)
    return {"type": "search", **result}


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