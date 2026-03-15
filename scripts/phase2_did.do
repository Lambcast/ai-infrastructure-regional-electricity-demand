/*
================================================================================
AI Infrastructure & Regional Electricity Demand
Phase 2: DiD with Low-Exposure Controls — Layer 3 Identification

Author:       Alan Lamb
Affiliation:  Lambcast Applied Economics | M.S. Applied Economics, UMD
Date:         March 2026
Contact:      lambcast.net

--------------------------------------------------------------------------------
REPLICATION NOTES

Software:     Stata (tested on Stata 17+)
Dependencies: reghdfe, ftools, boottest
              Install via ssc if not present.

Input:        data/panel_expanded.csv
              504 rows, 6 balancing authorities x 84 months (2019-01 to 2025-12)
              Built by scripts/build_panel.py and scripts/pull_controls.py

Output:       logs/phase2_did.log   — full session log

--------------------------------------------------------------------------------
DESIGN NOTES

This do file implements Layer 3 of the four-layer identification strategy.
See Phase2_Methodology_Workflow.docx for full specification decisions.

Treated unit:   ERCO (ba_num = 1)
Control units:  ISNE (2), NYIS (4), SWPP (6)
                Classified as low-exposure using cumulative 100MW+ queue
                filings from LBL data. Same classification criterion as
                synthetic control donor pool — one decision serving double duty.
                PJM (5) and MISO (3) excluded — contaminated by data center
                investment over 2019-2025.

Treatment date: 2023m5 (month_year = 760)
                Same as Bai-Perron structural break date from
                phase2_panel_regression.do. Not revisited after
                synthetic control results were examined.

Outcome:        demand_idx — indexed demand, 2019 average = 100 for each BA.
                Indexing removes absolute scale differences across BAs.
                Same construction as synthetic control do file.

Expected result: DiD coefficient > SC-3 gap (24.5) would confirm
                contamination lower bound story — low-exposure controls
                produce a larger estimate than contaminated SC donors.
                DiD coefficient < SC-3 gap reflects TWFE absorption of
                the persistent level shift — documented and explained.

--------------------------------------------------------------------------------
INFERENCE NOTE

Four clusters (ERCO, ISNE, NYIS, SWPP). Wild cluster bootstrap with Webb
weights produced an unbounded confidence interval due to insufficient power
with 4 clusters — the bootstrap distribution never crosses the critical value
across any parameter value. Rademacher weights used instead for the DiD,
performing full enumeration of all 2^4 = 16 sign combinations. This produces
a bounded CI and a minimum achievable p-value of 1/16 = 0.0625.

Webb weights preferred over Rademacher in general (smoother approximation
at small G) but Rademacher's exact enumeration is necessary here to obtain
a bounded confidence set. This is documented explicitly and does not
affect the coefficient estimate.

References:
  Roodman, D., Nielsen, M.O., MacKinnon, J.G., and Webb, M.D. (2019).
  Fast and wild: Bootstrap inference in Stata using boottest.
  The Stata Journal, 19(1), 4-60.

--------------------------------------------------------------------------------
SPECIFICATION DECISIONS — LOCKED BEFORE STATA WAS OPENED

  1. Treatment date: 2023m5 — same as Bai-Perron result, not revisited
  2. Control units: ISNE, NYIS, SWPP — classified from LBL queue data
  3. Outcome: demand_idx — indexed to 2019=100, same as synthetic control
  4. Inference: boottest only — regression clustered SEs not reported
  5. Every specification runs and is reported — nothing dropped

================================================================================
*/


// ===========================================================================
// SECTION 0: ENVIRONMENT SETUP
// ===========================================================================

cd "C:\Users\alamb\OneDrive\Alans Work Folder\independent projects\ai-electricity-demand"

capture mkdir "logs"

capture log close
log using "logs/phase2_did.log", replace text

display "Session started: $S_DATE $S_TIME"
display "Stata version: `c(stata_version)'"


// ===========================================================================
// SECTION 1: DATA PREPARATION
// ===========================================================================

display _newline "--- SECTION 1: DATA PREPARATION ---"

import delimited "data/panel_expanded.csv", clear
display "Observations loaded: `=_N'"

rename ba ba_id
gen month_year = monthly(year_month, "YM")
format month_year %tm
encode ba_id, gen(ba_num)

display "BA encoding:"
label list ba_num
// Expected: 1=ERCO, 2=ISNE, 3=MISO, 4=NYIS, 5=PJM, 6=SWPP

// Drop contaminated donors — PJM(5) and MISO(3)
drop if ba_num == 3 | ba_num == 5
display "Observations after dropping PJM and MISO: `=_N'"
// Expected: 336 (4 BAs x 84 months)

xtset ba_num month_year
// Expected: strongly balanced, 2019m1-2025m12, delta 1 month

// Index demand — 2019 average = 100 for each BA
// Same construction as synthetic control do file
bysort ba_num: egen demand_2019 = mean(avg_demand_mwh) if year == 2019
bysort ba_num: egen demand_base = mean(demand_2019)
gen demand_idx = (avg_demand_mwh / demand_base) * 100
drop demand_2019

// Verify indexing
tabstat demand_idx if year == 2019, by(ba_id) stats(mean)
// Expected: all BAs near 100

// Treatment indicators
gen post    = (month_year >= 760)
gen treated = (ba_num == 1)
gen did     = post * treated

// Pre/post descriptive check
display _newline "Pre-treatment mean demand index by BA:"
tabstat demand_idx if post == 0, by(ba_id) stats(mean)

display _newline "Post-treatment mean demand index by BA:"
tabstat demand_idx if post == 1, by(ba_id) stats(mean)


// ===========================================================================
// SECTION 2: PARALLEL TRENDS — VISUAL CHECK
// ===========================================================================
// With 4 units, a formal parallel trends test has very low power.
// Report pre-treatment means and SDs as the primary evidence.
// Visual inspection of pre-treatment trajectories in co-movement charts
// (built in Phase 1) provides supporting evidence.

display _newline "--- SECTION 2: PRE-TREATMENT TRENDS ---"

tabstat demand_idx if post == 0, by(ba_id) stats(mean sd min max)

// Note: ERCOT pre-treatment mean should be near 100 (indexed).
// Low-exposure BAs should also be near 100.
// Large pre-treatment differences would threaten parallel trends.


// ===========================================================================
// SECTION 3: PRIMARY DiD SPECIFICATION
// ===========================================================================
// Outcome: demand_idx
// Treatment: did = post x treated (ERCO x post-2023m5)
// Fixed effects: BA-level and month-year
// Controls: hdd, cdd, gdp
// Inference: boottest with Rademacher weights
//            Webb weights produced unbounded CI — see inference note in header.
// Note: absorb(month_year) only — i.ba_num carried explicitly
//       Required for boottest compatibility with reghdfe

display _newline "--- SECTION 3: PRIMARY DiD ---"

reghdfe demand_idx did hdd cdd gdp i.ba_num, absorb(month_year) cluster(ba_id)

// Rademacher weights — full enumeration of 2^4 = 16 sign combinations
// Webb weights produced unbounded CI with 4 clusters
boottest did, boottype(wild) cluster(ba_id) reps(999) seed(42) weight(rademacher)

// DiD PRIMARY RESULTS (confirmed March 2026):
//   Coefficient:        9.8 index points
//   Bootstrap CI:       [-12.1, 57.9] — Rademacher, 16-draw enumeration
//   Bootstrap p-value:  0.125
//   N:                  336
//   Weight note:        Webb weights produced unbounded CI with 4 clusters.
//                       Rademacher used — bounded via full 2^4 enumeration.
//                       Minimum achievable p-value = 1/16 = 0.0625.
//   Interpretation:     Coefficient positive (9.8) but below SC-3 gap (24.5).
//                       TWFE month-year FE absorb the persistent level shift
//                       — same problem documented in panel regression.
//                       DiD estimate is a lower bound under restrictive
//                       parallel trends assumption. SC-3 synthetic control
//                       is the less restrictive and more credible estimate.
//                       Consistent ordering across all TWFE-based methods.


// ===========================================================================
// SECTION 4: ROBUSTNESS — NO GDP CONTROL
// ===========================================================================

display _newline "--- SECTION 4: DiD ROBUSTNESS NO GDP ---"

reghdfe demand_idx did hdd cdd i.ba_num, absorb(month_year) cluster(ba_id)

boottest did, boottype(wild) cluster(ba_id) reps(999) seed(42) weight(rademacher)

// Record coefficient and boottest output after running


// ===========================================================================
// SECTION 5: SYNTHESIS — COMPARISON ACROSS ALL METHODS
// ===========================================================================
// Report estimated range across all identification layers.
// This table is the basis for the synthesis paragraph in the paper.

display _newline "--- SECTION 5: SYNTHESIS ACROSS IDENTIFICATION LAYERS ---"
display ""
display "IDENTIFICATION LAYER SUMMARY:"
display "----------------------------------------------"
display "Layer 1 — Panel regression S1:    0.029 MWh per MW (p=0.063)"
display "Layer 2 — SC-3 synthetic control: 24.5 index points (p=0.25)"
display "Layer 3 — DiD low-exposure:       9.8  index points (p=0.125)"
display "Layer 4 — Narrative validation:   pending (energization overlay)"
display "----------------------------------------------"
display ""
display "SC-3 is primary estimate. All methods positive."
display "TWFE-based methods (panel regression, DiD) attenuate due to"
display "level shift absorption by time fixed effects — documented throughout."
display "Synthetic control does not impose time FE and recovers larger gap."


// ===========================================================================
// END OF PHASE 2 DiD DO FILE
// ===========================================================================

log close
