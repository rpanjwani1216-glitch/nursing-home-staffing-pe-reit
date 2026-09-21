/* Analysis-only replication entry point.

Run from the repository root:
    do stata/run_all_stata.do
*/

version 17
clear all
set more off
capture log close _all

global PROJECT_ROOT "`c(pwd)'"

capture confirm file "${PROJECT_ROOT}/data/analysis/pe_national.csv"
if _rc {
    di as error "Could not find data/analysis/pe_national.csv."
    di as error "Change directory to the repository root and run this file again."
    exit 601
}

global ANALYSIS_STATA "${PROJECT_ROOT}/data/analysis/_stata"
global GENERATED "${PROJECT_ROOT}/outputs/generated"
global REPRO_OUTPUT "outputs/generated"

capture mkdir "${PROJECT_ROOT}/outputs"
capture mkdir "${GENERATED}"
capture mkdir "${GENERATED}/logs"
capture mkdir "${GENERATED}/tables"
capture mkdir "${GENERATED}/figures"
capture mkdir "${GENERATED}/qa"

log using "${GENERATED}/logs/run_all_stata.log", replace text

di as text _newline "STEP 1: Prepare tracked CSV panels for Stata"
do "${PROJECT_ROOT}/stata/0_prepare_analysis_data.do"

di as text _newline "STEP 2: Baseline and balance tables"
do "${PROJECT_ROOT}/stata/2_descriptive/build_table1_baseline_balance_same_state.do"
do "${PROJECT_ROOT}/stata/2_descriptive/build_table1_baseline_balance_same_state_matched.do"

di as text _newline "STEP 3: Econometric analysis"
do "${PROJECT_ROOT}/stata/3_econometrics/run_paper_strengthening_gold_plus_silver.do"
do "${PROJECT_ROOT}/stata/3_econometrics/run_reit_staffing_econometrics.do"
do "${PROJECT_ROOT}/stata/3_econometrics/run_reit_medicaid_heterogeneity.do"
do "${PROJECT_ROOT}/stata/3_econometrics/run_star_rating_econometrics_gold_plus_silver.do"

di as text _newline "STEP 4: Build plotting data and summary tables"
capture erase "${GENERATED}/tables/econometrics/paper_medicaid_terciles_total_nurse_plot_data_gold_plus_silver.csv"
capture erase "${GENERATED}/tables/econometrics_reit/paper_medicaid_terciles_directcare_reit_plot_data.csv"
shell python3 "${PROJECT_ROOT}/scripts/analysis/build_pe_support_outputs.py"
capture confirm file "${GENERATED}/tables/econometrics/paper_medicaid_terciles_total_nurse_plot_data_gold_plus_silver.csv"
if _rc {
    di as error "PE support-output generation failed."
    exit 601
}
shell python3 "${PROJECT_ROOT}/scripts/analysis/build_reit_support_outputs.py"
capture confirm file "${GENERATED}/tables/econometrics_reit/paper_medicaid_terciles_directcare_reit_plot_data.csv"
if _rc {
    di as error "REIT support-output generation failed."
    exit 601
}

di as text _newline "STEP 5: Figures"
do "${PROJECT_ROOT}/stata/4_figures/build_paper_support_figures_gold_plus_silver.do"
do "${PROJECT_ROOT}/stata/4_figures/build_clean_pe_paper_figures.do"
do "${PROJECT_ROOT}/stata/4_figures/build_medicaid_tercile_figures_gold_plus_silver.do"
do "${PROJECT_ROOT}/stata/4_figures/build_reit_support_figures.do"
do "${PROJECT_ROOT}/stata/4_figures/build_reit_medicaid_tercile_figures.do"

di as text _newline "STEP 6: Render selected tables when LaTeX/Poppler are available"
shell python3 "${PROJECT_ROOT}/scripts/analysis/build_tables.py"
if _rc exit _rc

di as result _newline "Analysis complete: ${GENERATED}"
file open complete_marker using "${GENERATED}/.analysis_complete", write replace
file write complete_marker "ok" _n
file close complete_marker
log close
