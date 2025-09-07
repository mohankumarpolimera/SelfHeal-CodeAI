# agents/validator.py
import ast
from typing import Optional

try:
    # Optional: if you later want to use MCP here, the clients are ready.
    from utils.mcp_client import MCPClient  # noqa
except Exception:
    MCPClient = None  # type: ignore


class ValidatorAgent:
    """
    Lightweight validator for the final pass:
      - Hard-fails on syntax errors only.
      - Style/security suggestions => warnings (do NOT block).
    Accepts optional MCP endpoints but doesn't re-run code to avoid loops;
    runtime/tests are already covered by ErrorAnalyzer.
    """

    def __init__(self, sandbox_url: Optional[str] = None, tester_url: Optional[str] = None):
        self.sandbox_url = sandbox_url
        self.tester_url = tester_url
        # If you ever want to use MCP here:
        # self.sandbox = MCPClient(sandbox_url) if (MCPClient and sandbox_url) else None
        # self.tester  = MCPClient(tester_url)  if (MCPClient and tester_url)  else None

    def validate_code(self, state: dict):
        code = state.get("code", "") or ""
        issues = []
        warnings = []

        # 1) Syntax check => ONLY hard failure
        try:
            ast.parse(code)
            syntax_ok = True
        except Exception as e:
            syntax_ok = False
            issues.append(f"Syntax: {e}")

        # 2) (Optional) basic policy checks → warnings only
        # Keep these as warnings so we don't churn in fix loops for trivial style.
        if "print(" in code:
            warnings.append("Style: found print(); prefer logging for apps (warning only).")
        if "eval(" in code or "exec(" in code:
            warnings.append("Security: avoid eval/exec when possible (warning only).")

        # Store results
        state["validation_issues"] = issues           # block only if non-empty
        state["validation_warnings"] = warnings      # non-blocking
        state["validated"] = syntax_ok and (len(issues) == 0)
        return state
