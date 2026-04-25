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
if "`repro_out'" == "" local repro_out "outputs/intermediate"
global OUTPUTS_DIR "${PROJECT_ROOT}/`repro_out'"

global ANALYSIS_DIR "${INTERMEDIATE}/analysis/panels"
global TABLES_DIR "${OUTPUTS_DIR}/tables/econometrics"
global QA_DIR "${OUTPUTS_DIR}/qa/econometrics"

capture mkdir "${OUTPUTS_DIR}"
capture mkdir "${OUTPUTS_DIR}/tables"
capture mkdir "${TABLES_DIR}"
capture mkdir "${QA_DIR}"

log using "${QA_DIR}/run_paper_strengthening.log", replace text

capture which csdid
if _rc {
    di as error "csdid is required but not installed."
    exit 499
}

capture which esttab
if _rc {
    di as error "esttab is required but not installed."
    exit 499
}

program define _esttab_export_pair
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

tempname coefpost loopost tercsupp holdcosupp
postfile `coefpost' str12 panel str16 outcome double coef se lb ub long N using "${TABLES_DIR}/paper_main_coef_plot_data.dta", replace
postfile `loopost' str12 panel str16 outcome str12 omitted_deal int omitted_facilities double coef se lb ub int treated_facilities_left using "${TABLES_DIR}/leave_one_deal_out_raw.dta", replace
postfile `tercsupp' str12 panel byte tercile int treated_facilities int control_facilities using "${TABLES_DIR}/medicaid_tercile_support.dta", replace
postfile `holdcosupp' str12 panel byte holdco_group int treated_facilities int control_facilities using "${TABLES_DIR}/holdco_group_support.dta", replace

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

    use "`panel_path'", clear
    keep if sample_main_staffing == 1

    tostring ccn_str, replace
    encode ccn_str, gen(ccn_id)
    xtset ccn_id year

    gen byte did_treat = 0
    replace did_treat = post_treat if !missing(post_treat)
    gen int gvar_treat = 0
    replace gvar_treat = treat_year if !missing(treat_year)

    destring any_holding_company_owner, replace force
    gen byte holdco_transition = (any_holding_company_owner == 1) & (did_treat == 1)

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

    preserve
        keep ccn_id ccn_str sample_role holdco_transition
        collapse (max) ever_holdco_treated=holdco_transition, by(ccn_id ccn_str sample_role)
        tempfile holdcogroups
        save `holdcogroups'

        quietly count if sample_role == "treated" & ever_holdco_treated == 1
        local holdco_treated = r(N)
        quietly count if sample_role == "treated" & ever_holdco_treated == 0
        local nonholdco_treated = r(N)
        quietly count if sample_role == "control"
        local holdco_controls = r(N)

        post `holdcosupp' ("`panel_label'") (1) (`holdco_treated') (`holdco_controls')
        post `holdcosupp' ("`panel_label'") (0) (`nonholdco_treated') (`holdco_controls')
    restore

    merge m:1 ccn_id using `holdcogroups', nogen keep(master match)
    replace ever_holdco_treated = 0 if missing(ever_holdco_treated) & sample_role == "control"

    quietly areg pbj_mean_nurse_hprd did_treat i.year, absorb(ccn_id) vce(cluster ccn_id)
    local b = _b[did_treat]
    local s = _se[did_treat]
    local lb = `b' - 1.96 * `s'
    local ub = `b' + 1.96 * `s'
    post `coefpost' ("`panel_label'") ("Total nurse HPRD") (`b') (`s') (`lb') (`ub') (e(N))

    quietly areg pbj_mean_rn_hprd did_treat i.year, absorb(ccn_id) vce(cluster ccn_id)
    local b = _b[did_treat]
    local s = _se[did_treat]
    local lb = `b' - 1.96 * `s'
    local ub = `b' + 1.96 * `s'
    post `coefpost' ("`panel_label'") ("RN HPRD") (`b') (`s') (`lb') (`ub') (e(N))

    levelsof deal_id if sample_role == "treated" & !missing(deal_id), local(deal_list)
    foreach deal in `deal_list' {
        preserve
            quietly egen tag_deal = tag(ccn_id) if sample_role == "treated" & deal_id == "`deal'"
            quietly count if tag_deal == 1
            local omitted_fac = r(N)

            drop if sample_role == "treated" & deal_id == "`deal'"

            quietly egen tag_left = tag(ccn_id) if sample_role == "treated"
            quietly count if tag_left == 1
            local treated_left = r(N)

            quietly areg pbj_mean_nurse_hprd did_treat i.year, absorb(ccn_id) vce(cluster ccn_id)
            local b = _b[did_treat]
            local s = _se[did_treat]
            local lb = `b' - 1.96 * `s'
            local ub = `b' + 1.96 * `s'
            post `loopost' ("`panel_label'") ("Total nurse HPRD") ("`deal'") (`omitted_fac') (`b') (`s') (`lb') (`ub') (`treated_left')

            quietly areg pbj_mean_rn_hprd did_treat i.year, absorb(ccn_id) vce(cluster ccn_id)
            local b = _b[did_treat]
            local s = _se[did_treat]
            local lb = `b' - 1.96 * `s'
            local ub = `b' + 1.96 * `s'
            post `loopost' ("`panel_label'") ("RN HPRD") ("`deal'") (`omitted_fac') (`b') (`s') (`lb') (`ub') (`treated_left')
        restore
    }

    quietly areg pbj_mean_nurse_hprd did_treat i.year if medicaid_tercile == 1, absorb(ccn_id) vce(cluster ccn_id)
    estimates store terc_nurse_low_`est_suffix'
    quietly areg pbj_mean_nurse_hprd did_treat i.year if medicaid_tercile == 2, absorb(ccn_id) vce(cluster ccn_id)
    estimates store terc_nurse_mid_`est_suffix'
    quietly areg pbj_mean_nurse_hprd did_treat i.year if medicaid_tercile == 3, absorb(ccn_id) vce(cluster ccn_id)
    estimates store terc_nurse_high_`est_suffix'

    quietly areg pbj_mean_rn_hprd did_treat i.year if medicaid_tercile == 1, absorb(ccn_id) vce(cluster ccn_id)
    estimates store terc_rn_low_`est_suffix'
    quietly areg pbj_mean_rn_hprd did_treat i.year if medicaid_tercile == 2, absorb(ccn_id) vce(cluster ccn_id)
    estimates store terc_rn_mid_`est_suffix'
    quietly areg pbj_mean_rn_hprd did_treat i.year if medicaid_tercile == 3, absorb(ccn_id) vce(cluster ccn_id)
    estimates store terc_rn_high_`est_suffix'

    foreach grp in holdco noholdco {
        local grp_flag = cond("`grp'" == "holdco", 1, 0)
        local grp_short = cond("`grp'" == "holdco", "yes", "no")
        quietly csdid pbj_mean_nurse_hprd baseline_medicaid_share if sample_role == "control" | ever_holdco_treated == `grp_flag', ///
            ivar(ccn_id) ///
            time(year) ///
            gvar(gvar_treat) ///
            method(dripw)

        estimates store csdid_hc_`grp_short'_`est_suffix'
        capture noisily estat event, window(-2 2) estore(cs_evt_hc_`grp_short'_`est_suffix')
    }
}

postclose `coefpost'
postclose `loopost'
postclose `tercsupp'
postclose `holdcosupp'

use "${TABLES_DIR}/paper_main_coef_plot_data.dta", clear
export delimited using "${TABLES_DIR}/paper_main_coef_plot_data.csv", replace

use "${TABLES_DIR}/leave_one_deal_out_raw.dta", clear
sort outcome panel omitted_deal
export delimited using "${TABLES_DIR}/leave_one_deal_out_raw.csv", replace

use "${TABLES_DIR}/medicaid_tercile_support.dta", clear
sort panel tercile
export delimited using "${TABLES_DIR}/medicaid_tercile_support.csv", replace

use "${TABLES_DIR}/holdco_group_support.dta", clear
sort panel holdco_group
export delimited using "${TABLES_DIR}/holdco_group_support.csv", replace

_esttab_export_pair ///
    terc_nurse_low_nat terc_nurse_mid_nat terc_nurse_high_nat ///
    terc_nurse_low_state terc_nurse_mid_state terc_nurse_high_state ///
    terc_nurse_low_match terc_nurse_mid_match terc_nurse_high_match, ///
    stem(staffing_medicaid_terciles_total_nurse) ///
    title("Medicaid terciles: total nurse hours per resident day") ///
    mtitles(`" "Nat. low" "Nat. mid" "Nat. high" "State low" "State mid" "State high" "Match low" "Match mid" "Match high" "')

_esttab_export_pair ///
    terc_rn_low_nat terc_rn_mid_nat terc_rn_high_nat ///
    terc_rn_low_state terc_rn_mid_state terc_rn_high_state ///
    terc_rn_low_match terc_rn_mid_match terc_rn_high_match, ///
    stem(staffing_medicaid_terciles_rn) ///
    title("Medicaid terciles: RN hours per resident day") ///
    mtitles(`" "Nat. low" "Nat. mid" "Nat. high" "State low" "State mid" "State high" "Match low" "Match mid" "Match high" "')

_esttab_export_pair ///
    cs_evt_hc_yes_nat cs_evt_hc_no_nat ///
    cs_evt_hc_yes_state cs_evt_hc_no_state ///
    cs_evt_hc_yes_match cs_evt_hc_no_match, ///
    stem(csdid_event_total_nurse_holdco_groups) ///
    title("CSDID event study: total nurse hours per resident day by holdco exposure") ///
    mtitles(`" "Nat. holdco" "Nat. no holdco" "State holdco" "State no holdco" "Match holdco" "Match no holdco" "')

log close
