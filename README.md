# AI Infrastructure and Regional Electricity Demand
## Evidence from U.S. Interconnection Queues

**Alan Lamb** | M.S. Applied Economics, University of Maryland | 2026  
[lambcast.net](https://lambcast.net) | [SSRN](https://ssrn.com/abstract=6446446) | [Replication Data (Harvard Dataverse)](https://doi.org/10.7910/DVN/F8JV2T)

---

## Overview

This project estimates the association between large-scale data center
investment and regional electricity demand growth across three U.S.
balancing authorities: ERCOT (Texas), PJM (Mid-Atlantic/Midwest), and
MISO (Southeast/Midwest). CAISO (California) serves as an
institutional falsification check.

The treatment variable is generation interconnection queue filings
from the LBNL Queued Up 2024 dataset. Unlike press releases or
announced investment figures, interconnection filings are legally
binding commitments with precise dates, locations, and MW ratings.
This eliminates the measurement error that affects announcement-based
designs.

The project combines a four-layer causal identification strategy with
a three-model forecasting pipeline and an interactive regional demand
dashboard.

---

## Key Findings

**Main empirical result:** ERCOT minimum hourly demand diverges from
its synthetic counterfactual by 34.8 index points (2019 = 100)
following the May 2023 structural break identified by Bai-Perron
testing. Zero of three in-space placebos exceed ERCOT's gap
(p = 0.25, minimum achievable with three donors).

Minimum demand isolates the always-on baseload floor of data center
infrastructure. Average demand conflates weather-driven peaks with
structural load growth; minimum demand does not. This distinction is
the methodological contribution of the paper.

**Falsification:** No structural break is detected in CAISO
(UDmax = 4.00). Synthetic control gaps for CAISO are weak and
negative post-treatment. The contrast between ERCOT's open-access
queue and CAISO's regulated environment is consistent with the
asymmetric results across identification layers.

**Scenario analysis:** ARIMA, Prophet, and XGBoost models are
estimated on ERCOT zone-level monthly demand (8 zones, 2019-2025).
Conservative and trend scenario projections extend through 2026-2027.
XGBoost with queue-derived features produces the lowest
out-of-sample RMSE.

---

## Live Dashboard

Scenario projections and zone-level demand analysis are available in
the interactive Hex dashboard:

[AI Infrastructure and Regional Electricity Demand: Hex Dashboard](https://app.hex.tech/019d202f-da81-7007-97ee-426ecaa0225e/app/AI-infrastructure-Regional-Electricity-Demand-Evidence-from-US-Interconnection-Queues-032nXU0Qyl37dzoD7TiIpZ/latest)

---

## Data Sources

| Dataset | Source |
|---|---|
| EIA Form 930 hourly demand | EIA Open Data API |
| Generation interconnection queues | LBNL Queued Up 2024 |
| Temperature and HDD/CDD | NOAA NCEI Climate Data Online API |
| Regional GDP | BEA Regional Accounts (SAGDP9) |
| PJM historical queue 2008-2020 | Johnston, Liu, Yang (NBER w31946) |

---

## Tool Stack

| Tool | Role |
|---|---|
| Python | Data pipeline, forecasting models (ARIMA, Prophet, XGBoost) |
| Stata | Panel regression, synthetic control, DiD, wild cluster bootstrap |
| Hex | Interactive dashboard |
| Git/GitHub | Version control |

---

## Repository Structure

```
├── data/                        # Raw and processed panel data
│   ├── ercot_zones/             # ERCOT native load files by year
│   ├── panel_base.csv           # Core BA-month panel
│   ├── panel_load_shape.csv     # Panel with load shape variables
│   ├── panel_caiso_comparison.csv
│   ├── lbnl_queue_data.csv
│   ├── weather_controls.csv
│   ├── gdp_controls.csv
│   └── forecasts_*.csv          # Model forecast outputs
├── scripts/                     # All Python and Stata scripts
│   ├── pull_eia_demand.py       # EIA Form 930 pull
│   ├── build_panel.py           # Core panel construction
│   ├── build_panel_caiso.py
│   ├── build_panel_expanded.py
│   ├── arima_baseline.py
│   ├── prophet_model.py
│   ├── xgboost_model.py
│   ├── structural_projection.py
│   ├── phase2_panel_regression.do
│   ├── phase2_synthetic_control.do
│   ├── phase2_sc_mindemand.do
│   ├── phase2_did.do
│   └── phase3_caiso_sc.do
├── outputs/                     # All figures and tables
│   ├── tables/                  # Formatted regression tables (.docx)
│   └── *.png                    # All paper and appendix figures
├── results/                     # Stata model output (.dta, .csv, .gph)
├── logs/                        # Stata log files
└── README.md
```

---

## Replication

A complete replication archive is published at Harvard Dataverse:
[https://doi.org/10.7910/DVN/F8JV2T](https://doi.org/10.7910/DVN/F8JV2T).
The archive contains the analysis-ready panels, all Python and Stata
scripts, final figures and tables, and the working paper PDF. Raw
third-party data is not redistributable under the terms of the
upstream providers; the archive's README documents how to acquire it.

**Fast path (recommended).** Download the Dataverse archive. The
analysis-ready panels are included, so you can run the Stata
identification scripts and the Python forecasting models without
hitting any external APIs.

**Full reproduction from sources.** Use this path if you want to
rebuild the panels from raw data.

Requirements: Python 3.14, Stata (with `synth`, `xtbreak`, `reghdfe`,
`boottest` packages installed).

1. Clone the repository and create a `.env` file in the project root:

   ```
   EIA_API_KEY=your_key_here
   ```

2. Pull EIA Form 930 demand data:

   ```
   python scripts/pull_eia_demand.py
   ```

3. Build the core panel:

   ```
   python scripts/build_panel.py
   ```

4. Run Stata identification scripts in order from the `scripts/`
   directory:
   - `phase2_panel_regression.do`
   - `phase2_synthetic_control.do`
   - `phase2_sc_mindemand.do`
   - `phase2_did.do`
   - `phase3_caiso_sc.do`

5. Run forecasting models:

   ```
   python scripts/arima_baseline.py
   python scripts/prophet_model.py
   python scripts/xgboost_model.py
   python scripts/structural_projection.py
   ```

Figures write to `outputs/`. Stata results write to `results/` and
`outputs/tables/`.

---

## Working Paper

Lamb, Alan. 2026. "AI Infrastructure and Regional Electricity Demand:
Evidence from U.S. Interconnection Queues." University of Maryland
Working Paper. https://ssrn.com/abstract=6446446

---

## Citation

To cite the paper:

```bibtex
@techreport{lamb2026ai,
  title       = {AI Infrastructure and Regional Electricity Demand: Evidence from U.S. Interconnection Queues},
  author      = {Lamb, Alan},
  year        = {2026},
  institution = {University of Maryland},
  type        = {Working Paper},
  url         = {https://ssrn.com/abstract=6446446}
}
```

To cite the replication data:

> Lamb, Alan, 2026, "AI Infrastructure and Regional Electricity Demand: Evidence from U.S. Interconnection Queues", https://doi.org/10.7910/DVN/F8JV2T, Harvard Dataverse, V1.

```bibtex
@misc{lamb2026data,
  title     = {Replication Data for: AI Infrastructure and Regional Electricity Demand: Evidence from U.S. Interconnection Queues},
  author    = {Lamb, Alan},
  year      = {2026},
  publisher = {Harvard Dataverse},
  version   = {V1},
  doi       = {10.7910/DVN/F8JV2T},
  url       = {https://doi.org/10.7910/DVN/F8JV2T}
}
```

---

## License

Code is released under the MIT License. Derived data and outputs are
released under CC BY 4.0. See the Dataverse landing page for the
authoritative license terms on the archived materials.