# utils/mcp_client.py
import requests
from urllib.parse import urljoin

class MCPClient:
    """
    Minimal HTTP client for our MCP microservers.
    - Provides .get(), .post(), and .request()
    - Keeps .call(endpoint, payload) for backward compatibility (aliases .post()).
    """
    def __init__(self, base_url: str, timeout: int = 30):
        # ensure a trailing slash so urljoin works reliably
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout

    def _url(self, path: str) -> str:
        # accept "/pytest" or "pytest"
        return urljoin(self.base_url, path.lstrip("/"))

    def request(self, method: str, path: str, json: dict | None = None):
        url = self._url(path)
        try:
            resp = requests.request(method.upper(), url, json=json, timeout=self.timeout)
            resp.raise_for_status()
            try:
                return resp.json()
            except Exception:
                return {"raw": resp.text, "status_code": resp.status_code}
        except requests.HTTPError as e:
            # include server response body for easier debugging
            body = getattr(e.response, "text", "")
            return {"error": str(e), "status_code": e.response.status_code if e.response else None, "body": body}
        except Exception as e:
            return {"error": str(e)}

    def get(self, path: str, params: dict | None = None):
        url = self._url(path)
        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            try:
                return resp.json()
            except Exception:
                return {"raw": resp.text, "status_code": resp.status_code}
        except requests.HTTPError as e:
            body = getattr(e.response, "text", "")
            return {"error": str(e), "status_code": e.response.status_code if e.response else None, "body": body}
        except Exception as e:
            return {"error": str(e)}

    def post(self, path: str, json: dict | None = None):
        return self.request("POST", path, json=json)

    # --- Backward compatibility with older agents ---
    def call(self, endpoint: str, payload: dict):
        """Alias for .post(endpoint, json=payload)."""
        return self.post(endpoint, payload)
# ---------------------------------------------------