from utils.llm import chat

class CodeGeneratorAgent:
    def generate_code(self, state: dict):
        req = state.get("user_request", "").strip()
        messages = [
            {"role": "system", "content": "You generate clean, runnable Python. Return only full code, no explanations."},
            {"role": "user", "content": (
                "Task:\n"
                f"{req}\n\n"
                "Requirements:\n"
                "- Return ONE complete Python file as plain text.\n"
                "- If building a web API, expose FastAPI 'app' and a '/health' route (200 OK).\n"
                "- Avoid network calls and heavy deps.\n"
            )},
        ]
        code = chat(messages, max_tokens=1500, temperature=0.2)
        state["code"] = code
        return state
