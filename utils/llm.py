# utils/llm.py
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

def _get_env(name: str, default=None, required=False):
    val = os.getenv(name, default)
    if required and not val:
        raise RuntimeError(f"Missing env var: {name}")
    return val

def groq_client() -> Groq:
    return Groq(api_key=_get_env("GROQ_API_KEY", required=True))

MODEL = _get_env("GROQ_MODEL")

def chat(messages, max_tokens: int = 1200, temperature: float = 0.2) -> str:
    """
    messages = [{"role": "system"|"user"|"assistant", "content": "..."}]
    Uses single model from .env for all agents.
    """
    client = groq_client()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    content = (resp.choices[0].message.content or "").strip()
    return _strip_code_fences(content)

def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        parts = t.split("```")
        if len(parts) >= 2:
            body = parts[1].strip()
            lines = body.splitlines()
            if lines and len(lines[0]) <= 20 and lines[0].isalpha():
                body = "\n".join(lines[1:])
            return body
    return t
