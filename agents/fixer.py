from utils.llm import chat

class FixerAgent:
    def fix_code(self, state: dict):
        code = state.get("code", "")
        errors = state.get("errors", [])
        issues = state.get("validation_issues", [])
        problem_text = ""
        if errors:
            problem_text += "Errors:\n" + ("\n\n".join([str(e) for e in errors]))
        if issues:
            problem_text += ("\n\nValidation issues:\n" + "\n".join([str(i) for i in issues]))

        messages = [
            {"role": "system", "content": "You are a precise Python debugging assistant. Return the corrected full file only."},
            {"role": "user", "content": (
                "Here is the current code:\n"
                "```\n" + code + "\n```\n\n"
                f"Problems:\n{problem_text}\n\n"
                "Fix the code. Return the complete corrected file as plain text, no commentary."
            )},
        ]
        fixed = chat(messages, max_tokens=1500, temperature=0.1)
        state["code"] = fixed
        state.setdefault("fix_attempts", []).append({
            "summary": "Auto-fix applied",
            "truncated_problems": problem_text[:500]
        })
        return state
