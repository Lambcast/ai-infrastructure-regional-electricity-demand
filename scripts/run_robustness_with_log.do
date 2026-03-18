cd "C:\Users\alamb\OneDrive\Alans Work Folder\independent projects\ai-electricity-demand"

capture log close _all
log using "outputs/tables/robustness_table_raw.log", replace text name(robustness)

do "scripts/phase2_panel_regression.do"

capture log close robustness