"""
utils/sandbox_runner.py

Small helper to execute a single Python script safely (best-effort).
- Writes the code to a temporary file and runs python on it.
- Applies basic resource limits on POSIX (RLIMIT_CPU, RLIMIT_AS).
- Returns a dict { stdout, stderr, returncode, timed_out, error }.
"""

import tempfile
import subprocess
import sys
import os
import traceback

try:
    import resource
    HAS_RESOURCE = True
except Exception:
    HAS_RESOURCE = False

def _set_limits(cpu_seconds: int, memory_mb: int):
    """
    Use as preexec_fn in subprocess on POSIX to limit CPU and memory.
    """
    if not HAS_RESOURCE:
        return
    # limit CPU time (seconds)
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
    # limit address space (bytes)
    mem_bytes = memory_mb * 1024 * 1024
    try:
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    except Exception:
        # some systems may not allow changing RLIMIT_AS
        pass

def run_script(code: str, timeout: int = 5, cpu_seconds: int = 5, memory_mb: int = 200) -> dict:
    """
    Execute a single python script and return outputs.

    Args:
      code: python code string
      timeout: wall time limit for subprocess.run
      cpu_seconds: RLIMIT_CPU (POSIX only)
      memory_mb: RLIMIT_AS approx (POSIX only)

    Returns:
      dict with keys:
        - stdout, stderr, returncode, timed_out (bool), error (exception string)
    """
    fd = None
    path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            f.flush()
            path = f.name

        preexec = (lambda: _set_limits(cpu_seconds, memory_mb)) if HAS_RESOURCE else None

        proc = subprocess.run(
            [sys.executable, path],
            capture_output=True,
            text=True,
            timeout=timeout,
            preexec_fn=preexec
        )
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
            "timed_out": False,
            "error": None
        }
    except subprocess.TimeoutExpired as e:
        return {"stdout": getattr(e, "stdout", ""), "stderr": getattr(e, "stderr", ""), "returncode": 124, "timed_out": True, "error": "TIMEOUT"}
    except Exception as ex:
        return {"stdout": "", "stderr": "", "returncode": -1, "timed_out": False, "error": traceback.format_exc()}
    finally:
        try:
            if path and os.path.exists(path):
                os.unlink(path)
        except Exception:
            pass
