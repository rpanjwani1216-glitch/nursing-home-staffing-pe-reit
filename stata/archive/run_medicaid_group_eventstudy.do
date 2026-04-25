version 17
clear all
set more off
capture log close _all

local cwd "`c(pwd)'"
if fileexists("`cwd'/research/treatment_inputs/pe_facility_verification.csv") {
    global PROJECT_ROOT "`cwd'"
}
else if fileexists("`cwd'/../research/treatment_inputs/pe_facility_verification.csv") {
    global PROJECT_ROOT "`cwd'/.."
}
else if fileexists("`cwd'/../../research/treatment_inputs/pe_facility_verification.csv") {
    global PROJECT_ROOT "`cwd'/../.."
}
else {
    di as error "Could not locate the project root. Run this script from the project root or a stata subdirectory."
    exit 601
}

local repro_int : env REPRO_INTERMEDIATE
if "`repro_int'" == "" local repro_int "intermediate"
global INTERMEDIATE "${PROJECT_ROOT}/data/`repro_int'"

local repro_out : env REPRO_OUTPUT
if "`repro_out'" == "" local repro_out "outputs"
global OUTPUTS_DIR "${PROJECT_ROOT}/`repro_out'"

global ANALYSIS_DIR "${INTERMEDIATE}/analysis/panels"
global TABLES_DIR "${OUTPUTS_DIR}/tables/econometrics"
global FIGURES_DIR "${OUTPUTS_DIR}/figures/econometrics"
global QA_DIR "${OUTPUTS_DIR}/qa/econometrics"

capture mkdir "${OUTPUTS_DIR}"
capture mkdir "${OUTPUTS_DIR}/tables"
capture mkdir "${OUTPUTS_DIR}/figures"
capture mkdir "${TABLES_DIR}"
capture mkdir "${FIGURES_DIR}"
capture mkdir "${QA_DIR}"

log using "${QA_DIR}/run_medicaid_group_eventstudy.log", replace text

capture which esttab
if _rc {
    di as error "esttab is required but not installed."
    exit 499
}

capture which csdid
if _rc {
    di as error "csdid is required but not installed."
    exit 499
}

program define _esttab_export_pair
    syntax namelist(min=1), Stem(string) Title(string) [MTitles(string)]

    esttab `namelist' using "${TABLES_DIR}/`stem'.tex", replace ///
        label se star(* 0.10 ** 0.05 *** 0.01) ///
        `=cond("`mtitles'" != "", `"mtitles(`mtitles')"', "")' ///
        title("`title'")

    esttab `namelist' using "${TABLES_DIR}/`stem'.csv", replace ///
        csv ///
        label se star(* 0.10 ** 0.05 *** 0.01) ///
        `=cond("`mtitles'" != "", `"mtitles(`mtitles')"', "")' ///
        title("`title'")

    preserve
        import delimited using "${TABLES_DIR}/`stem'.csv", clear varnames(1)
        save "${TABLES_DIR}/`stem'.dta", replace
    restore
end

local panels "gold_v2 gold_v2_same_state gold_v2_same_state_matched"
estimates clear

foreach spec in `panels' {
    local panel_path ""
    local short_label ""
    local est_suffix ""

    if "`spec'" == "gold_v2" {
        local panel_path "${ANALYSIS_DIR}/regression_analysis_panel_gold_v2.dta"
        local short_label "National v2"
        local est_suffix "nat"
    }
    else if "`spec'" == "gold_v2_same_state" {
        local panel_path "${ANALYSIS_DIR}/regression_analysis_panel_gold_v2_same_state.dta"
        local short_label "Same-state"
        local est_suffix "state"
    }
    else if "`spec'" == "gold_v2_same_state_matched" {
        local panel_path "${ANALYSIS_DIR}/regression_analysis_panel_gold_v2_same_state_matched.dta"
        local short_label "Matched"
        local est_suffix "match"
    }

    di as text "Running Medicaid-group event study on `short_label'"
    use "`panel_path'", clear
    keep if sample_main_staffing == 1

    tostring ccn_str, replace
    encode ccn_str, gen(ccn_id)
    xtset ccn_id year

    gen int gvar_treat = 0
    replace gvar_treat = treat_year if !missing(treat_year)

    preserve
        keep if sample_role == "treated" & !missing(baseline_medicaid_share)
        keep ccn_id baseline_medicaid_share
        duplicates drop
        quietly summarize baseline_medicaid_share, detail
        local medicaid_p50 = r(p50)
    restore

    gen byte high_medicaid = baseline_medicaid_share >= `medicaid_p50' if !missing(baseline_medicaid_share)

    foreach grp in high low {
        local grp_flag = cond("`grp'" == "high", 1, 0)
        local grp_label = cond("`grp'" == "high", "High Medicaid", "Low Medicaid")
        di as text "  Group: `grp_label'"

        quietly csdid pbj_mean_nurse_hprd baseline_medicaid_share if high_medicaid == `grp_flag', ///
            ivar(ccn_id) ///
            time(year) ///
            gvar(gvar_treat) ///
            method(dripw)

        estimates store csdid_nurse_`grp'_`est_suffix'
        capture noisily estat event, window(-2 2) estore(cs_evt_nurse_`grp'_`est_suffix')
        capture noisily estat pretrend, window(-2 -1)

    }
}

_esttab_export_pair ///
    cs_evt_nurse_high_nat ///
    cs_evt_nurse_low_nat ///
    cs_evt_nurse_high_state ///
    cs_evt_nurse_low_state ///
    cs_evt_nurse_high_match ///
    cs_evt_nurse_low_match, ///
    stem(csdid_event_total_nurse_high_low) ///
    title("CSDID event study: total nurse hours per resident day by Medicaid group") ///
    mtitles(`" "Nat. high" "Nat. low" "State high" "State low" "Match high" "Match low" "')

log close
