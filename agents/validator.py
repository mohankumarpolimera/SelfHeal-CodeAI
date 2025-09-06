from utils.mcp_client import MCPClient

class ValidatorAgent:
    def __init__(self, sandbox_url: str, tester_url: str):
        self.sandbox = MCPClient(sandbox_url)
        self.tester = MCPClient(tester_url)

    def validate_code(self, state: dict):
        code = state.get("code")
        sandbox_result = self.sandbox.call("run", {"code": code})
        test_result = self.tester.call("pytest", {"code": code})

        if "error" in sandbox_result or "error" in test_result:
            state["test_results"] = "Fail ❌"
            state["errors"] = [sandbox_result, test_result]
        else:
            state["test_results"] = "Pass ✅"
            state["errors"] = []

        return state
