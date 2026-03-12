# AI Infrastructure & Regional Electricity Demand
### A Forecasting Framework for U.S. Grid Stress

**Alan Lamb** | Lambcast Applied Economics | M.S. Applied Economics, University of Maryland | 2026  
[lambcast.net](https://lambcast.net)

---

## Project Overview

This project quantifies the relationship between data center investment and regional electricity demand growth, then builds a forward-looking grid stress forecast across three major U.S. electricity markets:

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

Project-level large load queue data does not exist as a public bulk download for PJM, ERCOT, or MISO. This absence is documented as an explicit policy finding. The identification strategy uses generation-side queue data (UMD + LBL) as the best available public proxy, and employs four complementary methods to produce a credible estimated range rather than a single overclaimed causal estimate.

---

## Identification Strategy

Four layers, used together to bound the demand effect of data center investment:

**Layer 1 — Panel Regression**  
Conditional association estimate. Outcome: monthly average hourly demand by BA. Primary regressor: `queue_mw_filed_large` (100MW+ projects) lagged 18 months. Controls: HDD, CDD, regional GDP. Fixed effects: BA-level and month-year. Inference via wild cluster bootstrap (Stata `boottest`) — not asymptotic clustered SEs. With 3 clusters, the minimum achievable p-value is 0.125, reported explicitly.

**Layer 2 — Synthetic Control**  
ERCOT as the treated unit. PJM and MISO as baseline donor pool. Treatment date determined by Bai-Perron structural break test. Acknowledged lower bound: PJM and MISO are themselves experiencing data center investment (contaminated donors). Donor pool expanded using LBL data to include low-exposure ISOs (ISONE, NYISO candidates) for robustness.

**Layer 3 — DiD with Low-Exposure Controls**  
BAs classified as low-exposure using cumulative 100MW+ queue filings from LBL data. ISONE and NYISO as primary candidates. Parallel pre-trends tested before estimation.

**Layer 4 — Narrative Validation**  
Known large ERCOT data center energizations overlaid on the synthetic control gap plot. Qualitative confirmation that estimated effects align with documented real-world events.

**Expected ordering of estimates:** Synthetic control (lowest) → Panel regression (middle) → DiD with clean controls (highest). Convergence with this ordering confirms the contamination lower bound story.

---

## Key Early Findings (Phase 1)

- ERCOT demand grew ~27% from 2019 to 2025 (indexed, 2019=100). PJM and MISO remained essentially flat (~102–105).
- ERCOT interconnection queue filings reached 97 GW in 2024 and 93 GW in 2023 — the two largest years on record.
- Battery storage became the dominant new generation type in ERCOT from 2022 onward.
- Analysis panel complete: 252 rows, 3 BAs × 84 months (2019-01 to 2025-12).

---

## Forecasting Model

Association estimates from the panel regression feed a forward-looking pipeline:

| Model | Role |
|---|---|
| ARIMA | Baseline with weather and economic controls |
| Prophet | Handles seasonality and holidays |
| XGBoost | Full feature set from queue pipeline |
| PySpark | Distributed feature engineering on 100M+ row EIA dataset |

Output: regional grid stress forecasts by BA with uncertainty bounds.

---

## Data Sources

| Dataset | Source | Status |
|---|---|---|
| EIA Form 930 hourly demand | eia.gov/opendata | ✅ 184,102 rows (2019–2025) |
| UMD PJM Queue 2008–2024 | UMD Economics (NSF-funded) | ✅ In hand — 7,492 rows, 121 cols |
| LBL Queued Up 2024 | Lawrence Berkeley National Lab | ✅ In hand — 16,093 rows after filter |
| Analysis Panel | Built from above | ✅ data/panel_base.csv — 252 rows, 17 cols |
| NOAA Weather (HDD/CDD) | NCEI Climate Data Online API | ⏳ Pending |
| BEA Regional GDP | BEA Regional Accounts | ⏳ Pending |
| ERCOT Large Load Queue | ERCOT public portal | ❌ PDFs only — documented as data gap |
| PJM Large Load Queue | PJM | ❌ No public dataset |
| MISO Large Load Queue | MISO | ❌ API blocked |

---

## Repository Structure

```
├── data/                          # Raw data files (gitignored)
│   ├── eia_demand_2018_2025.csv   # 184,102 rows EIA Form 930
│   ├── lbnl_queue_data.csv        # LBL queue, filtered to PJM/MISO/ERCOT
│   ├── pjm_main_data_for_public_with_additional_vars.csv
│   └── panel_base.csv             # Core analysis panel — 252 rows, 17 cols
├── scripts/
│   ├── pull_eia_demand.py         # EIA demand data pull
│   ├── explore_eia.py             # Demand charts
│   ├── explore_queue.py           # Queue charts
│   └── build_panel.py             # Builds data/panel_base.csv
├── outputs/                       # Generated charts (tracked by git)
├── notebooks/                     # Jupyter notebooks
├── .env                           # API keys (NOT committed)
├── .gitignore
└── README.md
```

---

## Setup

```bash
# Clone repo
git clone https://github.com/Lambcast/ai-infrastructure-regional-electricity-demand.git
cd ai-electricity-demand

# Install dependencies
pip install requests pandas matplotlib python-dotenv openpyxl

# Set up API key
echo "EIA_API_KEY=your_key_here" > .env

# Pull demand data
python scripts/pull_eia_demand.py

# Exploratory charts
python scripts/explore_eia.py
python scripts/explore_queue.py

# Build analysis panel
python scripts/build_panel.py
```

---

## Tool Stack

| Tool | Role |
|---|---|
| Python | Core language — API pulls, data cleaning, forecasting |
| Stata | Panel regression, wild cluster bootstrap, synthetic control, DiD |
| SQL / BigQuery | Warehouse and querying at scale |
| PySpark | Feature engineering on 100M+ row EIA dataset |
| XGBoost / Prophet / ARIMA | Forecasting model stack |
| Hex | Interactive dashboard |
| Git / GitHub | Version control — feature branch workflow |
| SSRN | Working paper publication |

---

## Project Status

- [x] Phase 1 — Data infrastructure complete (EIA pull, queue data, analysis panel built)
- [ ] Phase 2 — Identification strategy (panel regression, synthetic control, DiD, robustness)
- [ ] Phase 3 — Forecasting model (ARIMA, Prophet, XGBoost, benchmarking)
- [ ] Phase 4 — Pipeline, dashboard, paper, SSRN submission

---

*Document version 5.0 | Updated March 2026 | lambcast.net*
