"""
utils/test_runner.py

Helper to run pytest on a set of files. The caller provides a mapping filename->content.
A temporary directory is created, files are written, and `pytest -q` is invoked in that dir.

Returns:
  {
    "passed": bool,
    "returncode": int,
    "stdout": str,
    "stderr": str,
    "timed_out": bool,
    "error": optional_exception_str
  }
"""

import tempfile
import subprocess
import sys
import os
import textwrap
import shutil
import traceback

# a small fallback test if generator doesn't provide tests
DEFAULT_TEST = textwrap.dedent("""
    from fastapi.testclient import TestClient
    try:
        from app import app
    except Exception:
        app = None

    def test_health_exists():
        assert app is not None, "app not found; generator should provide app.py with FastAPI app named 'app'"
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
""")

def run_pytest_on_files(files: dict, timeout: int = 30, create_default_test: bool = True) -> dict:
    """
    files: dict mapping filename -> content
    """
    tempdir = tempfile.mkdtemp(prefix="selfheal_test_")
    try:
        # write files
        for fname, content in files.items():
            # ensure subdirs
            full = os.path.join(tempdir, fname)
            os.makedirs(os.path.dirname(full), exist_ok=True) if os.path.dirname(fname) else None
            with open(full, "w", encoding="utf-8") as f:
                f.write(content)

        # check if any test_*.py exists, otherwise write default
        tests_present = any(name.startswith("test_") and name.endswith(".py") for name in files.keys())
        if not tests_present and create_default_test:
            with open(os.path.join(tempdir, "test_app.py"), "w", encoding="utf-8") as f:
                f.write(DEFAULT_TEST)

        # run pytest in tempdir
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=tempdir,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "passed": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "timed_out": False,
            "error": None
        }
    except subprocess.TimeoutExpired as e:
        return {"passed": False, "returncode": 124, "stdout": getattr(e, "stdout", ""), "stderr": getattr(e, "stderr", ""), "timed_out": True, "error": "TIMEOUT"}
    except Exception:
        return {"passed": False, "returncode": -1, "stdout": "", "stderr": "", "timed_out": False, "error": traceback.format_exc()}
    finally:
        try:
            shutil.rmtree(tempdir)
        except Exception:
            pass
