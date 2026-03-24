/*
================================================================================
08_make_figures_2_4.do
AI Infrastructure and Regional Electricity Demand
Replication package — Figure generation

Produces:
  outputs/queue_monthly_mw_filed.png       (Figure 2 in paper)
  outputs/ercot_avg_vs_min_indexed.png     (Figure 4 in paper)

Input data:
  data/panel_base.csv          — demand + queue variables, 252 obs
  data/panel_load_shape.csv    — adds demand_min and load shape variables

Run from project root:
  do scripts/08_make_figures_2_4.do

Author:      Alan Lamb
Affiliation: Lambcast Applied Economics | M.S. Applied Economics, UMD
Date:        March 2026
Contact:     lambcast.net
================================================================================
*/

cd "C:\Users\alamb\OneDrive\Alans Work Folder\independent projects\ai-electricity-demand"

capture mkdir "outputs"

display "Session started: $S_DATE $S_TIME"


// ===========================================================================
// FIGURE 2
// Monthly large-project (≥100 MW) queue filings by balancing authority
// 2019--2024, 6-month moving average
//
// Variable: queue_mw_filed_large — matches the primary treatment variable
// All three BAs shown; MISO capped at 15 GW for display because
// uncapped peak (~30 GW, 2022-2023) reflects documented queue reform
// batch filings, not underlying demand. See Appendix C.3 (winsorization note).
// PJM drops near zero post-2022 due to interconnection study pause.
// ===========================================================================

import delimited "data/panel_base.csv", clear
rename ba ba_id
gen month_year = monthly(year_month, "YM")
format month_year %tm
encode ba_id, gen(ba_num)

gen queue_gw = queue_mw_filed_large / 1000
keep if year <= 2024
keep ba_id month_year queue_gw
reshape wide queue_gw, i(month_year) j(ba_id) string

rename queue_gwERCO  ercot_gw
rename queue_gwMISO  miso_gw
rename queue_gwPJM   pjm_gw

tsset month_year

// 6-month moving average using lag operators
gen ercot_ma6 = (ercot_gw + L.ercot_gw + L2.ercot_gw + ///
                 L3.ercot_gw + L4.ercot_gw + L5.ercot_gw) / 6
gen miso_ma6  = (miso_gw  + L.miso_gw  + L2.miso_gw  + ///
                 L3.miso_gw  + L4.miso_gw  + L5.miso_gw ) / 6
gen pjm_ma6   = (pjm_gw   + L.pjm_gw   + L2.pjm_gw   + ///
                 L3.pjm_gw   + L4.pjm_gw   + L5.pjm_gw  ) / 6

// Cap MISO at 15 GW for display only — underlying data unchanged
gen miso_plot = min(miso_ma6, 15)

// Rectangular shaded region: post-January 2022 (AI-driven filing surge)
local surge = monthly("2022m1", "YM")
gen shade_lo = 0
gen shade_hi = 0
replace shade_hi = 15 if month_year >= `surge'

twoway ///
    (rarea shade_lo shade_hi month_year, ///
        color("210 228 248%55") lwidth(none)) ///
    (line ercot_ma6 month_year, ///
        lcolor("180 25 25") lwidth(medthick) lpattern(solid)) ///
    (line pjm_ma6 month_year, ///
        lcolor("25 60 140") lwidth(medium) lpattern(dash)) ///
    (line miso_plot month_year, ///
        lcolor("20 115 60") lwidth(medium) lpattern(shortdash_dot)) ///
    , ///
    xlabel( ///
        `=monthly("2019m1","YM")' "2019" ///
        `=monthly("2020m1","YM")' "2020" ///
        `=monthly("2021m1","YM")' "2021" ///
        `=monthly("2022m1","YM")' "2022" ///
        `=monthly("2023m1","YM")' "2023" ///
        `=monthly("2024m1","YM")' "2024" ///
        , labsize(medsmall) angle(0) tlength(medsmall)) ///
    ylabel(0(3)15, labsize(medsmall) angle(0) format(%9.0f) gmin gmax) ///
    ytitle("GW filed per month (6-month MA)", size(medsmall) margin(r=2)) ///
    xtitle("") ///
    legend(order(2 "ERCOT" 3 "PJM" 4 "MISO") ///
        pos(4) ring(0) col(1) size(medsmall) ///
        region(lcolor(gs14) fcolor(white)) bmargin(small)) ///
    note("Notes: Monthly megawatts filed by projects {&ge}100 MW (6-month moving average)." ///
        "Shaded region: post-January 2022. MISO capped at 15 GW for display; peak of ~30 GW" ///
        "(2022-2023) reflects queue reform batch filings, not underlying demand pressure." ///
        "PJM series drops toward zero post-2022 due to an interconnection study pause." ///
        "Source: LBNL Queued Up 2024.", ///
        size(vsmall) margin(t=1)) ///
    graphregion(color(white) margin(small)) ///
    plotregion(color(white) margin(small)) ///
    scheme(s1color) ///
    xsize(6.5) ysize(3.8)

graph export "outputs/queue_monthly_mw_filed.png", replace width(2000)
display "Figure 2 saved: outputs/queue_monthly_mw_filed.png"


// ===========================================================================
// FIGURE 4
// ERCOT indexed average vs. minimum hourly demand, 2019--2025
//
// Both series indexed to 2019 annual average = 100.
// Minimum demand (demand_min) is the lowest hourly reading in each
// BA-month — isolates the always-on baseload floor. The post-2023
// divergence between the two series (minimum rising faster than average)
// is the visual motivation for the minimum demand synthetic control.
// ===========================================================================

import delimited "data/panel_load_shape.csv", clear
rename ba ba_id
gen month_year = monthly(year_month, "YM")
format month_year %tm
keep if ba_id == "ERCO"
tsset month_year

// Index to 2019 annual average
sum avg_demand_mwh if year == 2019
local avg_base = r(mean)
sum demand_min if year == 2019
local min_base = r(mean)

display "ERCOT 2019 avg demand baseline (MWh): `avg_base'"
display "ERCOT 2019 min demand baseline (MWh): `min_base'"
// Expected: avg ~40,046  |  min ~35,374 (matches Table 1)

gen avg_idx = (avg_demand_mwh / `avg_base') * 100
gen min_idx = (demand_min     / `min_base') * 100

// 6-month moving average
gen avg_ma6 = (avg_idx + L.avg_idx + L2.avg_idx + ///
               L3.avg_idx + L4.avg_idx + L5.avg_idx) / 6
gen min_ma6 = (min_idx + L.min_idx + L2.min_idx + ///
               L3.min_idx + L4.min_idx + L5.min_idx) / 6

// Rectangular shaded region: post-May 2023 (Bai-Perron break)
local treat = monthly("2023m5", "YM")
gen shade_lo = 80
gen shade_hi = 80
replace shade_hi = 160 if month_year >= `treat'

twoway ///
    (rarea shade_lo shade_hi month_year, ///
        color("248 215 215%55") lwidth(none)) ///
    (line avg_idx month_year, ///
        lcolor("200 60 60%30") lwidth(thin) lpattern(solid)) ///
    (line min_idx month_year, ///
        lcolor("60 90 180%30") lwidth(thin) lpattern(solid)) ///
    (line avg_ma6 month_year, ///
        lcolor("180 25 25") lwidth(medthick) lpattern(solid)) ///
    (line min_ma6 month_year, ///
        lcolor("25 60 140") lwidth(medthick) lpattern(dash)) ///
    , ///
    yline(100, lcolor(gs13) lwidth(vthin) lpattern(shortdash)) ///
    xline(`treat', lcolor(gs9) lwidth(vthin) lpattern(dot)) ///
    xlabel( ///
        `=monthly("2019m1","YM")' "2019" ///
        `=monthly("2020m1","YM")' "2020" ///
        `=monthly("2021m1","YM")' "2021" ///
        `=monthly("2022m1","YM")' "2022" ///
        `=monthly("2023m1","YM")' "2023" ///
        `=monthly("2024m1","YM")' "2024" ///
        `=monthly("2025m1","YM")' "2025" ///
        , labsize(medsmall) angle(0) tlength(medsmall)) ///
    ylabel(80(10)160, labsize(medsmall) angle(0) format(%9.0f) gmin gmax) ///
    ytitle("Demand index (2019 average = 100)", size(medsmall) margin(r=2)) ///
    xtitle("") ///
    legend(order(4 "Average hourly demand (6-month MA)" ///
                 5 "Minimum hourly demand (6-month MA)") ///
        pos(4) ring(0) col(1) size(medsmall) ///
        region(lcolor(gs14) fcolor(white)) bmargin(small)) ///
    text(158 `=monthly("2023m7","YM")' ///
        "Post-break (May 2023)", ///
        size(vsmall) color(gs8) justification(left)) ///
    note("Notes: ERCOT only. Both series indexed to 2019 annual average = 100." ///
        "Thin lines: monthly values. Thick lines: 6-month moving average." ///
        "Shaded region: post-May 2023 (Bai-Perron break, UDmax = 35.39)." ///
        "Source: EIA Form 930; authors' calculations.", ///
        size(vsmall) margin(t=1)) ///
    graphregion(color(white) margin(small)) ///
    plotregion(color(white) margin(small)) ///
    scheme(s1color) ///
    xsize(6.5) ysize(3.8)

graph export "outputs/ercot_avg_vs_min_indexed.png", replace width(2000)
display "Figure 4 saved: outputs/ercot_avg_vs_min_indexed.png"

display _newline "=== 08_make_figures_2_4.do complete ==="
