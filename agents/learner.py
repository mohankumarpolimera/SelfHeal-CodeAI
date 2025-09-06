from utils.mcp_client import MCPClient

class LearnerAgent:
    def __init__(self):
        self.client = MCPClient("http://127.0.0.1:8005")  # chroma_server

    async def learn_patterns(self):
        # Fetch all stored experiences
        entries = await self.client.call("chroma", {"action": "fetch_all"})
        
        patterns = {"common_errors": {}, "fix_strategies": {}}

        for entry in entries.get("data", []):
            error = entry.get("error")
            fix = entry.get("fix")

            if error and fix:
                patterns["common_errors"][error] = fix
                patterns["fix_strategies"][fix] = error

        return patterns
