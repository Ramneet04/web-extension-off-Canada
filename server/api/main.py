from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import duckdb
from api.search import search_products

app = FastAPI(title="OFF Canada AI Search API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

con = duckdb.connect("data/off_canada.duckdb")

class SearchRequest(BaseModel):
    query: str
    limit: int = 20

@app.post("/api/search")
async def search(req: SearchRequest):
    result = search_products(req.query, req.limit)
    return result

@app.get("/api/product/{code}")
async def get_product(code: str):
    result = con.execute(
        "SELECT * FROM products WHERE code = ?", [code]
    ).fetchdf()
    
    if result.empty:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return result.to_dict("records")[0]

@app.get("/health")
async def health():
    return {"status": "ok"}