import requests

class MCPClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def call(self, endpoint: str, payload: dict):
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
