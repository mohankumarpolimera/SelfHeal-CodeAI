"""
mcp_servers/docs_server.py

Simple MCP service that fetches PyPI package metadata (via pypi.org JSON API)
Endpoint:
 - POST /pkg_info  { "package": "fastapi" }
Returns package info summary.
"""

from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI(title="MCP - PyPI Docs")

PYPI_URL = "https://pypi.org/pypi/{pkg}/json"

class PkgIn(BaseModel):
    package: str

@app.post("/pkg_info")
def pkg_info(payload: PkgIn):
    pkg = payload.package.strip()
    if not pkg:
        return {"ok": False, "error": "empty package"}
    try:
        r = requests.get(PYPI_URL.format(pkg=pkg), timeout=8)
        if r.status_code == 404:
            return {"ok": False, "error": "package not found"}
        r.raise_for_status()
        j = r.json()
        info = j.get("info", {})
        releases = j.get("releases", {}).keys()
        return {
            "ok": True,
            "name": info.get("name"),
            "summary": info.get("summary"),
            "version": info.get("version"),
            "home_page": info.get("home_page"),
            "requires_dist": info.get("requires_dist"),
            "releases": list(releases)[:10]
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
