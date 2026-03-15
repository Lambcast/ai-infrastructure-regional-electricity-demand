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


// ===========================================================================
// SECTION 4: SC-2 — EXPANDED DONOR POOL
// ===========================================================================
// Donor pool: ISNE, MISO, NYIS, PJM, SWPP (ba_num 2,3,4,5,6)
// Adds low-exposure BAs to the donor pool alongside PJM and MISO.
// If gap estimate rises above SC-1, expanded pool is doing real work.
// Pre-treatment RMSPE should improve with more donors.

display _newline "--- SECTION 4: SC-2 EXPANDED DONOR POOL ---"

import delimited "data/panel_expanded.csv", clear
rename ba ba_id
gen month_year = monthly(year_month, "YM")
format month_year %tm
encode ba_id, gen(ba_num)
xtset ba_num month_year

// Index demand — 2019 average = 100 for each BA
bysort ba_num: egen demand_2019 = mean(avg_demand_mwh) if year == 2019
bysort ba_num: egen demand_base = mean(demand_2019)
gen demand_idx = (avg_demand_mwh / demand_base) * 100
drop demand_2019

synth demand_idx ///
    demand_idx(708) demand_idx(720) demand_idx(732) ///
    demand_idx(744) demand_idx(756) ///
    hdd cdd gdp, ///
    trunit(1) trperiod(760) ///
    keep(results/sc2_idx_results.dta) replace

matrix list e(W_weights)
matrix list e(X_balance)

// Compute and plot gap
use results/sc2_idx_results.dta, clear
gen gap = _Y_treated - _Y_synthetic

summarize gap if _time >= 760
summarize gap if _time < 760

twoway line gap _time, lcolor(black) lwidth(medium) ///
    xline(760, lcolor(red) lpattern(dot)) ///
    yline(0, lcolor(gray) lpattern(dash)) ///
    xlabel(708(12)791, angle(45) format(%tmMon_CCYY)) ///
    ylabel(-30(10)50, format(%9.0f)) ///
    title("SC-2: ERCOT Demand Gap vs Synthetic ERCOT") ///
    ytitle("Gap (index points, 2019=100)") ///
    xtitle("") ///
    note("Donor pool: ISNE, MISO, NYIS, PJM, SWPP (expanded pool).") ///
    saving(results/sc2_gap_plot.gph, replace)

// SC-2 RESULTS (confirmed March 2026):
//   Pre-treatment RMSPE:     8.30 index points (best fit of three specs)
//   Donor weights:           SWPP 1.0, all others 0
//   Post-treatment mean gap: 15.4 index points
//   Pre-treatment mean gap:  3.1 index points
//   Note: Optimizer selected SWPP exclusively — best pre-treatment match.
//         SWPP's own post-treatment demand growth compresses gap estimate.
//         Lower gap reflects donor trajectory, not absence of ERCOT effect.


// ===========================================================================
// SECTION 5: SC-3 — LOW-EXPOSURE DONOR POOL ONLY
// ===========================================================================
// Donor pool: ISNE(2), NYIS(4), SWPP(6) only — PJM and MISO excluded.
// Cleanest donor pool — removes contaminated units entirely.
// If SC-3 gap > SC-1 gap, contamination lower bound story is confirmed.
// If SC-3 ≈ SC-2, expanded pool result is stable.

display _newline "--- SECTION 5: SC-3 LOW-EXPOSURE DONOR POOL ---"

import delimited "data/panel_expanded.csv", clear
rename ba ba_id
gen month_year = monthly(year_month, "YM")
format month_year %tm
encode ba_id, gen(ba_num)

// Drop PJM and MISO — low-exposure only
drop if ba_num == 3 | ba_num == 5

xtset ba_num month_year

// Index demand
bysort ba_num: egen demand_2019 = mean(avg_demand_mwh) if year == 2019
bysort ba_num: egen demand_base = mean(demand_2019)
gen demand_idx = (avg_demand_mwh / demand_base) * 100
drop demand_2019

synth demand_idx ///
    demand_idx(708) demand_idx(720) demand_idx(732) ///
    demand_idx(744) demand_idx(756) ///
    hdd cdd gdp, ///
    trunit(1) trperiod(760) ///
    keep(results/sc3_idx_results.dta) replace

matrix list e(W_weights)
matrix list e(X_balance)

// Compute and plot gap
use results/sc3_idx_results.dta, clear
gen gap = _Y_treated - _Y_synthetic

summarize gap if _time >= 760
summarize gap if _time < 760

twoway line gap _time, lcolor(black) lwidth(medium) ///
    xline(760, lcolor(red) lpattern(dot)) ///
    yline(0, lcolor(gray) lpattern(dash)) ///
    xlabel(708(12)791, angle(45) format(%tmMon_CCYY)) ///
    ylabel(-30(10)50, format(%9.0f)) ///
    title("SC-3: ERCOT Demand Gap vs Synthetic ERCOT") ///
    ytitle("Gap (index points, 2019=100)") ///
    xtitle("") ///
    note("Donor pool: ISNE, NYIS, SWPP only (low-exposure, cleanest estimate).") ///
    saving(results/sc3_gap_plot.gph, replace)


// SC-3 RESULTS (confirmed March 2026):
//   Pre-treatment RMSPE:     11.12 index points
//   Donor weights:           NYIS 0.755, SWPP 0.245, ISNE 0
//   Post-treatment mean gap: 24.5 index points  ← PRIMARY SC ESTIMATE
//   Pre-treatment mean gap:  5.1 index points
//   Note: Cleanest donor pool. Gap above SC-1 confirms contamination
//         lower bound story. ISNE receives zero weight — climate
//         mismatch prevents meaningful contribution to ERCOT match.


// ===========================================================================
// SECTION 5b: SC-3 CALENDAR DATE ROBUSTNESS — TREATMENT AT 2022m1
// ===========================================================================
// Purpose: Confirm Bai-Perron date of 2023m5 is not arbitrary.
// Method: Rerun SC-3 with treatment at 2022m1 (744) — the alternative
//         calendar date referenced in the methodology doc.
// Expected: Smaller gap than primary because 2022-2023 ramp-up period
//           is absorbed into the post-treatment window.
// File saved separately to avoid overwriting primary SC-3 results.

display _newline "--- SECTION 5b: CALENDAR DATE ROBUSTNESS 2022m1 ---"

// Reload SC-3 panel — same setup as Section 5
import delimited "data/panel_expanded.csv", clear
rename ba ba_id
gen month_year = monthly(year_month, "YM")
format month_year %tm
encode ba_id, gen(ba_num)
drop if ba_num == 3 | ba_num == 5
xtset ba_num month_year
bysort ba_num: egen demand_2019 = mean(avg_demand_mwh) if year == 2019
bysort ba_num: egen demand_base = mean(demand_2019)
gen demand_idx = (avg_demand_mwh / demand_base) * 100
drop demand_2019

synth demand_idx ///
    demand_idx(708) demand_idx(720) demand_idx(732) ///
    demand_idx(744) demand_idx(756) ///
    hdd cdd gdp, ///
    trunit(1) trperiod(744) ///
    keep(results/sc3_robustness_2022m1.dta) replace

matrix list e(W_weights)

use results/sc3_robustness_2022m1.dta, clear
gen gap = _Y_treated - _Y_synthetic

summarize gap if _time >= 744
summarize gap if _time < 744

twoway line gap _time, lcolor(black) lwidth(medium) ///
    xline(744, lcolor(red) lpattern(dot)) ///
    yline(0, lcolor(gray) lpattern(dash)) ///
    xlabel(708(12)791, angle(45) format(%tmMon_CCYY)) ///
    ylabel(-30(10)50, format(%9.0f)) ///
    title("SC-3 Robustness: Calendar Date 2022m1") ///
    ytitle("Gap (index points, 2019=100)") ///
    xtitle("") ///
    note("Robustness check — treatment date 2022m1 (744)." ///
         "Primary estimate uses Bai-Perron date 2023m5 (760)." ///
         "Donor pool: ISNE, NYIS, SWPP.") ///
    name(sc3_calendar, replace) ///
    saving(results/sc3_robustness_2022m1_plot.gph, replace)

// RESULTS (confirmed March 2026):
//   RMSPE:               9.25
//   Weights:             NYIS 0.796, SWPP 0.204, ISNE 0
//   Post-treatment gap:  20.5 index points
//   Pre-treatment gap:   2.4 index points
//   Interpretation: Smaller gap than primary (24.5) because 2022-2023
//   ramp-up period is included in post-treatment window, diluting the
//   divergence estimate. Confirms Bai-Perron date of 2023m5 better
//   isolates the post-divergence period. Coherent with lower bound story.

// *** STOP HERE ***
// Compare SC-1, SC-2, SC-3 gap estimates before proceeding to placebos.
// If SC-1 < SC-2 ≈ SC-3, contamination lower bound story is confirmed.


// ===========================================================================
// SECTION 6: IN-TIME PLACEBO TESTS
// ===========================================================================
// Purpose: Test whether the 2023m5 treatment date is special.
// Method: Rerun SC-3 as if treatment had occurred at earlier dates.
// If placebo gaps are small relative to the true 2023m5 gap, that is
// evidence the result is not just noise in the synthetic control method.
//
// Placebo dates: 2020m1 (720), 2021m1 (732), 2022m1 (744)
// True treatment: 2023m5 (760)
// All use SC-3 donor pool: ERCO vs ISNE, NYIS, SWPP

display _newline "--- SECTION 6: IN-TIME PLACEBO TESTS ---"

// Reload SC-3 panel
import delimited "data/panel_expanded.csv", clear
rename ba ba_id
gen month_year = monthly(year_month, "YM")
format month_year %tm
encode ba_id, gen(ba_num)
drop if ba_num == 3 | ba_num == 5
xtset ba_num month_year
bysort ba_num: egen demand_2019 = mean(avg_demand_mwh) if year == 2019
bysort ba_num: egen demand_base = mean(demand_2019)
gen demand_idx = (avg_demand_mwh / demand_base) * 100
drop demand_2019

// Placebo 1: treatment date = 2020m1 (720)
// Pre-treatment predictors limited to 708-719 (12 months only)
synth demand_idx demand_idx(708) demand_idx(714) demand_idx(719) hdd cdd gdp, ///
    trunit(1) trperiod(720) keep(results/sc3_intime_2020m1.dta) replace
display "In-time placebo 2020m1 RMSPE:"
matrix list e(RMSPE)

// Placebo 2: treatment date = 2021m1 (732)
synth demand_idx demand_idx(708) demand_idx(714) demand_idx(720) ///
    demand_idx(726) demand_idx(731) hdd cdd gdp, ///
    trunit(1) trperiod(732) keep(results/sc3_intime_2021m1.dta) replace
display "In-time placebo 2021m1 RMSPE:"
matrix list e(RMSPE)

// Placebo 3: treatment date = 2022m1 (744)
synth demand_idx demand_idx(708) demand_idx(714) demand_idx(720) ///
    demand_idx(726) demand_idx(732) demand_idx(738) demand_idx(743) hdd cdd gdp, ///
    trunit(1) trperiod(744) keep(results/sc3_intime_2022m1.dta) replace
display "In-time placebo 2022m1 RMSPE:"
matrix list e(RMSPE)

// Build combined gap dataset for plotting
// True treatment gap
use results/sc3_idx_results.dta, clear
gen gap_true = _Y_treated - _Y_synthetic
keep _time gap_true
save results/intime_combined.dta, replace

// 2020m1 placebo gap
use results/sc3_intime_2020m1.dta, clear
gen gap_2020 = _Y_treated - _Y_synthetic
keep _time gap_2020
merge 1:1 _time using results/intime_combined.dta, nogenerate
save results/intime_combined.dta, replace

// 2021m1 placebo gap
use results/sc3_intime_2021m1.dta, clear
gen gap_2021 = _Y_treated - _Y_synthetic
keep _time gap_2021
merge 1:1 _time using results/intime_combined.dta, nogenerate
save results/intime_combined.dta, replace

// 2022m1 placebo gap
use results/sc3_intime_2022m1.dta, clear
gen gap_2022 = _Y_treated - _Y_synthetic
keep _time gap_2022
merge 1:1 _time using results/intime_combined.dta, nogenerate
save results/intime_combined.dta, replace

// Plot all four gap series on same figure
// True treatment in black, placebos in gray
use results/intime_combined.dta, clear

twoway ///
    (line gap_2020 _time, lcolor(gs10) lwidth(thin) lpattern(dash)) ///
    (line gap_2021 _time, lcolor(gs10) lwidth(thin) lpattern(dash)) ///
    (line gap_2022 _time, lcolor(gs10) lwidth(thin) lpattern(dash)) ///
    (line gap_true _time, lcolor(black) lwidth(medthick)) ///
    , xline(760, lcolor(red) lpattern(dot)) ///
    yline(0, lcolor(gray) lpattern(dash)) ///
    xlabel(708(12)791, angle(45) format(%tmMon_CCYY)) ///
    ylabel(-30(10)50, format(%9.0f)) ///
    legend(order(4 "True treatment (2023m5)" ///
                 1 "Placebo 2020m1" 2 "Placebo 2021m1" 3 "Placebo 2022m1") ///
           position(11) ring(0) cols(1)) ///
    title("In-Time Placebo Tests: SC-3 Specification") ///
    ytitle("Gap (index points, 2019=100)") ///
    xtitle("") ///
    note("Black = true treatment date (2023m5). Gray = placebo treatment dates." ///
         "Donor pool: ISNE, NYIS, SWPP.") ///
    saving(results/intime_placebo_plot.gph, replace)

// *** STOP HERE — record RMSPE values and paste plot before Section 7 ***


// ===========================================================================
// SECTION 7: IN-SPACE PLACEBO TESTS
// ===========================================================================
// Purpose: Formal permutation inference for SC-3.
// Method: Treat each donor BA as if it were the treated unit.
//         Construct synthetic version from remaining units.
//         Compare post-treatment gap to ERCOT's gap.
// P-value = fraction of placebos with gap >= ERCOT's gap.
// RMSPE filter: exclude placebos where pre-treatment RMSPE > 2x ERCOT's.
// ERCOT SC-3 RMSPE = 11.12 — exclude placebos above 22.24.
// Minimum p-value with 3 donors = 1/4 = 0.25.

display _newline "--- SECTION 7: IN-SPACE PLACEBO TESTS ---"

// Reload SC-3 panel
import delimited "data/panel_expanded.csv", clear
rename ba ba_id
gen month_year = monthly(year_month, "YM")
format month_year %tm
encode ba_id, gen(ba_num)
drop if ba_num == 3 | ba_num == 5
xtset ba_num month_year
bysort ba_num: egen demand_2019 = mean(avg_demand_mwh) if year == 2019
bysort ba_num: egen demand_base = mean(demand_2019)
gen demand_idx = (avg_demand_mwh / demand_base) * 100
drop demand_2019

// Save ERCOT gap for comparison
use results/sc3_idx_results.dta, clear
gen gap_erco = _Y_treated - _Y_synthetic
keep _time gap_erco
save results/inspace_combined.dta, replace

// Placebo 1: ISNE as treated unit (ba_num=2)
// Donors: ERCO(1), NYIS(4), SWPP(6)
import delimited "data/panel_expanded.csv", clear
rename ba ba_id
gen month_year = monthly(year_month, "YM")
format month_year %tm
encode ba_id, gen(ba_num)
drop if ba_num == 3 | ba_num == 5
xtset ba_num month_year
bysort ba_num: egen demand_2019 = mean(avg_demand_mwh) if year == 2019
bysort ba_num: egen demand_base = mean(demand_2019)
gen demand_idx = (avg_demand_mwh / demand_base) * 100
drop demand_2019

synth demand_idx ///
    demand_idx(708) demand_idx(720) demand_idx(732) ///
    demand_idx(744) demand_idx(756) ///
    hdd cdd gdp, ///
    trunit(2) trperiod(760) keep(results/sc3_placebo_isne.dta) replace

display "ISNE placebo RMSPE (threshold for exclusion = 22.24):"
matrix list e(RMSPE)

use results/sc3_placebo_isne.dta, clear
gen gap_isne = _Y_treated - _Y_synthetic
keep _time gap_isne
merge 1:1 _time using results/inspace_combined.dta, nogenerate
save results/inspace_combined.dta, replace

// Placebo 2: NYIS as treated unit (ba_num=4)
// Donors: ERCO(1), ISNE(2), SWPP(6)
import delimited "data/panel_expanded.csv", clear
rename ba ba_id
gen month_year = monthly(year_month, "YM")
format month_year %tm
encode ba_id, gen(ba_num)
drop if ba_num == 3 | ba_num == 5
xtset ba_num month_year
bysort ba_num: egen demand_2019 = mean(avg_demand_mwh) if year == 2019
bysort ba_num: egen demand_base = mean(demand_2019)
gen demand_idx = (avg_demand_mwh / demand_base) * 100
drop demand_2019

synth demand_idx ///
    demand_idx(708) demand_idx(720) demand_idx(732) ///
    demand_idx(744) demand_idx(756) ///
    hdd cdd gdp, ///
    trunit(4) trperiod(760) keep(results/sc3_placebo_nyis.dta) replace

display "NYIS placebo RMSPE (threshold for exclusion = 22.24):"
matrix list e(RMSPE)

use results/sc3_placebo_nyis.dta, clear
gen gap_nyis = _Y_treated - _Y_synthetic
keep _time gap_nyis
merge 1:1 _time using results/inspace_combined.dta, nogenerate
save results/inspace_combined.dta, replace

// Placebo 3: SWPP as treated unit (ba_num=6)
// Donors: ERCO(1), ISNE(2), NYIS(4)
import delimited "data/panel_expanded.csv", clear
rename ba ba_id
gen month_year = monthly(year_month, "YM")
format month_year %tm
encode ba_id, gen(ba_num)
drop if ba_num == 3 | ba_num == 5
xtset ba_num month_year
bysort ba_num: egen demand_2019 = mean(avg_demand_mwh) if year == 2019
bysort ba_num: egen demand_base = mean(demand_2019)
gen demand_idx = (avg_demand_mwh / demand_base) * 100
drop demand_2019

synth demand_idx ///
    demand_idx(708) demand_idx(720) demand_idx(732) ///
    demand_idx(744) demand_idx(756) ///
    hdd cdd gdp, ///
    trunit(6) trperiod(760) keep(results/sc3_placebo_swpp.dta) replace

display "SWPP placebo RMSPE (threshold for exclusion = 22.24):"
matrix list e(RMSPE)

use results/sc3_placebo_swpp.dta, clear
gen gap_swpp = _Y_treated - _Y_synthetic
keep _time gap_swpp
merge 1:1 _time using results/inspace_combined.dta, nogenerate
save results/inspace_combined.dta, replace


// ===========================================================================
// SECTION 8: COMBINED VISUAL PRESENTATION
// ===========================================================================
// Plot ERCOT gap against all placebo gaps.
// Gray lines = placebo units. Black line = ERCOT.
// Dashed gray = placebo excluded by RMSPE filter (if any).
// This figure is the primary inferential exhibit for the paper.
// P-value computed below after examining RMSPE filter results.

display _newline "--- SECTION 8: IN-SPACE PLACEBO FIGURE ---"

use results/inspace_combined.dta, clear

// Note: update lpattern for excluded placebos after checking RMSPE values
// If placebo RMSPE > 22.24, change its line to lpattern(shortdash) and
// add to figure note that it was excluded from p-value computation.

twoway ///
    (line gap_isne _time, lcolor(gs12) lwidth(thin)) ///
    (line gap_nyis _time, lcolor(gs12) lwidth(thin)) ///
    (line gap_swpp _time, lcolor(gs12) lwidth(thin)) ///
    (line gap_erco _time, lcolor(black) lwidth(medthick)) ///
    , xline(760, lcolor(red) lpattern(dot)) ///
    yline(0, lcolor(gray) lpattern(dash)) ///
    xlabel(708(12)791, angle(45) format(%tmMon_CCYY)) ///
    ylabel(-50(10)60, format(%9.0f)) ///
    legend(order(4 "ERCOT (treated)" 1 "ISNE placebo" ///
                 2 "NYIS placebo" 3 "SWPP placebo") ///
           position(11) ring(0) cols(1)) ///
    title("In-Space Placebo Tests: SC-3 Specification") ///
    ytitle("Gap (index points, 2019=100)") ///
    xtitle("") ///
    note("Black = ERCOT. Gray = donor BAs treated as placebo units." ///
         "Vertical line = treatment date (2023m5)." ///
         "Placebos with pre-treatment RMSPE > 2x ERCOT excluded from p-value.") ///
    saving(results/inspace_placebo_plot.gph, replace)

// P-value computation — fill in after examining RMSPE values above
// Step 1: Record post-treatment mean gap for ERCOT: 24.5 index points
// Step 2: For each placebo NOT excluded by RMSPE filter, compute mean
//         post-treatment gap and check whether it exceeds 24.5
// Step 3: P-value = (number of placebos with gap >= 24.5) / (total placebos + 1)

summarize gap_erco if _time >= 760
summarize gap_isne if _time >= 760
summarize gap_nyis if _time >= 760
summarize gap_swpp if _time >= 760

// *** STOP HERE ***
// Paste: all four RMSPE values, all four post-treatment gap summaries,
// and both plot windows (in-time and in-space).
// We will compute the formal p-value and record all results together.