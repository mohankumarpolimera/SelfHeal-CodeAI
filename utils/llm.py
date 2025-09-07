# utils/llm.py
import os
from dotenv import load_dotenv
import groq
from groq import Groq

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    raise RuntimeError("Missing GROQ_API_KEY in environment (.env)")

# Use the same model for all agents (from .env), with a safe default
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Reuse a single client across calls
_client = Groq(api_key=API_KEY)

class ChatRateLimited(Exception):
    """Raised when Groq returns HTTP 429 (rate limit)."""
    pass

def chat(messages, max_tokens: int = 1200, temperature: float = 0.2) -> str:
    """
    messages = [{"role": "system"|"user"|"assistant", "content": "..."}]
    Uses the single model defined by GROQ_MODEL for all agents.
    Raises ChatRateLimited on 429 so agents can exit gracefully.
    """
    try:
        resp = _client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        content = (resp.choices[0].message.content or "").strip()
        return _strip_code_fences(content)
    except groq.RateLimitError as e:
        # Let agents catch this and force 'giveup' to avoid loops
        raise ChatRateLimited(str(e))

def _strip_code_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        parts = t.split("```")
        if len(parts) >= 2:
            body = parts[1].strip()
            # If first line is a language tag, drop it
            lines = body.splitlines()
            if lines and len(lines[0]) <= 20 and lines[0].isalpha():
                body = "\n".join(lines[1:])
            return body
    return t
