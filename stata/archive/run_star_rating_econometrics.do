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

log using "${QA_DIR}/run_star_rating_econometrics.log", replace text

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

tempname coefpost
postfile `coefpost' str12 panel str24 outcome double coef se lb ub long N using "${TABLES_DIR}/paper_star_main_coef_plot_data.dta", replace

local panels "gold_v2 gold_v2_same_state gold_v2_same_state_matched"
estimates clear

foreach spec in `panels' {
    local panel_path ""
    local panel_label ""
    local est_suffix ""

    if "`spec'" == "gold_v2" {
        local panel_path "${ANALYSIS_DIR}/regression_analysis_panel_gold_v2.dta"
        local panel_label "National"
        local est_suffix "nat"
    }
    else if "`spec'" == "gold_v2_same_state" {
        local panel_path "${ANALYSIS_DIR}/regression_analysis_panel_gold_v2_same_state.dta"
        local panel_label "Same-state"
        local est_suffix "state"
    }
    else if "`spec'" == "gold_v2_same_state_matched" {
        local panel_path "${ANALYSIS_DIR}/regression_analysis_panel_gold_v2_same_state_matched.dta"
        local panel_label "Matched"
        local est_suffix "match"
    }

    if !fileexists("`panel_path'") {
        di as error "Missing analysis panel: `panel_path'"
        continue
    }

    di as text "Running star-rating econometrics on `panel_label'"
    use "`panel_path'", clear
    keep if sample_star_ratings == 1

    tostring ccn_str, replace
    encode ccn_str, gen(ccn_id)
    xtset ccn_id year

    gen byte did_treat = 0
    replace did_treat = post_treat if !missing(post_treat)
    gen int gvar_treat = 0
    replace gvar_treat = treat_year if !missing(treat_year)

    * Health rating
    quietly areg provider_health_rating did_treat i.year if !missing(provider_health_rating), absorb(ccn_id) vce(cluster ccn_id)
    estimates store star_health_main_`est_suffix'
    local b = _b[did_treat]
    local s = _se[did_treat]
    local lb = `b' - 1.96 * `s'
    local ub = `b' + 1.96 * `s'
    post `coefpost' ("`panel_label'") ("Health rating") (`b') (`s') (`lb') (`ub') (e(N))

    quietly csdid provider_health_rating baseline_medicaid_share if !missing(provider_health_rating), ///
        ivar(ccn_id) time(year) gvar(gvar_treat) method(dripw)
    estimates store csdid_health_`est_suffix'
    capture noisily estat event, window(-2 2) estore(cs_evt_health_`est_suffix')

    * Overall rating
    quietly areg provider_overall_rating did_treat i.year if !missing(provider_overall_rating), absorb(ccn_id) vce(cluster ccn_id)
    estimates store star_overall_main_`est_suffix'
    local b = _b[did_treat]
    local s = _se[did_treat]
    local lb = `b' - 1.96 * `s'
    local ub = `b' + 1.96 * `s'
    post `coefpost' ("`panel_label'") ("Overall rating") (`b') (`s') (`lb') (`ub') (e(N))

    quietly csdid provider_overall_rating baseline_medicaid_share if !missing(provider_overall_rating), ///
        ivar(ccn_id) time(year) gvar(gvar_treat) method(dripw)
    estimates store csdid_overall_`est_suffix'
    capture noisily estat event, window(-2 2) estore(cs_evt_overall_`est_suffix')

    * Staffing rating
    quietly areg provider_staffing_rating did_treat i.year if !missing(provider_staffing_rating), absorb(ccn_id) vce(cluster ccn_id)
    estimates store star_staffing_main_`est_suffix'
    local b = _b[did_treat]
    local s = _se[did_treat]
    local lb = `b' - 1.96 * `s'
    local ub = `b' + 1.96 * `s'
    post `coefpost' ("`panel_label'") ("Staffing rating") (`b') (`s') (`lb') (`ub') (e(N))

    quietly csdid provider_staffing_rating baseline_medicaid_share if !missing(provider_staffing_rating), ///
        ivar(ccn_id) time(year) gvar(gvar_treat) method(dripw)
    estimates store csdid_staffing_`est_suffix'
    capture noisily estat event, window(-2 2) estore(cs_evt_staffing_`est_suffix')

    * Quality-measure rating
    quietly areg provider_qm_rating did_treat i.year if !missing(provider_qm_rating), absorb(ccn_id) vce(cluster ccn_id)
    estimates store star_qm_main_`est_suffix'
    local b = _b[did_treat]
    local s = _se[did_treat]
    local lb = `b' - 1.96 * `s'
    local ub = `b' + 1.96 * `s'
    post `coefpost' ("`panel_label'") ("QM rating") (`b') (`s') (`lb') (`ub') (e(N))

    quietly csdid provider_qm_rating baseline_medicaid_share if !missing(provider_qm_rating), ///
        ivar(ccn_id) time(year) gvar(gvar_treat) method(dripw)
    estimates store csdid_qm_`est_suffix'
    capture noisily estat event, window(-2 2) estore(cs_evt_qm_`est_suffix')
}

postclose `coefpost'

use "${TABLES_DIR}/paper_star_main_coef_plot_data.dta", clear
export delimited using "${TABLES_DIR}/paper_star_main_coef_plot_data.csv", replace

_esttab_export_pair ///
    star_health_main_nat star_health_main_state star_health_main_match, ///
    stem(star_main_health_rating) ///
    title("Main DID: health rating") ///
    keep("did_treat") ///
    mtitles("National" "Same-state" "Matched")

_esttab_export_pair ///
    star_overall_main_nat star_overall_main_state star_overall_main_match, ///
    stem(star_main_overall_rating) ///
    title("Main DID: overall rating") ///
    keep("did_treat") ///
    mtitles("National" "Same-state" "Matched")

_esttab_export_pair ///
    star_staffing_main_nat star_staffing_main_state star_staffing_main_match, ///
    stem(star_main_staffing_rating) ///
    title("Main DID: staffing rating") ///
    keep("did_treat") ///
    mtitles("National" "Same-state" "Matched")

_esttab_export_pair ///
    star_qm_main_nat star_qm_main_state star_qm_main_match, ///
    stem(star_main_qm_rating) ///
    title("Main DID: quality-measure rating") ///
    keep("did_treat") ///
    mtitles("National" "Same-state" "Matched")

_esttab_export_pair ///
    cs_evt_health_nat cs_evt_health_state cs_evt_health_match, ///
    stem(csdid_event_health_rating) ///
    title("CSDID event study: health rating") ///
    mtitles("National" "Same-state" "Matched")

_esttab_export_pair ///
    cs_evt_overall_nat cs_evt_overall_state cs_evt_overall_match, ///
    stem(csdid_event_overall_rating) ///
    title("CSDID event study: overall rating") ///
    mtitles("National" "Same-state" "Matched")

_esttab_export_pair ///
    cs_evt_staffing_nat cs_evt_staffing_state cs_evt_staffing_match, ///
    stem(csdid_event_staffing_rating) ///
    title("CSDID event study: staffing rating") ///
    mtitles("National" "Same-state" "Matched")

_esttab_export_pair ///
    cs_evt_qm_nat cs_evt_qm_state cs_evt_qm_match, ///
    stem(csdid_event_qm_rating) ///
    title("CSDID event study: quality-measure rating") ///
    mtitles("National" "Same-state" "Matched")

log close
