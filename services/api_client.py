import requests
from config import API_BASE_URL, API_KEY

class AccountingAPIClient:
    def __init__(self):
        self.base_url = API_BASE_URL
        self.headers = {
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        }

    def get_partners(self):
        resp = requests.get(f"{self.base_url}/partners", headers={"X-API-Key": API_KEY})
        return resp.json()['data']['partners'] if resp.status_code == 200 else []

    def register_invoice(self, data):
        resp = requests.post(f"{self.base_url}/invoices", headers=self.headers, json=data)
        return resp.status_code, resp.json()