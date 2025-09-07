# agents/memory.py
from utils.mcp_client import MCPClient

class MemoryAgent:
    def __init__(self, memory_url: str):
        self.memory = MCPClient(memory_url)

    def store(self, state: dict):
        state.setdefault("debug", []).append({"node": "memory", "attempts": int(state.get("attempts", 0))})

        errors = "\n---\n".join([str(e) for e in (state.get("errors") or [])])
        code = state.get("code", "")

        if not code:
            return state

        payload = {
            "error_text": errors or "no-errors",
            "fix": {"files": {"main.py": code}},
        }
        try:
            resp = self.memory.call("store", payload)
            state["memory_write"] = resp
        except Exception:
            # don't block the flow on memory failures
            pass
        return state
