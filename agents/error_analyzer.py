# agents/error_analyzer.py
import os
from typing import Any, Dict
from utils.mcp_client import MCPClient

ANALYZE_LIMIT = int(os.getenv("ANALYZE_LIMIT", "20"))

class ErrorAnalyzerAgent:
    def __init__(self):
        self.tester = MCPClient("http://127.0.0.1:8002")         # /pytest
        self.sandbox = MCPClient("http://127.0.0.1:8001")        # /run
        self.stackoverflow = MCPClient("http://127.0.0.1:8003")  # /search

    def analyze_error(self, state: Dict[str, Any]):
        dbg = state.setdefault("debug", [])
        dbg.append({"node": "analyze", "attempts": int(state.get("attempts", 0))})

        code = (state.get("code") or "").strip()
        if not code:
            state["errors"] = ["No code yet; generator must create code first."]
            return state

        # Loop guard to avoid infinite ping-pong
        state["analyze_count"] = int(state.get("analyze_count", 0)) + 1
        if state["analyze_count"] > ANALYZE_LIMIT:
            state["errors"] = ["Loop guard tripped in analyzer."]
            state["force_giveup"] = True
            dbg[-1]["loop_guard"] = "tripped"
            return state

        # 1) Run tests (or auto-pass if no tests were provided)
        t = self.tester.post("pytest", {"files": {"app.py": code}})
        if isinstance(t, dict) and t.get("error"):
            state["errors"] = [f"tester_error: {t['error']}"]
            state["force_giveup"] = True
            dbg[-1]["tester"] = "error"
            return state

        if t.get("passed"):
            # 2) When tests pass (or none provided), run the program to capture output
            r = self.sandbox.post("run", {"code": code, "timeout": 8})
            if isinstance(r, dict) and r.get("error"):
                # If sandbox infra fails, exit gracefully (don’t loop)
                state["errors"] = [f"sandbox_error: {r['error']}"]
                state["force_giveup"] = True
                dbg[-1]["sandbox"] = "error"
                return state

            state["errors"] = []
            state["program_output"] = (r.get("stdout") or "").strip()
            dbg[-1]["tester"] = "passed"
            dbg[-1]["run_rc"] = r.get("returncode", 0)
            return state

        # 3) Tests failed: collect a concise error message
        err_text = (t.get("stderr") or t.get("stdout") or "").strip()
        state["errors"] = [err_text[:4000]]
        dbg[-1]["tester"] = "failed"

        # Single SO query per attempt
        if not state.get("so_queried", False) and err_text:
            q = (err_text.splitlines()[0] if err_text else "python error")[:160]
            sr = self.stackoverflow.post("search", {"query": q})
            refs = state.setdefault("references", {}).setdefault("stackoverflow", [])
            if isinstance(sr, dict):
                refs.extend(sr.get("results", [])[:3])
            state["so_queried"] = True

        return state
