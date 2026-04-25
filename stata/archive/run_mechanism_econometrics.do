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
    di as error "Could not locate the project root."
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
global QA_DIR "${OUTPUTS_DIR}/qa/econometrics"

capture mkdir "${OUTPUTS_DIR}"
capture mkdir "${OUTPUTS_DIR}/tables"
capture mkdir "${TABLES_DIR}"
capture mkdir "${QA_DIR}"

log using "${QA_DIR}/run_mechanism_econometrics.log", replace text

capture which esttab
if _rc {
    di as error "esttab is required but not installed."
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
        csv label se star(* 0.10 ** 0.05 *** 0.01) ///
        `=cond("`keep'" != "", "keep(`keep')", "")' ///
        `=cond("`order'" != "", "order(`order')", "")' ///
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
        local short_label "National"
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

    if !fileexists("`panel_path'") {
        di as error "Missing analysis panel: `panel_path'"
        continue
    }

    use "`panel_path'", clear
    keep if sample_main_staffing == 1

    tostring ccn_str, replace
    encode ccn_str, gen(ccn_id)
    xtset ccn_id year

    destring high_medicare any_reit_owner any_holding_company_owner, replace force

    gen byte did_treat = 0
    replace did_treat = post_treat if !missing(post_treat)

    preserve
        keep if sample_role == "treated" & !missing(baseline_medicaid_share)
        keep ccn_id baseline_medicaid_share
        duplicates drop
        quietly summarize baseline_medicaid_share, detail
        local medicaid_p50 = r(p50)
    restore

    gen byte high_medicaid = baseline_medicaid_share >= `medicaid_p50' if !missing(baseline_medicaid_share)
    gen byte holdco_transition = (any_holding_company_owner == 1) & (did_treat == 1)
    gen byte reit_transition = (any_reit_owner == 1) & (did_treat == 1)

    quietly areg pbj_mean_nurse_hprd c.did_treat##i.high_medicare i.year, absorb(ccn_id) vce(cluster ccn_id)
    estimates store slack_`est_suffix'

    capture noisily quietly areg pbj_mean_nurse_hprd did_treat c.holdco_transition##i.high_medicaid i.year, absorb(ccn_id) vce(cluster ccn_id)
    if !_rc {
        estimates store holdco_`est_suffix'
    }

    quietly count if reit_transition == 1 & sample_role == "treated"
    local reit_treated_rows = r(N)
    if `reit_treated_rows' > 1 {
        quietly areg pbj_mean_nurse_hprd did_treat c.reit_transition##i.high_medicaid i.year, absorb(ccn_id) vce(cluster ccn_id)
        estimates store reit_`est_suffix'
    }
}

_esttab_export_pair ///
    slack_nat slack_state slack_match, ///
    stem(mechanism_slack_interaction) ///
    title("Mechanism: Medicare Slack Interaction") ///
    keep("did_treat 1.high_medicare#c.did_treat") ///
    order("did_treat 1.high_medicare#c.did_treat") ///
    mtitles("National" "Same-state" "Matched")

_esttab_export_pair ///
    holdco_nat holdco_state holdco_match, ///
    stem(mechanism_holdco_interaction) ///
    title("Mechanism: Holding Company x Medicaid Interaction") ///
    keep("holdco_transition 1.high_medicaid#c.holdco_transition") ///
    order("holdco_transition 1.high_medicaid#c.holdco_transition") ///
    mtitles("National" "Same-state" "Matched")

log close
