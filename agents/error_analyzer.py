from utils.mcp_client import MCPClient
from utils.sandbox_runner import run_script
from utils.test_runner import run_pytest_on_files

def _strip_fences(code: str) -> str:
    t = code.strip()
    if t.startswith("```"):
        parts = t.split("```")
        if len(parts) >= 2:
            body = parts[1].strip()
            lines = body.splitlines()
            if lines and len(lines[0]) <= 20 and lines[0].isalpha():
                body = "\n".join(lines[1:])
            return body
    return code

class ErrorAnalyzerAgent:
    """
    Runs code via MCP sandbox & tester, with local fallback.
    Also queries MCP docs/stackoverflow if errors are found.
    Outputs:
      state["errors"]: list[str]
      state["analyzer_output"]: {"sandbox": {...}, "tests": {...}}
      state["references"]: {"stackoverflow": [...], "docs": {...?}}  (optional)
    """
    def __init__(self):
        self.sandbox = MCPClient("http://127.0.0.1:8001")
        self.tester  = MCPClient("http://127.0.0.1:8002")
        self.so      = MCPClient("http://127.0.0.1:8003")  # stackoverflow_server.py
        self.docs    = MCPClient("http://127.0.0.1:8004")  # docs_server.py

    def _run_mcp_sandbox(self, code: str):
        return self.sandbox.call("run", {"code": code})

    def _run_mcp_pytest(self, code: str):
        return self.tester.call("pytest", {"code": code})

    def _fallback_sandbox(self, code: str):
        return run_script(code, timeout=10)

    def _fallback_pytest(self, code: str):
        return run_pytest_on_files({"main.py": code}, timeout=20, create_default_test=True)

    def analyze_error(self, state: dict):
        code = _strip_fences(state.get("code", "") or "")

        # 1) Try MCP sandbox; fallback if needed
        sb = self._run_mcp_sandbox(code)
        if not isinstance(sb, dict) or "returncode" not in sb:
            sb = self._fallback_sandbox(code)

        # 2) Try MCP pytest; fallback if needed
        tr = self._run_mcp_pytest(code)
        if not isinstance(tr, dict) or ("returncode" not in tr and "passed" not in tr):
            tr = self._fallback_pytest(code)

        errs = []
        # runtime error?
        if sb.get("timed_out") or sb.get("error") or (sb.get("returncode", 0) != 0):
            msg = (sb.get("stderr") or sb.get("error") or sb.get("stdout") or "").strip()
            if msg:
                errs.append(msg)

        # pytest failure?
        if (
            tr.get("error") or tr.get("timed_out") or
            (tr.get("returncode", 0) not in (0, None)) or
            (tr.get("passed") is False)
        ):
            combined = ((tr.get("stderr") or "") + "\n" + (tr.get("stdout") or "")).strip()
            if combined:
                errs.append(combined)

        state["errors"] = [e for e in errs if e]
        state["analyzer_output"] = {"sandbox": sb, "tests": tr}

        # 3) If errors, enrich with MCP knowledge (StackOverflow + Docs)
        refs = {}
        if state["errors"]:
            query = (state["errors"][0] or "")[:200]
            so_res = self.so.call("search", {"query": query, "pagesize": 5})
            if isinstance(so_res, dict) and so_res.get("ok"):
                refs["stackoverflow"] = so_res.get("results", [])

            # very light heuristic: if ImportError, try docs on the missing pkg
            import_pkg = None
            for line in query.splitlines():
                if "No module named" in line:
                    import_pkg = line.split("No module named")[-1].strip().strip("'\" .")
                    break
            if import_pkg:
                doc_res = self.docs.call("pkg_info", {"package": import_pkg})
                if isinstance(doc_res, dict) and doc_res.get("ok"):
                    refs["docs"] = doc_res

        state["references"] = refs
        return state
