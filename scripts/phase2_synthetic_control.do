/*
================================================================================
AI Infrastructure & Regional Electricity Demand
Phase 2: Synthetic Control Analysis

Author:       Alan Lamb
Affiliation:  Lambcast Applied Economics | M.S. Applied Economics, UMD
Date:         March 2026
Contact:      lambcast.net

--------------------------------------------------------------------------------
REPLICATION NOTES

Software:     Stata (tested on Stata 17+)
Dependencies: synth
              Installed automatically in Section 1 if not present.

Input:        data/panel_with_controls.csv
              252 rows, 3 balancing authorities x 84 months (2019-01 to 2025-12)
              Built by scripts/build_panel.py and scripts/pull_controls.py

Output:       logs/phase2_synthetic_control.log     — full session log
              results/sc1_gap_plot.gph               — SC-1 gap figure
              results/sc2_gap_plot.gph               — SC-2 gap figure
              results/sc3_gap_plot.gph               — SC-3 gap figure
              results/placebo_gap_plot.gph           — in-space placebo figure

--------------------------------------------------------------------------------
SYNTHETIC CONTROL DESIGN NOTES

Treated unit:   ERCO (ba_num = 1)
Treatment date: 2023m5 (May 2023) — Stata numeric value 760
                Identified by Bai-Perron structural break test in
                phase2_panel_regression.do. UDmax = 35.39, far exceeds
                1% critical value of 12.37. Break date locked before
                any synthetic control results were examined.

Treatment date numeric value confirmation:
  display monthly("2023-5", "YM") = 760

Robustness:     Calendar check at 2022m1 (Stata value 744) run in
                Section 3 alongside primary treatment date.

Donor contamination acknowledgment:
  PJM and MISO received real data center investment over 2019-2025.
  They are not fully untreated controls. The SC-1 gap estimate is
  therefore a lower bound on the true ERCOT treatment effect.
  SC-2 and SC-3 use cleaner donor pools to bound the estimate upward.
  If SC-1 < SC-2 ≈ SC-3, contamination story is confirmed.

Three donor pool specifications:
  SC-1: PJM + MISO only — contaminated baseline, establishes lower bound
  SC-2: Expanded pool — all low-exposure BAs with EIA coverage
  SC-3: Low-exposure only — PJM and MISO excluded, cleanest pool

Low-exposure classification:
  BAs where cumulative 100MW+ queue filings over 2019-2025 fall below
  threshold computed from LBL queue data. Same classification criterion
  as Layer 3 DiD. Primary candidates: ISONE, NYISO, SPP.
  To be confirmed from LBL data before SC-2 and SC-3 run.

--------------------------------------------------------------------------------
INFERENCE NOTE

Synthetic control inference uses in-space placebo tests — permutation
inference, not bootstrap. Each donor BA is treated as if it were the
treated unit. The fraction of placebos with a post-treatment gap as
large as ERCOT's is the p-value.

With 3 BAs total (SC-1), minimum p-value = 1/3 ≈ 0.33. Reported
explicitly. Donor pool expansion improves inferential resolution.

Pre-treatment RMSPE filter: placebos with pre-treatment RMSPE more
than 2x ERCOT's pre-treatment RMSPE are excluded from the permutation
distribution. Reported explicitly.

Reference:
  Abadie, A., Diamond, A., and Hainmueller, J. (2010). Synthetic
  Control Methods for Comparative Case Studies: Estimating the Effect
  of California's Tobacco Control Program. Journal of the American
  Statistical Association, 105(490), 493-505.

--------------------------------------------------------------------------------
SYNTH COMMAND SYNTAX NOTE

synth requires xtset panel data and uses this structure:
  synth depvar predictor_vars, trunit(#) trperiod(#)

  trunit:   numeric code for treated unit (ERCO = 1)
  trperiod: Stata monthly date numeric for treatment period (2023m5 = 760)

Predictors can include:
  - Variable name alone: uses full sample average
  - var(start) to (end): uses average over specified range
  - Lagged outcome values as predictors for pre-treatment fit

Key output:
  e(W_weights)   — donor unit weights
  e(X_balance)   — predictor balance table
  e(RMSPE)       — pre-treatment root mean squared prediction error
  e(Y_treated)   — actual treated unit outcome
  e(Y_synthetic) — synthetic control outcome

================================================================================
*/


// ===========================================================================
// SECTION 0: ENVIRONMENT SETUP
// ===========================================================================

cd "C:\Users\alamb\OneDrive\Alans Work Folder\independent projects\ai-electricity-demand"

capture mkdir "logs"
capture mkdir "results"

capture log close
log using "logs/phase2_synthetic_control.log", replace text

display "Session started: $S_DATE $S_TIME"
display "Stata version: `c(stata_version)'"


// ===========================================================================
// SECTION 1: PACKAGE INSTALLATION
// ===========================================================================

capture ssc install synth


// ===========================================================================
// SECTION 2: DATA PREPARATION
// ===========================================================================
// synth requires xtset panel data with a numeric unit identifier and
// numeric time variable. Same setup as panel regression do file.

display _newline "--- SECTION 2: DATA PREPARATION ---"

import delimited "data/panel_with_controls.csv", clear
display "Observations loaded: `=_N'"

rename ba ba_id

gen month_year = monthly(year_month, "YM")
format month_year %tm

encode ba_id, gen(ba_num)
display "BA encoding:"
label list ba_num
// Expected: 1=ERCO, 2=MISO, 3=PJM

xtset ba_num month_year
// Expected: strongly balanced, 2019m1-2025m12, delta 1 month

// Confirm treatment date numeric value
display "Treatment date numeric value (2023m5):"
display monthly("2023-5", "YM")
// Expected: 760

// Confirm pre-treatment period
// Pre-treatment: 2019m1 (Stata value 708) through 2023m4 (Stata value 759)
// Post-treatment: 2023m5 (760) through 2025m12 (791)
display "Pre-treatment start (2019m1):"
display monthly("2019-1", "YM")
display "Pre-treatment end (2023m4):"
display monthly("2023-4", "YM")
display "Post-treatment end (2025m12):"
display monthly("2025-12", "YM")

// Quick descriptive check — confirm ERCOT divergence is visible
tabstat avg_demand_mwh if month_year < 760, by(ba_id) stats(mean)
tabstat avg_demand_mwh if month_year >= 760, by(ba_id) stats(mean)

// *** STOP HERE — verify output before proceeding to SC-1 ***
// Confirm: 1=ERCO, balanced panel, treatment date = 760
// Pre/post means should show ERCOT diverging relative to PJM and MISO


// ===========================================================================
// SECTION 3: SC-1 — PJM AND MISO DONOR POOL (LOWER BOUND)
// ===========================================================================
// Baseline synthetic control. Donor pool: PJM (ba_num=3) and MISO (ba_num=2).
// Treatment date: 2023m5 (trperiod=760). Treated unit: ERCO (trunit=1).
//
// Outcome variable: demand_idx — indexed demand, 2019 average = 100.
// Indexing required because ERCOT's absolute demand level sits outside
// the convex hull of PJM and MISO. Running synth on avg_demand_mwh
// produced RMSPE=28,227 with 100% weight on MISO and no meaningful fit.
// Indexed demand removes absolute scale differences and asks the correct
// question: did ERCOT's demand grow faster than a weighted combination
// of donors would predict?
//
// ACKNOWLEDGED LOWER BOUND: PJM and MISO received real data center
// investment over 2019-2025. They are contaminated donors. This gap
// estimate understates the true ERCOT treatment effect. Reported
// explicitly as lower bound. SC-2 and SC-3 use cleaner donor pools.

display _newline "--- SECTION 3: SC-1 PJM + MISO DONOR POOL ---"

// Create indexed demand variable — 2019 average = 100 for each BA
bysort ba_num: egen demand_2019 = mean(avg_demand_mwh) if year == 2019
bysort ba_num: egen demand_base = mean(demand_2019)
gen demand_idx = (avg_demand_mwh / demand_base) * 100
drop demand_2019

// Verify indexing
tabstat demand_idx if year == 2019, by(ba_id) stats(mean)
// Expected: all BAs = 100

tabstat demand_idx if month_year >= 760, by(ba_id) stats(mean)
// Expected: ERCO ~124, MISO ~101, PJM ~102

// Run SC-1
synth demand_idx ///
    demand_idx(708) demand_idx(720) demand_idx(732) ///
    demand_idx(744) demand_idx(756) ///
    hdd cdd gdp, ///
    trunit(1) trperiod(760) ///
    keep(results/sc1_idx_results.dta) replace

// Record weights and balance
matrix list e(W_weights)
matrix list e(X_balance)

// SC-1 RESULTS (confirmed March 2026):
//   Pre-treatment RMSPE:     11.09 index points
//   Donor weights:           MISO 0.752, PJM 0.248
//   Post-treatment mean gap: 23.0 index points
//   Pre-treatment mean gap:  4.6 index points
//   Signal-to-noise ratio:   ~5:1
//   Interpretation:          ERCOT demand ran 23 index points above
//                            synthetic counterfactual after May 2023.
//                            Contaminated donors — lower bound estimate.
//                            Pre-treatment fit strongest 2021-2023.

// Compute and plot gap
use results/sc1_idx_results.dta, clear
gen gap = _Y_treated - _Y_synthetic

summarize gap if _time >= 760
summarize gap if _time < 760

twoway line gap _time, lcolor(black) lwidth(medium) ///
    xline(760, lcolor(red) lpattern(dot)) ///
    yline(0, lcolor(gray) lpattern(dash)) ///
    xlabel(708(12)791, angle(45) format(%tmMon_CCYY)) ///
    ylabel(-30(10)50, format(%9.0f)) ///
    title("SC-1: ERCOT Demand Gap vs Synthetic ERCOT") ///
    ytitle("Gap (index points, 2019=100)") ///
    xtitle("") ///
    note("Positive values = ERCOT demand above synthetic counterfactual." ///
         "Vertical line = treatment date (2023m5). RMSPE=11.09." ///
         "Donor pool: PJM + MISO (contaminated — lower bound estimate).") ///
    saving(results/sc1_gap_plot.gph, replace)

// Reload full panel for subsequent sections
import delimited "data/panel_with_controls.csv", clear
rename ba ba_id
gen month_year = monthly(year_month, "YM")
format month_year %tm
encode ba_id, gen(ba_num)
xtset ba_num month_year
bysort ba_num: egen demand_2019 = mean(avg_demand_mwh) if year == 2019
bysort ba_num: egen demand_base = mean(demand_2019)
gen demand_idx = (avg_demand_mwh / demand_base) * 100
drop demand_2019

// *** STOP HERE — SC-2 requires expanded donor pool ***
// Next step: confirm which additional BAs are available in
// eia_demand_2018_2025.csv and classify low-exposure BAs
// from LBL queue data before proceeding to SC-2.