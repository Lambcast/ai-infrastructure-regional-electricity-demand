"""
test_eia.py
-----------
Quick sanity check: confirms EIA API key is loaded and the endpoint is live.
Run from project root: python scripts/test_eia.py
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("EIA_API_KEY")

if not API_KEY:
    raise ValueError("EIA_API_KEY not found. Check your .env file.")

url = "https://api.eia.gov/v2/electricity/rto/region-data/data/"

params = {
    "api_key": API_KEY,
    "frequency": "hourly",
    "data[0]": "value",
    "facets[respondent][]": "ERCO",
    "facets[type][]": "D",
    "start": "2024-01-01T00",
    "end": "2024-01-02T00",
    "length": 5,
}

response = requests.get(url, params=params)

if response.status_code == 200:
    data = response.json()
    total = data.get("response", {}).get("total", "unknown")
    print(f"✅ EIA API connection successful. Records available: {total}")
else:
    print(f"❌ API call failed. Status code: {response.status_code}")
    print(response.text)
