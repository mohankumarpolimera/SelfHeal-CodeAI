from fastapi import FastAPI
import subprocess, tempfile, os

app = FastAPI()

@app.post("/pytest")
def run_tests(request: dict):
    code = request.get("code", "")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tmp:
        tmp.write(code.encode())
        tmp.flush()
        try:
            result = subprocess.run(
                ["pytest", tmp.name],
                capture_output=True,
                text=True,
                timeout=5
            )
            return {"stdout": result.stdout, "stderr": result.stderr, "status": result.returncode}
        except Exception as e:
            return {"error": str(e)}
        finally:
            os.unlink(tmp.name)
