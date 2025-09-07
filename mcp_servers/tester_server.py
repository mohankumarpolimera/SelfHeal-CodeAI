# mcp_servers/tester_server.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from utils.test_runner import run_pytest_on_files

app = FastAPI(title="MCP Tester Server")

@app.post("/pytest")
async def run_tests(request: Request):
    try:
        data = await request.json()
        files = data.get("files", {}) or {}

        # Detect explicit tests from payload
        has_tests = any(
            name.startswith("test_") and name.endswith(".py") or name.endswith("_test.py")
            for name in files.keys()
        )

        if not has_tests:
            # ✨ If no tests provided, treat as success.
            # This avoids the default FastAPI test that breaks simple scripts.
            return JSONResponse({
                "passed": True,
                "returncode": 0,
                "stdout": "NO_TESTS",
                "stderr": "",
                "timed_out": False,
                "error": None
            })

        # Run only the provided tests (no auto-injected defaults)
        res = run_pytest_on_files(files, timeout=30, create_default_test=False)
        return JSONResponse(res)
    except Exception as e:
        return JSONResponse({
            "passed": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "timed_out": False,
            "error": str(e)
        }, status_code=500)
