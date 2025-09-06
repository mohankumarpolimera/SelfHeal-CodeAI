"""
mcp_servers/stackoverflow_server.py

Small MCP wrapper around Stack Exchange API (StackOverflow search).
POST /search  { "query": "text", "pagesize": 5 }
Returns a list of {title, link, is_answered, score, excerpt}
"""

from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os

app = FastAPI(title="MCP - StackOverflow")

STACK_EX_BASE = "https://api.stackexchange.com/2.3/search/advanced"

class QueryIn(BaseModel):
    query: str
    pagesize: int = 5

@app.post("/search")
def search_stackoverflow(payload: QueryIn):
    q = payload.query
    pagesize = min(max(1, payload.pagesize), 20)
    params = {
        "order": "desc",
        "sort": "relevance",
        "q": q,
        "site": "stackoverflow",
        "pagesize": pagesize
    }
    try:
        r = requests.get(STACK_EX_BASE, params=params, timeout=8)
        r.raise_for_status()
        data = r.json()
        items = data.get("items", [])[:pagesize]
        results = []
        for it in items:
            results.append({
                "title": it.get("title"),
                "link": it.get("link"),
                "is_answered": it.get("is_answered"),
                "score": it.get("score"),
                "excerpt": it.get("excerpt") if "excerpt" in it else None
            })
        return {"ok": True, "results": results}
    except Exception as e:
        return {"ok": False, "error": str(e)}
