from utils.mcp_client import MCPClient

class MemoryAgent:
    def __init__(self, memory_url: str):
        self.memory = MCPClient(memory_url)

    def store(self, state: dict):
        errors = state.get("errors", [])
        fix = state.get("fixed_code", "")
        if errors and fix:
            self.memory.call("store", {"errors": errors, "fix": fix})
        return state
