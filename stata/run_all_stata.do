/*
================================================================================
run_all_stata.do  —  Master Stata entry point
================================================================================
Detects the project root by locating:
  research/treatment_inputs/pe_facility_verification.csv
Sets global PROJECT_ROOT and runs all Stata do files in order.

Run this file from any working directory:
  do "/path/to/stata/run_all_stata.do"

Prerequisites:
  - Raw data must exist under data/raw/
  - Python pipeline (scripts/run_data_pipeline.py) should be run first to
    populate data/intermediate/ and data/final/
================================================================================
*/

version 17
clear all
set more off

// ---------------------------------------------------------------------------
// 1. Detect project root
// ---------------------------------------------------------------------------
// Walk up from this file's directory until we find the sentinel file.
local _this_dir = subinstr(`"`c(sysdir_personal)'"', "\", "/", .)

// Resolve directory of this do-file via c(script)
local _dofile `"`0'"'
if "`_dofile'" == "" {
    di as error "Cannot detect do-file path. Run via: do /full/path/to/run_all_stata.do"
    exit 1
}

// Use cd-based detection: test candidate dirs upward
local _sentinel "research/treatment_inputs/pe_facility_verification.csv"
local _found 0

// Try the directory containing this do-file and its parents
local _check : pwd
forvalues _lvl = 1/6 {
    local _candidate_sentinel `"`_check'/`_sentinel'"'
    capture confirm file `"`_candidate_sentinel'"'
    if _rc == 0 {
        global PROJECT_ROOT `"`_check'"'
        local _found 1
        continue, break
    }
    // Go one level up
    local _check = substr(`"`_check'"', 1, \
        max(0, length(`"`_check'"') - length(reverse(substr(reverse(`"`_check'"'), 1, \
        index(reverse(`"`_check'"'), "/"))))))
}

if !`_found' {
    // Fallback: use the directory two levels above this do-file
    // (stata/run_all_stata.do → project root is two dirs up: stata/ → project/)
    local _stata_dir = substr(`"`_dofile'"', 1, max(0, ///
        length(`"`_dofile'"') - length("run_all_stata.do") - 1))
    local _stata_dir = subinstr(`"`_stata_dir'"', "\", "/", .)
    // Strip trailing slash
    if substr(`"`_stata_dir'"', -1, 1) == "/" {
        local _stata_dir = substr(`"`_stata_dir'"', 1, length(`"`_stata_dir'"') - 1)
    }
    // Parent of stata/ directory
    local _root_len = length(`"`_stata_dir'"') - ///
        length(substr(`"`_stata_dir'"', index(`"`_stata_dir'"', "/stata"), .))
    // Simple approach: strip /stata suffix
    local _project_root = subinstr(`"`_stata_dir'"', "/stata", "", .)
    global PROJECT_ROOT `"`_project_root'"'
    di as text "Warning: sentinel not found via pwd walk; using inferred root: ${PROJECT_ROOT}"
}

di as text "PROJECT_ROOT = ${PROJECT_ROOT}"

// ---------------------------------------------------------------------------
// 2. Set convenience globals
// ---------------------------------------------------------------------------
global REPRO_INTERMEDIATE "${PROJECT_ROOT}/data/intermediate"
global REPRO_OUTPUT        "${PROJECT_ROOT}/outputs/intermediate"
global INTERMEDIATE        "${PROJECT_ROOT}/data/intermediate"
global OUTPUT              "${PROJECT_ROOT}/outputs"

di as text "REPRO_INTERMEDIATE = ${REPRO_INTERMEDIATE}"
di as text "REPRO_OUTPUT       = ${REPRO_OUTPUT}"

// ---------------------------------------------------------------------------
// 3. Run all do files in order
// ---------------------------------------------------------------------------

// ---- 3.1  Foundation -------------------------------------------------------
di as text _newline "=========================================================="
di as text "STEP 1: Foundation — Medicaid foundation panel"
di as text "=========================================================="
do "${PROJECT_ROOT}/stata/1_foundation/build_medicaid_foundation.do"
di as text "STEP 1 complete."

// ---- 3.2  Descriptive / Balance --------------------------------------------
di as text _newline "=========================================================="
di as text "STEP 2a: Descriptive — Table 1 baseline balance (same-state)"
di as text "=========================================================="
do "${PROJECT_ROOT}/stata/2_descriptive/build_table1_baseline_balance_same_state.do"
di as text "STEP 2a complete."

di as text _newline "=========================================================="
di as text "STEP 2b: Descriptive — Table 1 baseline balance (matched)"
di as text "=========================================================="
do "${PROJECT_ROOT}/stata/2_descriptive/build_table1_baseline_balance_same_state_matched.do"
di as text "STEP 2b complete."

// ---- 3.3  Econometrics -----------------------------------------------------
di as text _newline "=========================================================="
di as text "STEP 3a: Econometrics — PE paper strengthening (gold+silver)"
di as text "=========================================================="
do "${PROJECT_ROOT}/stata/3_econometrics/run_paper_strengthening_gold_plus_silver.do"
di as text "STEP 3a complete."

di as text _newline "=========================================================="
di as text "STEP 3b: Econometrics — REIT staffing econometrics"
di as text "=========================================================="
do "${PROJECT_ROOT}/stata/3_econometrics/run_reit_staffing_econometrics.do"
di as text "STEP 3b complete."

di as text _newline "=========================================================="
di as text "STEP 3c: Econometrics — REIT Medicaid heterogeneity"
di as text "=========================================================="
do "${PROJECT_ROOT}/stata/3_econometrics/run_reit_medicaid_heterogeneity.do"
di as text "STEP 3c complete."

di as text _newline "=========================================================="
di as text "STEP 3d: Econometrics — Star rating econometrics (gold+silver)"
di as text "=========================================================="
do "${PROJECT_ROOT}/stata/3_econometrics/run_star_rating_econometrics_gold_plus_silver.do"
di as text "STEP 3d complete."

// ---- 3.4  Figures ----------------------------------------------------------
di as text _newline "=========================================================="
di as text "STEP 4a: Figures — Paper support figures (gold+silver)"
di as text "=========================================================="
do "${PROJECT_ROOT}/stata/4_figures/build_paper_support_figures_gold_plus_silver.do"
di as text "STEP 4a complete."

di as text _newline "=========================================================="
di as text "STEP 4b: Figures — Clean PE paper figures"
di as text "=========================================================="
do "${PROJECT_ROOT}/stata/4_figures/build_clean_pe_paper_figures.do"
di as text "STEP 4b complete."

di as text _newline "=========================================================="
di as text "STEP 4c: Figures — Medicaid tercile figures (gold+silver)"
di as text "=========================================================="
do "${PROJECT_ROOT}/stata/4_figures/build_medicaid_tercile_figures_gold_plus_silver.do"
di as text "STEP 4c complete."

di as text _newline "=========================================================="
di as text "STEP 4d: Figures — REIT support figures"
di as text "=========================================================="
do "${PROJECT_ROOT}/stata/4_figures/build_reit_support_figures.do"
di as text "STEP 4d complete."

di as text _newline "=========================================================="
di as text "STEP 4e: Figures — REIT Medicaid tercile figures"
di as text "=========================================================="
do "${PROJECT_ROOT}/stata/4_figures/build_reit_medicaid_tercile_figures.do"
di as text "STEP 4e complete."

// ---- 3.5  Output / Tables --------------------------------------------------
di as text _newline "=========================================================="
di as text "STEP 5: Output — Build paper tables PDF"
di as text "=========================================================="
do "${PROJECT_ROOT}/stata/5_output/build_paper_tables_pdf.do"
di as text "STEP 5 complete."

// ---------------------------------------------------------------------------
// 4. Done
// ---------------------------------------------------------------------------
di as text _newline "=========================================================="
di as text "ALL STATA STEPS COMPLETE"
di as text "=========================================================="
