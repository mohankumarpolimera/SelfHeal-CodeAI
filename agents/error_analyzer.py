import os
from groq import Groq

class ErrorAnalyzerAgent:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def analyze_error(self, state: dict):
        errors = state.get("errors", [])
        error_text = str(errors)
        prompt = f"Analyze the following Python errors and explain root cause:\n{error_text}"
        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300
        )
        explanation = response.choices[0].message.content
        state["explanation"] = explanation
        return state
