"""
pull_eia_donor_bas.py
---------------------
Pulls EIA Form 930 hourly demand for ISNE, NYIS, and SWPP (2019-2025).
These are the synthetic control donor pool BAs.
Appends to data/eia_demand_2018_2025.csv without re-pulling ERCO/PJM/MISO.

Run from project root: python scripts/pull_eia_donor_bas.py
"""

import requests
import os
import pandas as pd
import time
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("EIA_API_KEY")
REGIONS = ["ISNE", "NYIS", "SWPP"]
YEARS = list(range(2019, 2026))
BASE_URL = "https://api.eia.gov/v2/electricity/rto/region-data/data/"

def pull_region_year(region, year):
    start = f"{year}-01-01T00"
    end = f"{year}-12-31T23"
    all_records = []
    offset = 0
    page_size = 5000
    while True:
        params = {
            "api_key": API_KEY,
            "frequency": "hourly",
            "data[0]": "value",
            "facets[respondent][]": region,
            "facets[type][]": "D",
            "start": start,
            "end": end,
            "length": page_size,
            "offset": offset
        }
        try:
            response = requests.get(BASE_URL, params=params, timeout=60)
            try:
                data = response.json()
            except Exception:
                print(f"  Bad response, retrying in 30s...")
                time.sleep(30)
                continue
            records = data["response"]["data"]
            total = int(data["response"]["total"])
            all_records.extend(records)
            offset += len(records)
            print(f"  {region} {year}: pulled {offset}/{total} records")
            if offset >= total or len(records) == 0:
                break
            time.sleep(0.5)
        except Exception as e:
            print(f"  Error: {e}, retrying in 30s...")
            time.sleep(30)
    return all_records

def main():
    all_data = []
    for region in REGIONS:
        for year in YEARS:
            print(f"Pulling {region} {year}...")
            records = pull_region_year(region, year)
            all_data.extend(records)
            time.sleep(1)

    df = pd.DataFrame(all_data)
    df = df.rename(columns={
        "period": "datetime",
        "respondent": "region",
        "respondent-name": "region_name",
        "type": "data_type",
        "type-name": "data_type_name",
        "value": "mwh",
        "value-units": "units"
    })

    # Append to existing CSV
    existing = pd.read_csv("data/eia_demand_2018_2025.csv")
    combined = pd.concat([existing, df], ignore_index=True)
    combined.to_csv("data/eia_demand_2018_2025.csv", index=False)

    print(f"\nDone. Added {len(df):,} records.")
    print(f"Total records in file: {len(combined):,}")
    print(f"Regions now in file: {combined['region'].unique().tolist()}")

if __name__ == "__main__":
    main()