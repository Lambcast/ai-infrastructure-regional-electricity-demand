/*
================================================================================
AI Infrastructure & Regional Electricity Demand
Phase 2: Synthetic Control — Minimum Hourly Demand Outcome

Author:       Alan Lamb
Affiliation:  Lambcast Applied Economics | M.S. Applied Economics, UMD
Date:         March 2026
Contact:      lambcast.net

--------------------------------------------------------------------------------
REPLICATION NOTES

Software:     Stata (tested on Stata 17+)
Dependencies: synth
              Install via ssc if not present.

Input:        data/panel_expanded.csv
              504 rows, 6 balancing authorities x 84 months (2019-01 to 2025-12)
              Includes min_demand_idx for all 6 BAs.
              Built by scripts/build_panel.py, scripts/pull_controls.py,
              and scripts/build_load_shape.py

Output:       logs/phase2_sc_mindemand.log         — full session log
              results/sc3_mindemand_results.dta     — SC-3 gap data
              results/sc3_mindemand_plot.gph        — SC-3 gap figure
              results/mindemand_placebo_isne.dta    — ISNE placebo gap
              results/mindemand_placebo_nyis.dta    — NYIS placebo gap
              results/mindemand_placebo_swpp.dta    — SWPP placebo gap
              results/mindemand_inspace.dta         — combined placebo dataset
              results/mindemand_inspace_plot.gph    — in-space placebo figure

--------------------------------------------------------------------------------
MOTIVATION

This do file complements phase2_synthetic_control.do by using minimum
hourly monthly demand as the outcome variable rather than average hourly
demand. Minimum demand captures the overnight baseload floor — the lowest
hourly demand recorded each month. This is theoretically more direct as a
measure of data center load because:

  (1) Data centers operate continuously at near-constant power draw.
      They raise the demand floor, not just the average.
  (2) Minimum demand removes weather-driven peak variation that
      obscures the flat continuous data center signal in average demand.
  (3) Rising minimum demand relative to comparable BAs is the specific
      load shape signature of always-on industrial infrastructure.

The minimum demand result (34.8 index point gap) is larger and more
visually distinct than the average demand result (24.5 index points),
consistent with data centers contributing disproportionately to the
baseload floor rather than to peak demand.

--------------------------------------------------------------------------------
DESIGN NOTES

Treated unit:   ERCO (ba_num = 1 in expanded panel encoding)
Donor pool:     ISNE (2), NYIS (4), SWPP (6) — SC-3 low-exposure spec
                PJM (5) and MISO (3) excluded — contaminated donors
Treatment date: 2023m5 (Stata monthly value 760)
                Same Bai-Perron date as average demand analysis.
                Locked before any synthetic control results examined.

Outcome:        min_demand_idx — monthly minimum hourly demand indexed
                to 2019 annual average = 100 for each BA.

Pre-treatment RMSPE: 13.53 (slightly worse than average demand 11.12)
                     HDD/CDD mismatch remains — same structural limitation
                     as average demand SC. Honest caveats apply.

RMSPE exclusion threshold: 2x ERCOT RMSPE = 27.06
All three placebos pass: ISNE 10.05, NYIS 14.61, SWPP 7.46.

Note on Winter Storm Uri (February 2021):
  The pre-treatment period includes a large negative spike in ERCOT
  minimum demand in early 2021 driven by the Texas winter storm event.
  This creates a pre-treatment fitting challenge and is visible as a dip
  to -20 in the gap plot. Documented here and in the paper footnotes.

--------------------------------------------------------------------------------
INFERENCE

In-space placebo tests. P-value = 1/4 = 0.25 (minimum achievable with
3 donors). Zero placebos produce a post-treatment gap as large as ERCOT's.
ISNE and NYIS post-treatment gaps are strongly negative (-25.6 and -13.2).
SWPP gap is positive but 12.9 vs ERCOT's 34.8 — less than half.
ERCOT sits unambiguously at the extreme right of the permutation distribution.

================================================================================
*/


// ===========================================================================
// SECTION 0: ENVIRONMENT SETUP
// ===========================================================================

cd "C:\Users\alamb\OneDrive\Alans Work Folder\independent projects\ai-electricity-demand"

capture mkdir "logs"
capture mkdir "results"

capture log close
log using "logs/phase2_sc_mindemand.log", replace text

display "Session started: $S_DATE $S_TIME"
display "Stata version: `c(stata_version)'"


// ===========================================================================
// SECTION 1: PACKAGE INSTALLATION
// ===========================================================================
// Required — install once if not present:
//   ssc install synth
// Confirmed installed as of March 2026 on Stata 19.


// ===========================================================================
// SECTION 2: SC-3 — MINIMUM DEMAND, LOW-EXPOSURE DONOR POOL
// ===========================================================================
// Primary specification. Same donor pool as average demand SC-3.
// Outcome: min_demand_idx — monthly minimum hourly demand, 2019=100.

display _newline "--- SECTION 2: SC-3 MINIMUM DEMAND ---"

import delimited "data/panel_expanded.csv", clear
rename ba ba_id
gen month_year = monthly(year_month, "YM")
format month_year %tm
encode ba_id, gen(ba_num)

display "BA encoding:"
label list ba_num
// Confirmed: 1=ERCO, 2=ISNE, 3=MISO, 4=NYIS, 5=PJM, 6=SWPP

// Drop contaminated donors
drop if ba_num == 3 | ba_num == 5
xtset ba_num month_year

synth min_demand_idx ///
    min_demand_idx(708) min_demand_idx(720) min_demand_idx(732) ///
    min_demand_idx(744) min_demand_idx(756) ///
    hdd cdd gdp, ///
    trunit(1) trperiod(760) ///
    keep(results/sc3_mindemand_results.dta) replace

matrix list e(W_weights)
matrix list e(X_balance)

// Compute and plot gap
use results/sc3_mindemand_results.dta, clear
gen gap = _Y_treated - _Y_synthetic

summarize gap if _time >= 760
summarize gap if _time < 760

twoway line gap _time, lcolor(black) lwidth(medium) ///
    xline(760, lcolor(red) lpattern(dot)) ///
    yline(0, lcolor(gray) lpattern(dash)) ///
    xlabel(708(12)791, angle(45) format(%tmMon_CCYY)) ///
    ylabel(-30(10)70, format(%9.0f)) ///
    title("SC-3: ERCOT Minimum Demand Gap vs Synthetic ERCOT") ///
    ytitle("Gap (index points, 2019=100)") ///
    xtitle("") ///
    note("Outcome: minimum hourly demand. Donor pool: ISNE, NYIS, SWPP." ///
         "Pre-treatment dip ~2021m2 reflects Winter Storm Uri (Texas).") ///
    name(sc3_mindemand, replace) ///
    saving(results/sc3_mindemand_plot.gph, replace)

// SC-3 MINIMUM DEMAND RESULTS (confirmed March 2026):
//   Pre-treatment RMSPE:     13.53 index points
//   Donor weights:           ISNE 0.639, NYIS 0.179, SWPP 0.182
//   Post-treatment mean gap: 34.8 index points  ← PRIMARY MIN DEMAND ESTIMATE
//   Pre-treatment mean gap:  6.1 index points
//   Signal-to-noise ratio:   5.7x
//   Interpretation:          ERCOT overnight baseload floor grew 34.8 index
//                            points above synthetic counterfactual after 2023m5.
//                            Larger than average demand gap (24.5) — consistent
//                            with data centers contributing disproportionately
//                            to the demand floor rather than to peak demand.
//                            Winter Storm Uri dip in early 2021 is a
//                            pre-treatment fitting artifact — documented.


// ===========================================================================
// SECTION 3: IN-SPACE PLACEBO TESTS
// ===========================================================================
// Permutation inference. Each donor treated as placebo treated unit.
// ERCOT RMSPE = 13.53 — exclusion threshold = 27.06 (2x).
// All three placebos pass the filter.
// Minimum p-value with 3 donors = 1/4 = 0.25.

display _newline "--- SECTION 3: IN-SPACE PLACEBO TESTS ---"

// Save ERCOT gap
use results/sc3_mindemand_results.dta, clear
gen gap_erco = _Y_treated - _Y_synthetic
keep _time gap_erco
save results/mindemand_inspace.dta, replace

// ISNE placebo (trunit=2)
import delimited "data/panel_expanded.csv", clear
rename ba ba_id
gen month_year = monthly(year_month, "YM")
format month_year %tm
encode ba_id, gen(ba_num)
drop if ba_num == 3 | ba_num == 5
xtset ba_num month_year

synth min_demand_idx ///
    min_demand_idx(708) min_demand_idx(720) min_demand_idx(732) ///
    min_demand_idx(744) min_demand_idx(756) ///
    hdd cdd gdp, ///
    trunit(2) trperiod(760) keep(results/mindemand_placebo_isne.dta) replace

display "ISNE placebo RMSPE (exclusion threshold = 27.06):"
matrix list e(RMSPE)
// Confirmed: 10.05 — PASSES

use results/mindemand_placebo_isne.dta, clear
gen gap_isne = _Y_treated - _Y_synthetic
keep _time gap_isne
merge 1:1 _time using results/mindemand_inspace.dta, nogenerate
save results/mindemand_inspace.dta, replace

// NYIS placebo (trunit=4)
import delimited "data/panel_expanded.csv", clear
rename ba ba_id
gen month_year = monthly(year_month, "YM")
format month_year %tm
encode ba_id, gen(ba_num)
drop if ba_num == 3 | ba_num == 5
xtset ba_num month_year

synth min_demand_idx ///
    min_demand_idx(708) min_demand_idx(720) min_demand_idx(732) ///
    min_demand_idx(744) min_demand_idx(756) ///
    hdd cdd gdp, ///
    trunit(4) trperiod(760) keep(results/mindemand_placebo_nyis.dta) replace

display "NYIS placebo RMSPE (exclusion threshold = 27.06):"
matrix list e(RMSPE)
// Confirmed: 14.61 — PASSES

use results/mindemand_placebo_nyis.dta, clear
gen gap_nyis = _Y_treated - _Y_synthetic
keep _time gap_nyis
merge 1:1 _time using results/mindemand_inspace.dta, nogenerate
save results/mindemand_inspace.dta, replace

// SWPP placebo (trunit=6)
import delimited "data/panel_expanded.csv", clear
rename ba ba_id
gen month_year = monthly(year_month, "YM")
format month_year %tm
encode ba_id, gen(ba_num)
drop if ba_num == 3 | ba_num == 5
xtset ba_num month_year

synth min_demand_idx ///
    min_demand_idx(708) min_demand_idx(720) min_demand_idx(732) ///
    min_demand_idx(744) min_demand_idx(756) ///
    hdd cdd gdp, ///
    trunit(6) trperiod(760) keep(results/mindemand_placebo_swpp.dta) replace

display "SWPP placebo RMSPE (exclusion threshold = 27.06):"
matrix list e(RMSPE)
// Confirmed: 7.46 — PASSES

use results/mindemand_placebo_swpp.dta, clear
gen gap_swpp = _Y_treated - _Y_synthetic
keep _time gap_swpp
merge 1:1 _time using results/mindemand_inspace.dta, nogenerate
save results/mindemand_inspace.dta, replace


// ===========================================================================
// SECTION 4: IN-SPACE PLACEBO FIGURE AND P-VALUE
// ===========================================================================

display _newline "--- SECTION 4: PLACEBO FIGURE AND P-VALUE ---"

use results/mindemand_inspace.dta, clear

display _newline "Post-treatment mean gaps:"
summarize gap_erco if _time >= 760
summarize gap_isne if _time >= 760
summarize gap_nyis if _time >= 760
summarize gap_swpp if _time >= 760

// IN-SPACE PLACEBO RESULTS (confirmed March 2026):
//   ERCOT:  +34.8  ← treated unit
//   ISNE:   -25.6  ← strongly negative — passes RMSPE filter
//   NYIS:   -13.2  ← negative — passes RMSPE filter
//   SWPP:   +12.9  ← positive but less than half ERCOT — passes filter
//
//   P-value: 1/4 = 0.25 — minimum achievable with 3 donors.
//   Zero placebos produce gap >= ERCOT's 34.8.
//   ERCOT sits unambiguously at extreme right of permutation distribution.
//   ISNE and NYIS minimum demand fell relative to counterfactual —
//   consistent with their low data center exposure and stable load profiles.

twoway ///
    (line gap_isne _time, lcolor(gs12) lwidth(thin)) ///
    (line gap_nyis _time, lcolor(gs12) lwidth(thin)) ///
    (line gap_swpp _time, lcolor(gs12) lwidth(thin)) ///
    (line gap_erco _time, lcolor(black) lwidth(medthick)) ///
    , xline(760, lcolor(red) lpattern(dot)) ///
    yline(0, lcolor(gray) lpattern(dash)) ///
    xlabel(708(12)791, angle(45) format(%tmMon_CCYY)) ///
    ylabel(-50(10)70, format(%9.0f)) ///
    legend(order(4 "ERCOT (treated)" 1 "ISNE placebo" ///
                 2 "NYIS placebo" 3 "SWPP placebo") ///
           position(11) ring(0) cols(1)) ///
    title("In-Space Placebos: Minimum Demand, SC-3 Specification") ///
    ytitle("Gap (index points, 2019=100)") ///
    xtitle("") ///
    note("Black = ERCOT. Gray = donor BAs treated as placebo units." ///
         "Outcome: minimum hourly demand. Vertical line = 2023m5." ///
         "All placebos pass pre-treatment RMSPE filter (threshold = 27.06).") ///
    name(mindemand_placebos, replace) ///
    saving(results/mindemand_inspace_plot.gph, replace)


// ===========================================================================
// END OF MINIMUM DEMAND SYNTHETIC CONTROL DO FILE
// ===========================================================================

log close
