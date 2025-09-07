# agents/validator.py
import ast
from typing import Optional

try:
    from utils.mcp_client import MCPClient  # noqa: F401
except Exception:
    MCPClient = None  # type: ignore

HARD_KWS = ("Syntax", "Error", "Exception", "ImportError", "NameError", "ModuleNotFoundError")

def _has_hard_issue(items) -> bool:
    if not items:
        return False
    for it in items:
        s = str(it)
        if any(kw in s for kw in HARD_KWS):
            return True
    return False

class ValidatorAgent:
    def __init__(self, sandbox_url: Optional[str] = None, tester_url: Optional[str] = None):
        self.sandbox_url = sandbox_url
        self.tester_url = tester_url

    def validate_code(self, state: dict):
        dbg = state.setdefault("debug", [])
        dbg.append({"node": "validate", "attempts": int(state.get("attempts", 0))})

        code = state.get("code", "") or ""
        issues, warnings = [], []

        try:
            ast.parse(code)
            syntax_ok = True
        except Exception as e:
            syntax_ok = False
            issues.append(f"Syntax: {e}")

        if "eval(" in code or "exec(" in code:
            warnings.append("Security: avoid eval/exec (warning).")
        if "print(" in code:
            warnings.append("Style: prefer logging over print() (warning).")

        hard_fail = (not syntax_ok) or _has_hard_issue(issues)
        validated = not hard_fail

        dbg.append({"node": "validate_out", "validated": validated, "issues": issues, "warnings": warnings})

        return {
            **state,
            "validation_issues": issues,
            "validation_warnings": warnings,
            "validated": validated,
        }
