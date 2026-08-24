import requests
from config import API_BASE_URL, API_KEY


class AccountingAPIClient:
    def __init__(self):
        self.base_url = API_BASE_URL
        self.headers = {
            "X-API-Key": API_KEY,
            "Content-Type": "application/json",
        }

    def health_check(self) -> bool:
        """Check API liveness. /health does NOT require authentication."""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=5)
            return resp.status_code == 200
        except (requests.ConnectionError, requests.Timeout):
            return False

    def get_partners(self) -> list[dict]:
        """Fetch supplier master data. Requires API key."""
        resp = requests.get(
            f"{self.base_url}/partners",
            headers={"X-API-Key": API_KEY},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["data"]["partners"]

    def register_invoice(self, data: dict) -> tuple[int, dict]:
        """Register an invoice. Returns (status_code, response_body)."""
        try:
            resp = requests.post(
                f"{self.base_url}/invoices",
                headers=self.headers,
                json=data,
                timeout=15,
            )
            return resp.status_code, resp.json()
        except requests.ConnectionError as e:
            return 0, {"error": {"code": "CONNECTION_ERROR", "message": str(e)}}
        except requests.Timeout:
            return 0, {"error": {"code": "TIMEOUT", "message": "API request timed out"}}
        except Exception as e:
            return 0, {"error": {"code": "UNKNOWN_ERROR", "message": str(e)}}
