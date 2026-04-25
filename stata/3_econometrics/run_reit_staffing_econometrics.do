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
global OUTPUTS_DIR "${PROJECT_ROOT}/outputs/intermediate"
global TABLES_DIR "${OUTPUTS_DIR}/tables/econometrics_reit"
global FIGURES_DIR "${OUTPUTS_DIR}/figures/econometrics_reit"
global QA_DIR "${OUTPUTS_DIR}/qa/econometrics_reit"

capture mkdir "${PROJECT_ROOT}/outputs"
capture mkdir "${OUTPUTS_DIR}"
capture mkdir "${OUTPUTS_DIR}/tables"
capture mkdir "${OUTPUTS_DIR}/figures"
capture mkdir "${OUTPUTS_DIR}/qa"
capture mkdir "${TABLES_DIR}"
capture mkdir "${FIGURES_DIR}"
capture mkdir "${QA_DIR}"

log using "${QA_DIR}/run_reit_staffing_econometrics.log", replace text

capture which esttab
if _rc {
    capture ssc install estout, replace
}
capture which esttab
if _rc {
    di as error "esttab is required but could not be installed."
    exit 499
}

capture which csdid
if _rc {
    capture ssc install csdid, replace
}
capture which csdid
if _rc {
    di as error "csdid is required but could not be installed."
    exit 499
}

program define _esttab_export_pair
    syntax namelist(min=1), Stem(string) Title(string) [Keep(string) Order(string) MTitles(string)]

    esttab `namelist' using "${TABLES_DIR}/`stem'.tex", replace ///
        label se star(* 0.10 ** 0.05 *** 0.01) ///
        `=cond("`keep'" != "", "keep(`keep')", "")' ///
        `=cond("`order'" != "", "order(`order')", "")' ///
        `=cond("`mtitles'" != "", `"mtitles(`mtitles')"', "")' ///
        title("`title'")

    esttab `namelist' using "${TABLES_DIR}/`stem'.csv", replace ///
        csv ///
        label se star(* 0.10 ** 0.05 *** 0.01) ///
        `=cond("`keep'" != "", "keep(`keep')", "")' ///
        `=cond("`order'" != "", "order(`order')", "")' ///
        `=cond("`mtitles'" != "", `"mtitles(`mtitles')"', "")' ///
        title("`title'")

    preserve
        import delimited using "${TABLES_DIR}/`stem'.csv", clear varnames(1)
        save "${TABLES_DIR}/`stem'.dta", replace
    restore
end

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

    if !fileexists("`panel_path'") {
        di as error "Missing REIT panel: `panel_path'"
        continue
    }

    use "`panel_path'", clear
    keep if sample_main_staffing == 1

    tostring ccn_str, replace
    encode ccn_str, gen(ccn_id)
    xtset ccn_id year

    destring treat_year post_treat did_treat ltcfocus_directcare_hprd ltcfocus_rn_hprd, replace force

    gen int gvar_treat = 0
    replace gvar_treat = treat_year if !missing(treat_year)

    quietly areg ltcfocus_directcare_hprd did_treat i.year, absorb(ccn_id) vce(cluster ccn_id)
    estimates store direct_main_`est_suffix'

    quietly areg ltcfocus_rn_hprd did_treat i.year, absorb(ccn_id) vce(cluster ccn_id)
    estimates store rn_main_`est_suffix'

    quietly csdid ltcfocus_directcare_hprd, ivar(ccn_id) time(year) gvar(gvar_treat) method(dripw)
    estimates store csdid_direct_`est_suffix'
    capture noisily estat event, window(-2 2) estore(cs_evt_direct_`est_suffix')

    quietly csdid ltcfocus_rn_hprd, ivar(ccn_id) time(year) gvar(gvar_treat) method(dripw)
    estimates store csdid_rn_`est_suffix'
    capture noisily estat event, window(-2 2) estore(cs_evt_rn_`est_suffix')
}

_esttab_export_pair ///
    direct_main_nat direct_main_state direct_main_match, ///
    stem(reit_staffing_main_directcare) ///
    title("REIT staffing DID: LTCFocus direct-care HPRD") ///
    keep("did_treat") ///
    mtitles("National" "Same-state" "Matched")

_esttab_export_pair ///
    rn_main_nat rn_main_state rn_main_match, ///
    stem(reit_staffing_main_rn) ///
    title("REIT staffing DID: LTCFocus RN HPRD") ///
    keep("did_treat") ///
    mtitles("National" "Same-state" "Matched")

capture noisily _esttab_export_pair ///
    cs_evt_direct_nat cs_evt_direct_state cs_evt_direct_match, ///
    stem(reit_csdid_event_directcare) ///
    title("REIT CSDID event study: LTCFocus direct-care HPRD") ///
    order("Pre_avg Post_avg Tm2 Tm1 Tp0 Tp1 Tp2") ///
    mtitles("National" "Same-state" "Matched")

capture noisily _esttab_export_pair ///
    cs_evt_rn_nat cs_evt_rn_state cs_evt_rn_match, ///
    stem(reit_csdid_event_rn) ///
    title("REIT CSDID event study: LTCFocus RN HPRD") ///
    order("Pre_avg Post_avg Tm2 Tm1 Tp0 Tp1 Tp2") ///
    mtitles("National" "Same-state" "Matched")

log close
