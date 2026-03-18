/*
================================================================================
AI Infrastructure & Regional Electricity Demand
Phase 3: CAISO Synthetic Control — Bai-Perron + SC

Author:       Alan Lamb
Affiliation:  Lambcast Applied Economics | M.S. Applied Economics, UMD
Date:         March 2026

--------------------------------------------------------------------------------
PURPOSE

CAISO is the second treated unit in the comparative institutional analysis.
California's regulated electricity market contrasts with ERCOT's deregulated
structure. Both received significant data center investment over 2019-2025.
This do-file estimates whether CAISO demand diverged from a synthetic
counterfactual in the same way ERCOT did — and if so, by how much.

Expected finding: CAISO average demand shows no clean structural break
(flat trend, strong seasonality). CAISO minimum demand shows modest
elevation. The ERCOT vs CAISO contrast is the comparative finding.

--------------------------------------------------------------------------------
INPUTS

  data/panel_caiso_comparison.csv  — 84 rows, CAISO demand + controls
  data/panel_expanded.csv          — 504 rows, 6 BAs donor pool

--------------------------------------------------------------------------------
OUTPUTS

  results/caiso_bp_results.txt     — Bai-Perron test statistics
  results/caiso_sc_results.dta     — SC results (avg demand)
  results/caiso_sc_min_results.dta — SC results (min demand)
  results/caiso_sc_gap_plot.gph    — gap plot
  results/caiso_sc_min_gap_plot.gph

--------------------------------------------------------------------------------
DONOR POOL

Low-exposure BAs (same classification as ERCOT SC-3):
  ISNE = ISO New England
  NYIS = New York ISO
  SWPP = Southwest Power Pool

ERCO excluded — treated unit in ERCOT analysis.
PJM excluded — high data center exposure (Northern Virginia).
MISO excluded — moderate exposure, queue reform artifact in 2022.

Use ISNE/NYIS/SWPP only for the preferred specification.
Run PJM+MISO as contaminated lower bound for comparison.

================================================================================
*/

// ===========================================================================
// SECTION 0: SETUP
// ===========================================================================

cd "C:\Users\alamb\OneDrive\Alans Work Folder\independent projects\ai-electricity-demand"

capture mkdir "results"
capture log close

log using "logs/phase3_caiso_sc.log", replace text
display "Session started: $S_DATE $S_TIME"

// ===========================================================================
// SECTION 1: LOAD AND PREPARE CAISO PANEL
// ===========================================================================

display _newline "--- SECTION 1: LOAD CAISO DATA ---"

import delimited "data/panel_caiso_comparison.csv", clear
display "CAISO rows: `=_N'"

// Date variable
gen month_year = monthly(year_month, "YM")
format month_year %tm

// BA numeric for xtset
gen ba_num = 1   // CAISO = 1 in this standalone panel

tsset month_year

// Verify
tabstat avg_demand_mwh, stats(mean sd min max)
tabstat min_demand_idx, stats(mean sd min max)

// Flag suspicious 2025m7 outlier in min_demand_idx
list year_month min_demand_idx if min_demand_idx < 80
// Expected: 2025-07 shows ~75.8 — data artifact, noted for paper

// Index avg demand to 2019 average = 100 (use demand_idx already in file)
// Verify 2019 base = 100
tabstat demand_idx if year == 2019, stats(mean)
// Expected: ~100

// ===========================================================================
// SECTION 2: BAI-PERRON STRUCTURAL BREAK TEST — CAISO AVERAGE DEMAND
// ===========================================================================

display _newline "--- SECTION 2: BAI-PERRON TEST — CAISO AVG DEMAND ---"

// Test for structural break in CAISO average demand index
// Expected: no clean break — flat trajectory with seasonal variation
// If UDmax < critical value, fail to reject null of no break
// This is itself the finding: ERCOT broke, CAISO did not

xtbreak test demand_idx, breakconstant hypothesis(2) breaks(3)

// Record result before proceeding
// If break found: record date, use as CAISO treatment date
// If no break: report UDmax and critical values, document as null finding

// Also test minimum demand index
display _newline "Bai-Perron test — CAISO min demand index:"
xtbreak test min_demand_idx, breakconstant hypothesis(2) breaks(3)

// Estimate break date if test rejects (run regardless, record result)
display _newline "Break date estimate — CAISO avg demand:"
xtbreak estimate demand_idx, breakconstant breaks(1)

display _newline "Break date estimate — CAISO min demand:"
xtbreak estimate min_demand_idx, breakconstant breaks(1)

// RECORD RESULTS HERE before proceeding to SC:
// UDmax statistic for avg demand: [record]
// UDmax statistic for min demand: [record]
// Break date avg demand:  [record or "no significant break"]
// Break date min demand:  [record or "no significant break"]

// ===========================================================================
// SECTION 3: BUILD COMBINED PANEL FOR SYNTHETIC CONTROL
// ===========================================================================

display _newline "--- SECTION 3: BUILD COMBINED PANEL ---"

// Load expanded panel (ERCO, ISNE, MISO, NYIS, PJM, SWPP)
import delimited "data/panel_expanded.csv", clear
display "Expanded panel rows: `=_N'"

// Rename ba to ba_id for consistency
rename ba ba_id

// Generate month_year
gen month_year = monthly(year_month, "YM")
format month_year %tm

// Index avg demand to 2019 average = 100 for each BA
bysort ba_id: egen demand_2019 = mean(avg_demand_mwh) if year == 2019
bysort ba_id: egen demand_base = mean(demand_2019)
gen demand_idx_exp = (avg_demand_mwh / demand_base) * 100
drop demand_2019

// Keep only donor BAs needed for CAISO SC
// Exclude ERCO (treated in ERCOT analysis, not a clean donor)
// Keep: ISNE, MISO, NYIS, PJM, SWPP
keep if inlist(ba_id, "ISNE", "MISO", "NYIS", "PJM", "SWPP")
display "Donor BA rows after filtering: `=_N'"
tab ba_id

// Load CAISO panel and append
import delimited "data/panel_caiso_comparison.csv", clear
gen ba_id = "CISO"
gen month_year_num = monthly(year_month, "YM")
rename month_year_num month_year_stata
// Rename to avoid conflict
rename demand_idx demand_idx_caiso
rename min_demand_idx min_demand_idx_caiso

// Save CAISO temp
tempfile caiso_temp
save `caiso_temp'

// Reload expanded (donors)
import delimited "data/panel_expanded.csv", clear
rename ba ba_id
gen month_year = monthly(year_month, "YM")
format month_year %tm
keep if inlist(ba_id, "ISNE", "MISO", "NYIS", "PJM", "SWPP")

// Index demand
bysort ba_id: egen demand_2019b = mean(avg_demand_mwh) if year == 2019
bysort ba_id: egen demand_baseb = mean(demand_2019b)
gen demand_idx = (avg_demand_mwh / demand_baseb) * 100
drop demand_2019b

// Add min demand index — use min_demand_idx already in expanded panel
// (it's already indexed)

// Append CAISO
gen demand_idx_caiso   = .
gen min_demand_idx_caiso = .

// Build unified panel differently — use synth directly on separate datasets
// synth requires treated + donors in same dataset with shared index variable

// Encode BA
encode ba_id, gen(ba_num)
display "BA encoding (donors):"
label list ba_num

// CAISO gets ba_num = 0 — assign after encoding donors
// Simpler: build panel from scratch

// ===========================================================================
// SECTION 4: SYNTHETIC CONTROL — CAISO (PREFERRED APPROACH)
// ===========================================================================
// NOTE: synth requires treated and donor units in the same dataset.
// Build a combined dataset: CAISO (treated) + low-exposure donors.
// Use same index variable approach as ERCOT SC.

display _newline "--- SECTION 4: SYNTHETIC CONTROL SETUP ---"

// Step 4a: Reload and prep CAISO
import delimited "data/panel_caiso_comparison.csv", clear
gen ba_id = "CISO"
gen month_year = monthly(year_month, "YM")
format month_year %tm

// Index avg demand to 2019 = 100 (demand_idx already exists — use it)
// Index min demand (min_demand_idx already exists)

// Step 4b: Reload donor BAs from expanded panel
preserve
import delimited "data/panel_expanded.csv", clear
rename ba ba_id
gen month_year = monthly(year_month, "YM")
format month_year %tm

// Index avg demand per BA
bysort ba_id: egen d2019 = mean(avg_demand_mwh) if year == 2019
bysort ba_id: egen dbase = mean(d2019)
gen demand_idx = (avg_demand_mwh / dbase) * 100
drop d2019 dbase

keep if inlist(ba_id, "ISNE", "NYIS", "SWPP", "PJM", "MISO")

tempfile donors
save `donors'
restore

// Step 4c: Merge CAISO and donors into one dataset
append using `donors'

// Encode ba_id — CISO must get a specific number for trunit
// Sort so CISO = 1
gen ba_sort = (ba_id == "CISO")
sort ba_sort ba_id
encode ba_id, gen(ba_num)
drop ba_sort

display "BA encoding for CAISO SC:"
label list ba_num
tab ba_id ba_num

xtset ba_num month_year

// Verify CISO ba_num value
levelsof ba_num if ba_id == "CISO", local(ciso_num)
display "CISO ba_num = `ciso_num'"

// Verify indexing
tabstat demand_idx if year == 2019, by(ba_id) stats(mean)
// Expected: all BAs ≈ 100

tabstat demand_idx if month_year >= 760, by(ba_id) stats(mean)
// CAISO should show near 100-110 (no strong divergence)
// ERCOT-equivalent would show ~124 — that contrast is the finding

// ===========================================================================
// SECTION 5: SC-1 — CAISO WITH PJM + MISO DONORS (LOWER BOUND)
// ===========================================================================

display _newline "--- SECTION 5: CAISO SC-1 — PJM + MISO DONORS ---"

// Treatment date: use same date as ERCOT (2023m5 = tm 760)
// If Bai-Perron found no break in CAISO, this is a robustness check
// The null result (small gap) is itself the finding

// Get ba_num values for PJM and MISO
levelsof ba_num if ba_id == "PJM",  local(pjm_num)
levelsof ba_num if ba_id == "MISO", local(miso_num)
display "PJM ba_num = `pjm_num', MISO ba_num = `miso_num'"

synth demand_idx ///
    demand_idx(708) demand_idx(720) demand_idx(732) ///
    demand_idx(744) demand_idx(756) ///
    hdd cdd gdp, ///
    trunit(`ciso_num') trperiod(760) ///
    keep(results/caiso_sc1_results.dta) replace

// Compute and summarize gap
use results/caiso_sc1_results.dta, clear
gen gap = _Y_treated - _Y_synthetic

summarize gap if _time >= 760
local caiso_sc1_postgap = r(mean)
display "CAISO SC-1 post-treatment mean gap: `caiso_sc1_postgap'"

summarize gap if _time < 760
display "CAISO SC-1 pre-treatment mean gap: `r(mean)'"

// Gap plot
twoway line gap _time, lcolor(black) lwidth(medium) ///
    xline(760, lcolor(red) lpattern(dot)) ///
    yline(0, lcolor(gray) lpattern(dash)) ///
    xlabel(708(12)791, angle(45) format(%tmMon_CCYY)) ///
    ylabel(-30(10)50, format(%9.0f)) ///
    title("CAISO SC-1: Avg Demand Gap vs Synthetic") ///
    ytitle("Gap (index points, 2019=100)") ///
    note("Donor pool: PJM + MISO (contaminated lower bound)." ///
         "Treatment date: 2023m5 (same as ERCOT).") ///
    saving(results/caiso_sc1_gap_plot.gph, replace)

// Reload combined panel
import delimited "data/panel_caiso_comparison.csv", clear
gen ba_id = "CISO"
gen month_year = monthly(year_month, "YM")
format month_year %tm
append using `donors'
gen ba_sort = (ba_id == "CISO")
sort ba_sort ba_id
encode ba_id, gen(ba_num)
drop ba_sort
levelsof ba_num if ba_id == "CISO", local(ciso_num)
xtset ba_num month_year

// ===========================================================================
// SECTION 6: SC-2 — CAISO WITH CLEAN DONOR POOL (ISNE/NYIS/SWPP)
// ===========================================================================

display _newline "--- SECTION 6: CAISO SC-2 — CLEAN DONOR POOL ---"

// Keep only CISO + low-exposure donors
keep if inlist(ba_id, "CISO", "ISNE", "NYIS", "SWPP")
xtset ba_num month_year

levelsof ba_num if ba_id == "CISO", local(ciso_num2)

synth demand_idx ///
    demand_idx(708) demand_idx(720) demand_idx(732) ///
    demand_idx(744) demand_idx(756) ///
    hdd cdd, ///
    trunit(`ciso_num2') trperiod(760) ///
    keep(results/caiso_sc2_results.dta) replace

// Compute gap
use results/caiso_sc2_results.dta, clear
gen gap = _Y_treated - _Y_synthetic

summarize gap if _time >= 760
local caiso_sc2_postgap = r(mean)
display "CAISO SC-2 post-treatment mean gap: `caiso_sc2_postgap'"

summarize gap if _time < 760
display "CAISO SC-2 pre-treatment RMSPE context: pre-gap = `r(mean)'"

// Gap plot
twoway line gap _time, lcolor(black) lwidth(medium) ///
    xline(760, lcolor(red) lpattern(dot)) ///
    yline(0, lcolor(gray) lpattern(dash)) ///
    xlabel(708(12)791, angle(45) format(%tmMon_CCYY)) ///
    ylabel(-30(10)50, format(%9.0f)) ///
    title("CAISO SC-2: Avg Demand Gap vs Synthetic") ///
    ytitle("Gap (index points, 2019=100)") ///
    note("Donor pool: ISNE, NYIS, SWPP (low-exposure)." ///
         "Treatment date: 2023m5.") ///
    saving(results/caiso_sc2_gap_plot.gph, replace)

// ===========================================================================
// SECTION 7: SC — CAISO MINIMUM DEMAND
// ===========================================================================

display _newline "--- SECTION 7: CAISO SC — MINIMUM DEMAND ---"

// Reload full combined panel with min_demand_idx
import delimited "data/panel_caiso_comparison.csv", clear
gen ba_id = "CISO"
gen month_year = monthly(year_month, "YM")
format month_year %tm

// For donors, need min_demand_idx — it's in panel_expanded.csv
import delimited "data/panel_expanded.csv", clear
rename ba ba_id
gen month_year = monthly(year_month, "YM")
format month_year %tm
keep if inlist(ba_id, "ISNE", "NYIS", "SWPP")
// min_demand_idx already in expanded panel

tempfile donors_min
save `donors_min'

import delimited "data/panel_caiso_comparison.csv", clear
gen ba_id = "CISO"
gen month_year = monthly(year_month, "YM")
format month_year %tm
append using `donors_min'

gen ba_sort = (ba_id == "CISO")
sort ba_sort ba_id
encode ba_id, gen(ba_num)
drop ba_sort
levelsof ba_num if ba_id == "CISO", local(ciso_min_num)
xtset ba_num month_year

// Re-verify min demand index base
tabstat min_demand_idx if year == 2019, by(ba_id) stats(mean)

synth min_demand_idx ///
    min_demand_idx(708) min_demand_idx(720) min_demand_idx(732) ///
    min_demand_idx(744) min_demand_idx(756) ///
    hdd cdd, ///
    trunit(`ciso_min_num') trperiod(760) ///
    keep(results/caiso_sc_mindemand_results.dta) replace

// Compute gap
use results/caiso_sc_mindemand_results.dta, clear
gen gap = _Y_treated - _Y_synthetic

summarize gap if _time >= 760
local caiso_min_postgap = r(mean)
display "CAISO min demand SC post-treatment mean gap: `caiso_min_postgap'"

summarize gap if _time < 760

// Gap plot
twoway line gap _time, lcolor(black) lwidth(medium) ///
    xline(760, lcolor(red) lpattern(dot)) ///
    yline(0, lcolor(gray) lpattern(dash)) ///
    xlabel(708(12)791, angle(45) format(%tmMon_CCYY)) ///
    ylabel(-40(10)60, format(%9.0f)) ///
    title("CAISO SC: Min Demand Gap vs Synthetic") ///
    ytitle("Gap (index points, 2019=100)") ///
    note("Donor pool: ISNE, NYIS, SWPP." ///
         "Treatment date: 2023m5.") ///
    saving(results/caiso_sc_mindemand_gap_plot.gph, replace)

// ===========================================================================
// SECTION 8: RECORD ALL RESULTS
// ===========================================================================

display _newline "--- SECTION 8: RESULTS SUMMARY ---"
display "==================================================="
display "CAISO SYNTHETIC CONTROL RESULTS — March 2026"
display "==================================================="
display ""
display "Bai-Perron test — avg demand:"
display "  [paste UDmax and break date from Section 2 output]"
display ""
display "Bai-Perron test — min demand:"
display "  [paste UDmax and break date from Section 2 output]"
display ""
display "SC-1 (PJM+MISO donors, avg demand):"
display "  Post-treatment mean gap: `caiso_sc1_postgap' index points"
display ""
display "SC-2 (ISNE/NYIS/SWPP donors, avg demand):"
display "  Post-treatment mean gap: `caiso_sc2_postgap' index points"
display ""
display "SC min demand (ISNE/NYIS/SWPP donors):"
display "  Post-treatment mean gap: `caiso_min_postgap' index points"
display ""
display "Compare with ERCOT:"
display "  ERCOT SC-3 avg demand gap:  24.5 index points"
display "  ERCOT SC-3 min demand gap:  34.8 index points"
display "==================================================="

log close
display "Done."
