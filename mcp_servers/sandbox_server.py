from fastapi import FastAPI
import subprocess, tempfile, os, shutil, sys

app = FastAPI(title="MCP - Sandbox")

@app.post("/run")
def run_code(request: dict):
    code = request.get("code", "")
    tmpdir = tempfile.mkdtemp(prefix="mcp_sandbox_")
    path = os.path.join(tmpdir, "main.py")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)

        proc = subprocess.run(
            [sys.executable, path],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            timeout=10
        )
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
            "timed_out": False
        }
    except subprocess.TimeoutExpired as e:
        return {
            "stdout": e.stdout or "",
            "stderr": (e.stderr or "") + "TIMEOUT",
            "returncode": 124,
            "timed_out": True
        }
    except Exception as e:
        # Never 500 — always return JSON
        return {"stdout": "", "stderr": str(e), "returncode": -1, "timed_out": False}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
