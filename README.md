# AI Infrastructure & Regional Electricity Demand
### A Causal Forecasting Framework for U.S. Grid Stress

**Alan Lamb** | Lambcast Applied Economics | M.S. Applied Economics, University of Maryland | 2026  
[lambcast.net](https://lambcast.net)

---

## Project Overview

This project estimates the causal effect of data center investment on regional electricity demand growth, then builds a forward-looking grid stress forecast. It combines difference-in-differences causal identification with a large-scale forecasting pipeline across three major U.S. electricity markets:

- **PJM** — Mid-Atlantic / Midwest (largest data center market in the world)
- **ERCOT** — Texas (fastest-growing data center market)
- **MISO** — Southeast / Midwest (high-growth corridor)

The project produces three deliverables:
1. **NBER-style working paper** — posted on lambcast.net and submitted to SSRN
2. **Hex dashboard** — interactive regional grid stress forecast by balancing authority
3. **5 blog posts** on lambcast.net documenting the build process

---

## Research Question

> Do large data center interconnection requests causally shift regional electricity load growth — and can we build a model that forecasts future grid stress from the existing investment pipeline?

---

## Methodology

**Primary: Difference-in-Differences**  
Compares electricity demand growth in balancing authority subregions that receive large interconnection requests against comparable regions that do not, before and after the filing date.

**Secondary: Event Study**  
Plots dynamic treatment effects around each interconnection filing date to test the parallel trends assumption and trace how quickly demand effects materialize.

**Forecasting Pipeline**  
The causal estimate feeds a forward-looking model using ARIMA, Prophet, and XGBoost benchmarked against each other, with PySpark for feature engineering at scale.

---

## Design Note

A thorough search confirms no existing paper uses interconnection queue filings as a DiD treatment variable with EIA Form 930 hourly demand as the outcome. This project fills that gap. Project-level large load queue data does not exist as a public bulk download for any of the three target markets — this absence is documented as an explicit policy finding. The causal identification uses generation-side queue data (UMD + LBL) as the treatment variable, which is the best available public proxy.

---

## Data Sources

| Dataset | Source | Status |
|---|---|---|
| EIA Form 930 hourly demand | eia.gov/opendata | ✅ 153,587 rows pulled (2019–2025) |
| UMD PJM Queue 2008–2020 | UMD Economics Dept. (NSF-funded) | ✅ In hand |
| LBL Queued Up 2025 | Lawrence Berkeley National Lab | ✅ In hand |
| NOAA Weather (HDD/CDD) | NCEI Climate Data Online API | Pending |
| BEA Regional GDP | BEA Regional Accounts | Pending |

---

## Repository Structure
```
├── data/                    # Raw data files (not tracked by git)
│   ├── eia_demand_2018_2025.csv   # 153,587 rows EIA Form 930
│   ├── pjm_main_data_for_public.csv  # UMD PJM queue 2008–2020
│   └── Queued_Up_2025_Data.xlsx   # LBL all-ISO queue through 2024
├── scripts/
│   ├── test_eia.py          # API connection test
│   ├── pull_eia_demand.py   # EIA demand data pull
│   └── explore_eia.py       # Exploratory analysis + charts
├── outputs/                 # Generated charts and figures
├── notebooks/               # Jupyter notebooks
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
pip install requests pandas matplotlib python-dotenv gridstatus

# Set up API key
echo "EIA_API_KEY=your_key_here" > .env

# Test connection
python scripts/test_eia.py

# Pull demand data (takes ~15 minutes)
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
| Stata | DiD and event study models |
| XGBoost / Prophet / ARIMA | Forecasting model stack |
| Hex | Interactive dashboard |
| Git / GitHub | Version control |
| SSRN | Working paper publication |

---

## Project Status

- [x] Phase 1 — Data Infrastructure (in progress)
- [ ] Phase 2 — Descriptive Analysis & Panel Regression
- [ ] Phase 3 — Event Study & Robustness
- [ ] Phase 4 — Forecasting, Dashboard & Publication

---

*Document version 3.0 | Updated March 2026*