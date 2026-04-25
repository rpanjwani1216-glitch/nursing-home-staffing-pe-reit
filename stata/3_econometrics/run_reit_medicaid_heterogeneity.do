version 17
clear all
set more off
capture log close _all

local cwd "`c(pwd)'"
if fileexists("`cwd'/research/treatment_inputs/reit_facility_verification.csv") {
    global PROJECT_ROOT "`cwd'"
}
else if fileexists("`cwd'/../research/treatment_inputs/reit_facility_verification.csv") {
    global PROJECT_ROOT "`cwd'/.."
}
else if fileexists("`cwd'/../../research/treatment_inputs/reit_facility_verification.csv") {
    global PROJECT_ROOT "`cwd'/../.."
}
else {
    di as error "Could not locate the project root."
    exit 601
}

global ANALYSIS_DIR "${PROJECT_ROOT}/data/final/panels"
global OUTPUTS_DIR "${PROJECT_ROOT}/outputs"
global TABLES_DIR "${OUTPUTS_DIR}/tables/econometrics_reit"
global QA_DIR "${OUTPUTS_DIR}/intermediate/qa/econometrics_reit"

capture mkdir "${OUTPUTS_DIR}"
capture mkdir "${OUTPUTS_DIR}/intermediate"
capture mkdir "${OUTPUTS_DIR}/intermediate/qa"
capture mkdir "${OUTPUTS_DIR}/tables"
capture mkdir "${QA_DIR}"
capture mkdir "${TABLES_DIR}"

log using "${QA_DIR}/run_reit_medicaid_heterogeneity.log", replace text

capture which esttab
if _rc {
    capture ssc install estout, replace
}
capture which esttab
if _rc {
    di as error "esttab is required but could not be installed."
    exit 499
}

program define _esttab_export
    syntax namelist(min=1), Stem(string) Title(string) [MTitles(string)]

    esttab `namelist' using "${TABLES_DIR}/`stem'.tex", replace ///
        label se star(* 0.10 ** 0.05 *** 0.01) ///
        `=cond("`mtitles'" != "", `"mtitles(`mtitles')"', "")' ///
        title("`title'")

    esttab `namelist' using "${TABLES_DIR}/`stem'.csv", replace ///
        csv label se star(* 0.10 ** 0.05 *** 0.01) ///
        `=cond("`mtitles'" != "", `"mtitles(`mtitles')"', "")' ///
        title("`title'")

    preserve
        import delimited using "${TABLES_DIR}/`stem'.csv", clear varnames(1)
        save "${TABLES_DIR}/`stem'.dta", replace
    restore
end

tempname tercsupp
postfile `tercsupp' str12 panel byte tercile int treated_facilities int control_facilities using "${TABLES_DIR}/reit_medicaid_tercile_support.dta", replace

local panels "national same_state matched"
estimates clear

foreach spec in `panels' {
    local panel_path ""
    local panel_label ""
    local est_suffix ""

    if "`spec'" == "national" {
        local panel_path "${ANALYSIS_DIR}/reit_staffing_panel_extended.dta"
        local panel_label "National"
        local est_suffix "nat"
    }
    else if "`spec'" == "same_state" {
        local panel_path "${ANALYSIS_DIR}/reit_staffing_panel_extended_same_state.dta"
        local panel_label "Same-state"
        local est_suffix "state"
    }
    else if "`spec'" == "matched" {
        local panel_path "${ANALYSIS_DIR}/reit_staffing_panel_extended_same_state_matched.dta"
        local panel_label "Matched"
        local est_suffix "match"
    }

    use "`panel_path'", clear
    keep if sample_main_staffing == 1
    keep if !missing(baseline_medicaid_share)

    tostring ccn_str, replace
    encode ccn_str, gen(ccn_id)
    xtset ccn_id year

    destring treat_year post_treat did_treat baseline_medicaid_share ltcfocus_directcare_hprd ltcfocus_rn_hprd, replace force

    preserve
        keep if sample_role == "treated" & !missing(baseline_medicaid_share)
        keep ccn_id ccn_str baseline_medicaid_share
        duplicates drop
        quietly summarize baseline_medicaid_share, detail
        local medicaid_p50 = r(p50)
        quietly _pctile baseline_medicaid_share, p(33.333333 66.666667)
        local medicaid_p33 = r(r1)
        local medicaid_p67 = r(r2)
    restore

    gen byte high_medicaid = baseline_medicaid_share >= `medicaid_p50' if !missing(baseline_medicaid_share)
    gen double baseline_medicaid_centered = baseline_medicaid_share - `medicaid_p50'
    gen byte medicaid_tercile = .
    replace medicaid_tercile = 1 if !missing(baseline_medicaid_share) & baseline_medicaid_share < `medicaid_p33'
    replace medicaid_tercile = 2 if !missing(baseline_medicaid_share) & baseline_medicaid_share >= `medicaid_p33' & baseline_medicaid_share < `medicaid_p67'
    replace medicaid_tercile = 3 if !missing(baseline_medicaid_share) & baseline_medicaid_share >= `medicaid_p67'

    preserve
        keep ccn_id ccn_str sample_role medicaid_tercile
        duplicates drop
        gen byte treated = sample_role == "treated"
        collapse (count) facility_count=ccn_id (sum) treated, by(medicaid_tercile)
        forvalues t = 1/3 {
            quietly summarize treated if medicaid_tercile == `t'
            local treated_fac = r(mean)
            quietly summarize facility_count if medicaid_tercile == `t'
            local total_fac = r(mean)
            local control_fac = `total_fac' - `treated_fac'
            post `tercsupp' ("`panel_label'") (`t') (`treated_fac') (`control_fac')
        }
    restore

    quietly areg ltcfocus_directcare_hprd c.did_treat##c.baseline_medicaid_centered i.year, absorb(ccn_id) vce(cluster ccn_id)
    estimates store direct_het_`est_suffix'

    quietly areg ltcfocus_rn_hprd c.did_treat##c.baseline_medicaid_centered i.year, absorb(ccn_id) vce(cluster ccn_id)
    estimates store rn_het_`est_suffix'

    quietly areg ltcfocus_directcare_hprd did_treat i.year if high_medicaid == 1, absorb(ccn_id) vce(cluster ccn_id)
    estimates store direct_high_`est_suffix'
    quietly areg ltcfocus_directcare_hprd did_treat i.year if high_medicaid == 0, absorb(ccn_id) vce(cluster ccn_id)
    estimates store direct_low_`est_suffix'

    quietly areg ltcfocus_rn_hprd did_treat i.year if high_medicaid == 1, absorb(ccn_id) vce(cluster ccn_id)
    estimates store rn_high_`est_suffix'
    quietly areg ltcfocus_rn_hprd did_treat i.year if high_medicaid == 0, absorb(ccn_id) vce(cluster ccn_id)
    estimates store rn_low_`est_suffix'

    quietly areg ltcfocus_directcare_hprd did_treat i.year if medicaid_tercile == 1, absorb(ccn_id) vce(cluster ccn_id)
    estimates store direct_t1_`est_suffix'
    quietly areg ltcfocus_directcare_hprd did_treat i.year if medicaid_tercile == 2, absorb(ccn_id) vce(cluster ccn_id)
    estimates store direct_t2_`est_suffix'
    quietly areg ltcfocus_directcare_hprd did_treat i.year if medicaid_tercile == 3, absorb(ccn_id) vce(cluster ccn_id)
    estimates store direct_t3_`est_suffix'

    quietly areg ltcfocus_rn_hprd did_treat i.year if medicaid_tercile == 1, absorb(ccn_id) vce(cluster ccn_id)
    estimates store rn_t1_`est_suffix'
    quietly areg ltcfocus_rn_hprd did_treat i.year if medicaid_tercile == 2, absorb(ccn_id) vce(cluster ccn_id)
    estimates store rn_t2_`est_suffix'
    quietly areg ltcfocus_rn_hprd did_treat i.year if medicaid_tercile == 3, absorb(ccn_id) vce(cluster ccn_id)
    estimates store rn_t3_`est_suffix'
}

postclose `tercsupp'

_esttab_export ///
    direct_het_nat direct_het_state direct_het_match, ///
    stem(reit_staffing_heterogeneity_directcare) ///
    title("REIT Medicaid interaction: direct-care hours per resident day") ///
    mtitles("National" "Same-state" "Matched")

_esttab_export ///
    rn_het_nat rn_het_state rn_het_match, ///
    stem(reit_staffing_heterogeneity_rn) ///
    title("REIT Medicaid interaction: RN hours per resident day") ///
    mtitles("National" "Same-state" "Matched")

_esttab_export ///
    direct_low_nat direct_high_nat direct_low_state direct_high_state direct_low_match direct_high_match, ///
    stem(reit_staffing_high_low_directcare) ///
    title("REIT high/low Medicaid split: direct-care hours per resident day") ///
    mtitles("Nat. low" "Nat. high" "State low" "State high" "Match low" "Match high")

_esttab_export ///
    rn_low_nat rn_high_nat rn_low_state rn_high_state rn_low_match rn_high_match, ///
    stem(reit_staffing_high_low_rn) ///
    title("REIT high/low Medicaid split: RN hours per resident day") ///
    mtitles("Nat. low" "Nat. high" "State low" "State high" "Match low" "Match high")

_esttab_export ///
    direct_t1_nat direct_t2_nat direct_t3_nat direct_t1_state direct_t2_state direct_t3_state direct_t1_match direct_t2_match direct_t3_match, ///
    stem(reit_staffing_medicaid_terciles_directcare) ///
    title("REIT Medicaid terciles: direct-care hours per resident day") ///
    mtitles("Nat. low" "Nat. mid" "Nat. high" "State low" "State mid" "State high" "Match low" "Match mid" "Match high")

_esttab_export ///
    rn_t1_nat rn_t2_nat rn_t3_nat rn_t1_state rn_t2_state rn_t3_state rn_t1_match rn_t2_match rn_t3_match, ///
    stem(reit_staffing_medicaid_terciles_rn) ///
    title("REIT Medicaid terciles: RN hours per resident day") ///
    mtitles("Nat. low" "Nat. mid" "Nat. high" "State low" "State mid" "State high" "Match low" "Match mid" "Match high")

use "${TABLES_DIR}/reit_medicaid_tercile_support.dta", clear
label define tercile_lbl 1 "Low" 2 "Middle" 3 "High"
label values tercile tercile_lbl
export delimited using "${TABLES_DIR}/reit_medicaid_tercile_support.csv", replace

log close
