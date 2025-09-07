"""
app.py

Main FastAPI app for SelfHeal-Code-AI
- Boots recruiter demo UI/API
- Starts all MCP microservers as background processes
"""

import os
import multiprocessing
import uvicorn
from fastapi import FastAPI, Request                       # ✨ NEW: Request
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse   # ✨ NEW: JSONResponse
import socket
# ✨ NEW: hook the graph runner
from graph.selfheal_graph import execute_selfheal          # <-- you'll add this function

# load .env keys
load_dotenv()

app = FastAPI(title="SelfHeal Code AI")
# ------------------------
# Utility to check port availability

def _port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Return True if something is already listening on host:port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        return s.connect_ex((host, port)) == 0
# ------------------------
# Background MCP Servers
# ------------------------

def run_server(module: str, port: int):
    """Run a uvicorn server on given module:app at port."""
    uvicorn.run(f"{module}:app", host="127.0.0.1", port=port, reload=False, log_level="info")

def start_mcp_servers():
    """Start all MCP microservers as separate processes (idempotent)."""
    servers = [
        ("mcp_servers.sandbox_server", 8001),
        ("mcp_servers.tester_server", 8002),
        ("mcp_servers.stackoverflow_server", 8003),
        ("mcp_servers.docs_server", 8004),
        ("mcp_servers.chroma_server", 8005),
    ]
    procs = []
    for module, port in servers:
        if _port_in_use(port):
            print(f"[SKIP] {module} on port {port} already running")
            continue
        p = multiprocessing.Process(target=run_server, args=(module, port))
        p.daemon = True
        p.start()
        procs.append(p)
        print(f"[BOOT] Started {module} on port {port}")
    return procs


@app.on_event("startup")
async def startup_event():
    # start all MCP services in background
    start_mcp_servers()

# ------------------------
# Main API routes
# ------------------------
# Serve static files
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

@app.get("/")
async def root():
    return FileResponse(os.path.join("frontend", "index.html"))

@app.get("/health")
def health():
    return {"status": "ok"}

# ✨ NEW: one-shot run endpoint that your frontend calls
@app.post("/run_workflow")
async def run_agentic_system(req: Request):
    payload = await req.json()
    prompt = payload.get("prompt", "").strip()
    if not prompt:
        return JSONResponse({"error": "prompt is required"}, status_code=400)
    # run the whole LangGraph/MCP pipeline and return a clean JSON
    result = execute_selfheal(prompt)
    return JSONResponse(result)

# ------------------------
# Main entry
# ------------------------

if __name__ == "__main__":
    # Run the main app itself (port 8000)
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True, log_level="info")
