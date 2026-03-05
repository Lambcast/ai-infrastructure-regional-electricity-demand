# AI Infrastructure & Regional Electricity Demand
### A Forecasting Framework for U.S. Grid Stress

**Alan Lamb** | Lambcast Applied Economics | M.S. Applied Economics, University of Maryland | 2026  
[lambcast.net](https://lambcast.net)

---

## Project Overview

This project quantifies the relationship between data center investment and regional electricity demand growth, then builds a forward-looking grid stress forecast for three major U.S. electricity markets:

- **PJM** — Mid-Atlantic / Midwest (largest data center market in the world)
- **ERCOT** — Texas (fastest-growing data center market)
- **MISO** — Southeast / Midwest (high-growth corridor)

The project produces three deliverables:
1. **NBER-style working paper** — posted on lambcast.net and submitted to SSRN
2. **Hex dashboard** — interactive regional grid stress forecast by balancing authority
3. **5 blog posts** on lambcast.net documenting the build process

---

## Research Question

> How much has data center investment driven regional electricity demand growth — and can we build a model that forecasts future grid stress from the existing investment pipeline?

---

## Design Note

The original project design called for a difference-in-differences causal identification using load-side interconnection queue filings as the treatment variable. Research confirmed that **project-level large load queue data does not exist as a public downloadable dataset** for PJM, ERCOT, or MISO. The paper documents this data gap as an explicit policy finding and proceeds with a rigorous forecasting framework using generation-side queue data as the best available proxy.

---

## Data Sources

| Dataset | Source | Status |
|---|---|---|
| EIA Form 930 hourly demand | eia.gov/opendata | ✅ 735,773 rows pulled |
| UMD PJM Queue 2008–2020 | UMD Economics Dept. (NSF-funded) | ✅ Confirmed available |
| LBL Queued Up 2024 | Lawrence Berkeley National Lab | ✅ In hand |
| NOAA Weather (HDD/CDD) | NCEI Climate Data Online API | Pending |
| BEA Regional GDP | BEA Regional Accounts | Pending |

---

## Repository Structure

```
├── data/                    # Raw data files (not tracked by git — too large)
│   └── eia_demand_2018_2025.csv   # 735,773 rows EIA Form 930
├── scripts/
│   ├── test_eia.py          # API connection test
│   ├── pull_eia_demand.py   # EIA demand data pull
│   └── explore_eia.py       # Exploratory analysis + charts
├── outputs/                 # Generated charts and figures
├── notebooks/               # Jupyter notebooks (analysis)
├── .env                     # API keys (NOT committed to git)
├── .gitignore
└── README.md
```

---

## Setup

```bash
# Clone repo
git clone https://github.com/Lambcast/ai-infrastructure-regional-electricity-demand.git
cd ai-infrastructure-regional-electricity-demand

# Install dependencies
pip install requests pandas matplotlib python-dotenv

# Set up API key
echo "EIA_API_KEY=your_key_here" > .env

# Test connection
python scripts/test_eia.py

# Pull demand data (takes a few minutes)
python scripts/pull_eia_demand.py

# Run exploratory analysis
python scripts/explore_eia.py
```

---

## Tool Stack

| Tool | Role |
|---|---|
| Python | Core language — API pulls, modeling |
| SQL / BigQuery | Warehouse and querying at scale |
| PySpark | Feature engineering on 100M+ row dataset |
| Stata | Panel regression, fixed effects |
| XGBoost / Prophet / ARIMA | Forecasting model stack |
| Hex | Interactive dashboard |
| Git / GitHub | Version control |
| SSRN | Working paper publication |

---

## Project Status

- [x] Phase 1 — Data Infrastructure (in progress)
- [ ] Phase 2 — Descriptive Analysis & Panel Regression
- [ ] Phase 3 — Forecasting Model
- [ ] Phase 4 — Dashboard, Paper & Publication

---

*Document version 3.0 | Updated March 2026*
