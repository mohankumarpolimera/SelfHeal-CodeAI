"""
mcp_servers/chroma_server.py

Simple MCP wrapper around ChromaDB for storing error->fix pairs.
Endpoints:
 - POST /store   { "error_text": "...", "fix": { "files": { fname: content, ... } } }
 - POST /query   { "error_text": "..." }   -> returns exact or signature match
 - POST /query_by_sig { "signature": "abcd1234" }

This is a simple in-memory Chromadb-based store using the local client.
"""

from fastapi import FastAPI
from pydantic import BaseModel
import chromadb
from chromadb.config import Settings
import hashlib
import os

app = FastAPI(title="MCP - Chroma Memory")

# Start chroma client (in-memory default)
CHROMA_DIR = os.getenv("CHROMA_DIR", None)
client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=CHROMA_DIR) if CHROMA_DIR else Settings())

COL_NAME = "error_fixes"
if COL_NAME in [c.name for c in client.list_collections()]:
    collection = client.get_collection(COL_NAME)
else:
    collection = client.create_collection(name=COL_NAME)

def _sig(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]

class StoreIn(BaseModel):
    error_text: str
    fix: dict

class QueryIn(BaseModel):
    error_text: str

class QuerySig(BaseModel):
    signature: str

@app.post("/store")
def store_fix(payload: StoreIn):
    sig = _sig(payload.error_text)
    # store text as document, metadata includes signature and fix summary
    doc = payload.error_text[:2000]
    metadata = {"signature": sig}
    # use a short string representation for the fix in metadata for quick search
    fix_repr = str(list(payload.fix.keys()))[:500] if isinstance(payload.fix, dict) else str(payload.fix)[:500]
    metadata["fix_preview"] = fix_repr
    # add to chroma
    try:
        collection.add(
            ids=[sig],
            documents=[doc],
            metadatas=[metadata]
        )
        # optionally persist files to disk or object store in real prod
        return {"ok": True, "signature": sig}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/query")
def query_fix(payload: QueryIn):
    sig = _sig(payload.error_text)
    # try exact signature first
    res = collection.get(ids=[sig]) if sig else None
    if res and len(res.get("ids", [])) > 0:
        # prepare return
        out = []
        for i, id_ in enumerate(res["ids"]):
            out.append({"id": id_, "document": res["documents"][i], "metadata": res["metadatas"][i]})
        return {"ok": True, "matches": out}
    # fallback: naive substring search through documents (small scale only)
    # load all documents and filter
    all_docs = collection.get()['documents']
    all_ids = collection.get()['ids']
    all_meta = collection.get()['metadatas']
    matches = []
    for i, doc in enumerate(all_docs):
        if payload.error_text.strip() and payload.error_text.strip() in doc:
            matches.append({"id": all_ids[i], "document": doc, "metadata": all_meta[i]})
    return {"ok": True, "matches": matches}

@app.post("/query_by_sig")
def query_by_sig(payload: QuerySig):
    try:
        res = collection.get(ids=[payload.signature])
        if res and res.get("ids"):
            out = []
            for i, id_ in enumerate(res["ids"]):
                out.append({"id": id_, "document": res["documents"][i], "metadata": res["metadatas"][i]})
            return {"ok": True, "matches": out}
        return {"ok": True, "matches": []}
    except Exception as e:
        return {"ok": False, "error": str(e)}
