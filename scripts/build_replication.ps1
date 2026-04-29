$src = "C:\Users\alamb\OneDrive\Alans Work Folder\independent projects\ai-electricity-demand"
$dst = "C:\Users\alamb\OneDrive\Alans Work Folder\independent projects\ai-electricity-demand-replication"

# Build the directory tree
New-Item -ItemType Directory -Path $dst -Force | Out-Null
New-Item -ItemType Directory -Path "$dst\data" -Force | Out-Null
New-Item -ItemType Directory -Path "$dst\scripts" -Force | Out-Null
New-Item -ItemType Directory -Path "$dst\outputs" -Force | Out-Null
New-Item -ItemType Directory -Path "$dst\outputs\tables" -Force | Out-Null
New-Item -ItemType Directory -Path "$dst\paper" -Force | Out-Null

# Derived data only (no raw third-party files)
$dataFiles = @(
    "panel_with_controls.csv",
    "panel_expanded.csv",
    "panel_caiso_comparison.csv",
    "ercot_zone_monthly.csv",
    "gdp_controls.csv",
    "weather_controls.csv",
    "structural_projection.csv",
    "forecasts_arima.csv",
    "forecasts_prophet.csv",
    "forecasts_xgboost.csv"
)
foreach ($f in $dataFiles) {
    Copy-Item "$src\data\$f" "$dst\data\$f"
}

# All scripts, flat, mirror existing structure
Copy-Item "$src\scripts\*" "$dst\scripts\" -Recurse

# Final figures
$figures = @(
    "demand_annual_avg_by_region.png",
    "demand_indexed_growth.png",
    "demand_monthly_by_region.png",
    "queue_annual_gw_filed.png",
    "queue_cumulative_gw.png",
    "queue_monthly_mw_filed.png",
    "queue_ercot_by_type.png",
    "histogram_project_mw.png",
    "did_parallel_trends.png",
    "controls_verification.png",
    "comovement_combined.png",
    "comovement_erco.png",
    "comovement_miso.png",
    "comovement_pjm.png",
    "sc1_gap_plot.png",
    "sc1_gap_only_plot.png",
    "sc2_gap_plot.png",
    "sc3_gap_plot.png",
    "sc3_mindemand_plot.png",
    "sc3_mindemand_gap_overlay.png",
    "sc3_mindemand_with_energizations.png",
    "sc3_avg_demand_twopanel.png",
    "sc3_robustness_2022m1_plot.png",
    "inspace_placebo_plot.png",
    "intime_placebo_plot.png",
    "inspace_placebos_mindemand_sc3.png",
    "mindemand_inspace_plot.png",
    "ercot_avg_vs_min_indexed.png",
    "ercot_caiso_comparison.png",
    "caiso_demand_diagnostic.png",
    "caiso_sc_mindemand_gap_plot.png",
    "caiso_sc1_gap_plot.png",
    "caiso_sc2_gap_plot.png",
    "caiso_vs_ercot_comparison.png"
)
foreach ($f in $figures) {
    if (Test-Path "$src\outputs\$f") {
        Copy-Item "$src\outputs\$f" "$dst\outputs\$f"
    }
}

# Final tables
Copy-Item "$src\outputs\tables\table1_descriptive_stats.csv" "$dst\outputs\tables\"
Copy-Item "$src\outputs\tables\table1_descriptive_stats.docx" "$dst\outputs\tables\"
Copy-Item "$src\outputs\tables\table2_robustness.docx" "$dst\outputs\tables\"
Copy-Item "$src\outputs\tables\table3_synthesis.csv" "$dst\outputs\tables\"
Copy-Item "$src\outputs\tables\table3_synthesis.docx" "$dst\outputs\tables\"

# Latest paper PDF (we may swap for the SSRN-published version after verifying)
Copy-Item "$src\Paper and drafts\AI Infrastructure and Regional Electricity Demand -1.2.pdf" `
          "$dst\paper\AI_Infrastructure_and_Regional_Electricity_Demand.pdf"

Write-Host ""
Write-Host "Replication package built at: $dst" -ForegroundColor Green
Write-Host ""
Get-ChildItem -Recurse $dst | Select-Object FullName, Length | Sort-Object FullName