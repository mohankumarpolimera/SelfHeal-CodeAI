# agents/fixer.py
import difflib
import re
from typing import Dict, Any, List
from utils.llm import chat, ChatRateLimited

# extract code from a ```python ... ``` block if the model returns fences
_CODE_FENCE_RE = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)

def _extract_code(text: str) -> str:
    if not text:
        return ""
    m = _CODE_FENCE_RE.search(text)
    return (m.group(1) if m else text).strip()


class FixerAgent:
    """
    - Calls the LLM to repair code.
    - If the returned code is IDENTICAL to the previous code, we increment a
      no-change streak and set `force_giveup=True` (so the graph exits via memory).
    - On LLM/rate-limit failure we also set `force_giveup=True`.
    """

    def fix_code(self, state: Dict[str, Any]):
        debug = state.setdefault("debug", [])
        debug.append({"node": "fix", "attempts": int(state.get("attempts", 0))})

        errors: List[str] = state.get("errors") or []
        if not errors:
            # nothing to fix
            debug[-1].update({"skipped": True, "reason": "no_errors"})
            return state

        current = state.get("code", "") or ""
        first_error = (errors[0] or "")[:2000]  # keep prompt small/safe

        prompt = (
            "You repair a single-file Python FastAPI app named app.py.\n"
            "Return ONLY the full corrected file content. Do not add explanations.\n\n"
            "Current code:\n```python\n" + current + "\n```\n\n"
            "Observed error (from tests/sandbox):\n" + first_error + "\n"
        )

        try:
            fixed_text = chat(
                [
                    {"role": "system", "content": "You are a meticulous Python fixer."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1500,
                temperature=0.1,
            )
        except ChatRateLimited as e:
            # stop the loop immediately on rate limit
            fa = state.get("fix_attempts", [])
            fa.append({"status": "rate_limited", "message": str(e)})
            state["fix_attempts"] = fa
            state["force_giveup"] = True
            state["giveup_reason"] = state.get("giveup_reason") or "llm_rate_limited"
            debug[-1].update({"status": "rate_limited"})
            return state
        except Exception as e:
            fa = state.get("fix_attempts", [])
            fa.append({"status": "llm_failed", "message": str(e)})
            state["fix_attempts"] = fa
            state["force_giveup"] = True
            state["giveup_reason"] = state.get("giveup_reason") or f"llm_error: {e}"
            debug[-1].update({"status": "llm_failed", "error": str(e)})
            return state

        # postprocess model output
        new_code = _extract_code(fixed_text) or ""
        changed = new_code.strip() != current.strip()

        # prepare diff for UI/debug
        udiff = "\n".join(
            difflib.unified_diff(
                current.splitlines(), new_code.splitlines(),
                fromfile="before", tofile="after", lineterm=""
            )
        )

        fa = state.get("fix_attempts", [])
        if not changed:
            # break the loop if model didn't change anything
            state["nochange_streak"] = int(state.get("nochange_streak", 0)) + 1
            fa.append({"status": "no_change", "changed": False, "diff": udiff[:5000]})
            state["fix_attempts"] = fa
            state["force_giveup"] = True
            state["giveup_reason"] = state.get("giveup_reason") or "no_change_from_fixer"
            debug[-1].update({"status": "no_change", "nochange_streak": state["nochange_streak"]})
            return state

        # accept the change
        state["code"] = new_code
        state["nochange_streak"] = 0
        fa.append({"status": "ok", "changed": True, "diff": udiff[:5000]})
        state["fix_attempts"] = fa
        debug[-1].update({"status": "ok", "changed": True, "len": len(new_code)})
        return state
