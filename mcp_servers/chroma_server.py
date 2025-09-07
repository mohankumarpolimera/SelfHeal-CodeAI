# mcp_servers/chroma_server.py
"""
MCP - Chroma Memory (v0.5+ API, telemetry OFF, local persistence)

Endpoints:
 - POST /store        { "error_text": "...", "fix": { ... } }
 - POST /query        { "error_text": "..." }
 - POST /query_by_sig { "signature": "abcd1234" }
 - GET  /health
"""

from fastapi import FastAPI
from pydantic import BaseModel
import hashlib
import os

# Chroma v0.5+ client API
try:
    from chromadb import PersistentClient, EphemeralClient
    from chromadb.config import Settings
except Exception:  # older versions fallback (shouldn't happen if on 0.5+)
    import chromadb  # type: ignore
    PersistentClient = getattr(chromadb, "PersistentClient")
    EphemeralClient = getattr(chromadb, "EphemeralClient")
    from chromadb.config import Settings  # type: ignore

app = FastAPI(title="MCP - Chroma Memory")

# ---- Storage / Client -------------------------------------------------------
# Use a NEW folder by default to avoid legacy DB conflicts
# (you can override with CHROMA_DIR in your .env)
PERSIST_DIR = os.getenv("CHROMA_DIR", os.path.join(os.getcwd(), "data", "chroma_v2"))
os.makedirs(PERSIST_DIR, exist_ok=True)

settings = Settings(anonymized_telemetry=False)

def _make_client():
    try:
        return PersistentClient(path=PERSIST_DIR, settings=settings)
    except Exception as e:
        # If an old/invalid DB exists, fall back to memory so the server still runs.
        print(f"[chroma] PersistentClient failed at {PERSIST_DIR}: {e}\n"
              f"         Falling back to EphemeralClient (data won't persist).")
        return EphemeralClient(settings=settings)

client = _make_client()

COL_NAME = "error_fixes"
# v0.5+ still supports get_or_create_collection
collection = client.get_or_create_collection(name=COL_NAME)

# ---- Helpers ----------------------------------------------------------------
def _sig(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]

class StoreIn(BaseModel):
    error_text: str
    fix: dict

class QueryIn(BaseModel):
    error_text: str

class QuerySig(BaseModel):
    signature: str

# ---- Endpoints ---------------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "persist_dir": PERSIST_DIR,
        "collection": COL_NAME,
        "telemetry": False,
    }

@app.post("/store")
def store_fix(payload: StoreIn):
    sig = _sig(payload.error_text)
    doc = (payload.error_text or "")[:2000]
    metadata = {
        "signature": sig,
        "fix_preview": str(list(payload.fix.keys()))[:500]
        if isinstance(payload.fix, dict) else str(payload.fix)[:500],
    }
    try:
        try:
            collection.add(ids=[sig], documents=[doc], metadatas=[metadata])
        except Exception:
            # If ID exists, update
            collection.update(ids=[sig], documents=[doc], metadatas=[metadata])
        return {"ok": True, "signature": sig}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/query")
def query_fix(payload: QueryIn):
    sig = _sig(payload.error_text)

    # First: exact ID match
    try:
        res = collection.get(ids=[sig])
        if res and res.get("ids"):
            ids = res.get("ids", [])
            docs = res.get("documents", [])
            metas = res.get("metadatas", [])
            out = [{"id": ids[i], "document": docs[i], "metadata": metas[i]} for i in range(len(ids))]
            return {"ok": True, "matches": out}
    except Exception:
        pass  # fall through to substring

    # Fallback: naive substring search across all docs (small scale)
    try:
        all_items = collection.get()
        ids = all_items.get("ids", []) or []
        docs = all_items.get("documents", []) or []
        metas = all_items.get("metadatas", []) or []
        term = (payload.error_text or "").strip()
        matches = []
        if term:
            for i, d in enumerate(docs):
                if term in (d or ""):
                    matches.append({"id": ids[i], "document": d, "metadata": metas[i]})
        return {"ok": True, "matches": matches}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/query_by_sig")
def query_by_sig(payload: QuerySig):
    try:
        res = collection.get(ids=[payload.signature])
        if res and res.get("ids"):
            ids = res.get("ids", [])
            docs = res.get("documents", [])
            metas = res.get("metadatas", [])
            out = [{"id": ids[i], "document": docs[i], "metadata": metas[i]} for i in range(len(ids))]
            return {"ok": True, "matches": out}
        return {"ok": True, "matches": []}
    except Exception as e:
        return {"ok": False, "error": str(e)}
