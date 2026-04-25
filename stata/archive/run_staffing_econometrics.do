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
if "`repro_out'" == "" local repro_out "outputs/intermediate"
global OUTPUTS_DIR "${PROJECT_ROOT}/`repro_out'"

global ANALYSIS_DIR "${INTERMEDIATE}/analysis/panels"
global TABLES_DIR "${OUTPUTS_DIR}/tables/econometrics"
global FIGURES_DIR "${OUTPUTS_DIR}/figures/econometrics"
global QA_DIR "${OUTPUTS_DIR}/qa/econometrics"

// Standard output directories
capture mkdir "${OUTPUTS_DIR}"
capture mkdir "${OUTPUTS_DIR}/tables"
capture mkdir "${OUTPUTS_DIR}/figures"
capture mkdir "${TABLES_DIR}"
capture mkdir "${FIGURES_DIR}"
capture mkdir "${QA_DIR}"

log using "${QA_DIR}/run_staffing_econometrics.log", replace text

capture which esttab
if _rc {
    di as error "esttab is required but not installed."
    exit 499
}

program define _esttab_export_pair
    syntax namelist(min=1), Stem(string) Title(string) [Keep(string) Order(string) MTitles(string) Stats(string)]

    esttab `namelist' using "${TABLES_DIR}/`stem'.tex", replace ///
        label se star(* 0.10 ** 0.05 *** 0.01) ///
        `=cond("`keep'" != "", "keep(`keep')", "")' ///
        `=cond("`order'" != "", "order(`order')", "")' ///
        `=cond("`mtitles'" != "", `"mtitles(`mtitles')"', "")' ///
        `=cond("`stats'" != "", `"stats(`stats')"', "")' ///
        title("`title'")

    esttab `namelist' using "${TABLES_DIR}/`stem'.csv", replace ///
        csv ///
        label se star(* 0.10 ** 0.05 *** 0.01) ///
        `=cond("`keep'" != "", "keep(`keep')", "")' ///
        `=cond("`order'" != "", "order(`order')", "")' ///
        `=cond("`mtitles'" != "", `"mtitles(`mtitles')"', "")' ///
        `=cond("`stats'" != "", `"stats(`stats')"', "")' ///
        title("`title'")

    preserve
        import delimited using "${TABLES_DIR}/`stem'.csv", clear varnames(1)
        save "${TABLES_DIR}/`stem'.dta", replace
    restore
end

capture which csdid
local has_csdid = cond(_rc == 0, 1, 0)

local run_csdid 1
local run_ptrends 1
local run_atetplot 1

local panels "gold_v2 gold_v2_same_state gold_v2_same_state_matched"

estimates clear

foreach spec in `panels' {
    local panel_path ""
    local panel_label ""
    local short_label ""
    local est_suffix ""

    if "`spec'" == "gold_v2" {
        local panel_path "${ANALYSIS_DIR}/regression_analysis_panel_gold_v2.dta"
        local panel_label "National v2"
        local short_label "National v2"
        local est_suffix "nat"
    }
    else if "`spec'" == "gold_v2_same_state" {
        local panel_path "${ANALYSIS_DIR}/regression_analysis_panel_gold_v2_same_state.dta"
        local panel_label "Same-state"
        local short_label "Same-state"
        local est_suffix "state"
    }
    else if "`spec'" == "gold_v2_same_state_matched" {
        local panel_path "${ANALYSIS_DIR}/regression_analysis_panel_gold_v2_same_state_matched.dta"
        local panel_label "Matched"
        local short_label "Matched"
        local est_suffix "match"
    }

    if !fileexists("`panel_path'") {
        di as error "Missing analysis panel: `panel_path'"
        continue
    }

    di as text "Running staffing econometrics on `panel_label'"
    use "`panel_path'", clear

    keep if sample_main_staffing == 1
    
    tostring ccn_str, replace
    encode ccn_str, gen(ccn_id)
    xtset ccn_id year

    destring high_medicare any_reit_owner any_holding_company_owner sample_payer_mix_outcome, replace force

    gen byte did_treat = 0
    replace did_treat = post_treat if !missing(post_treat)
    gen int gvar_treat = 0
    replace gvar_treat = treat_year if !missing(treat_year)

    gen byte reit_transition = (any_reit_owner == 1) & (did_treat == 1)
    gen byte holdco_transition = (any_holding_company_owner == 1) & (did_treat == 1)

    preserve
        keep if sample_role == "treated" & !missing(baseline_medicaid_share)
        keep ccn_id baseline_medicaid_share
        duplicates drop
        quietly summarize baseline_medicaid_share, detail
        local medicaid_p50 = r(p50)
    restore

    gen double baseline_medicaid_centered = baseline_medicaid_share - `medicaid_p50'
    gen byte high_medicaid = baseline_medicaid_share >= `medicaid_p50' if !missing(baseline_medicaid_share)

    gen byte slack_group = .
    replace slack_group = 1 if high_medicare == 0 & high_medicaid == 1 
    replace slack_group = 2 if high_medicare == 0 & high_medicaid == 0 
    replace slack_group = 3 if high_medicare == 1 & high_medicaid == 1 
    replace slack_group = 4 if high_medicare == 1 & high_medicaid == 0 

    preserve
        keep ccn_id ccn_str sample_role high_medicare high_medicaid slack_group holdco_transition reit_transition
        duplicates drop
        gen byte treated_facility = sample_role == "treated"
        collapse ///
            (count) facility_count=ccn_id ///
            (sum) treated_facility ///
            (sum) holdco_transition ///
            (sum) reit_transition, ///
            by(high_medicare high_medicaid slack_group)
        export delimited using "${TABLES_DIR}/mechanism_support_`est_suffix'.csv", replace
        save "${TABLES_DIR}/mechanism_support_`est_suffix'.dta", replace
    restore

    // Regression Models
    quietly areg pbj_mean_nurse_hprd did_treat i.year, absorb(ccn_id) vce(cluster ccn_id)
    estimates store nurse_main_`est_suffix'

    quietly areg pbj_mean_nurse_hprd did_treat i.year if high_medicare == 1, absorb(ccn_id) vce(cluster ccn_id)
    estimates store nurse_hi_mc_`est_suffix'

    quietly areg pbj_mean_nurse_hprd did_treat i.year if high_medicare == 0, absorb(ccn_id) vce(cluster ccn_id)
    estimates store nurse_lo_mc_`est_suffix'

    forval i = 1/4 {
        quietly areg pbj_mean_nurse_hprd did_treat i.year if slack_group == `i', absorb(ccn_id) vce(cluster ccn_id)
        estimates store nurse_sl_g`i'_`est_suffix'
    }

    quietly areg pbj_mean_nurse_hprd did_treat holdco_transition i.year if high_medicaid == 1, absorb(ccn_id) vce(cluster ccn_id)
    estimates store nurse_hc_hi_ma_`est_suffix'
    
    quietly areg pbj_mean_nurse_hprd did_treat holdco_transition i.year if high_medicaid == 0, absorb(ccn_id) vce(cluster ccn_id)
    estimates store nurse_hc_lo_ma_`est_suffix'

    // Export individual interaction tables
    _esttab_export_pair ///
        nurse_hi_mc_`est_suffix' nurse_lo_mc_`est_suffix', ///
        stem(staffing_medicare_slack_`est_suffix') ///
        title("Medicare Slack Analysis (`short_label')") ///
        keep("did_treat") ///
        mtitles("HighSlack" "LowSlack")

    _esttab_export_pair ///
        nurse_sl_g1_`est_suffix' nurse_sl_g2_`est_suffix' nurse_sl_g3_`est_suffix' nurse_sl_g4_`est_suffix', ///
        stem(staffing_2x2_interaction_`est_suffix') ///
        title("Slack Interaction (Mcare x Mcaid) (`short_label')") ///
        keep("did_treat") ///
        mtitles("Least" "Low/Low" "High/High" "Most")

    _esttab_export_pair ///
        nurse_hc_hi_ma_`est_suffix' nurse_hc_lo_ma_`est_suffix', ///
        stem(staffing_medicaid_holdco_interaction_`est_suffix') ///
        title("HoldCo x Mcaid Interaction (`short_label')") ///
        keep("holdco_transition") ///
        mtitles("HighMcaid" "LowMcaid")

    // Figure Generation (National Sample)
    if "`est_suffix'" == "nat" {
        preserve
            clear
            set obs 2
            gen group = _n
            gen beta = .
            gen se = .
            estimates restore nurse_hi_mc_nat
            replace beta = _b[did_treat] in 1
            replace se = _se[did_treat] in 1
            estimates restore nurse_lo_mc_nat
            replace beta = _b[did_treat] in 2
            replace se = _se[did_treat] in 2
            gen hi = beta + 1.96*se
            gen lo = beta - 1.96*se
            twoway (bar beta group if group==1, color(gs12) barw(0.6)) ///
                   (bar beta group if group==2, color(navy) barw(0.6)) ///
                   (rcap hi lo group, lcolor(black)), ///
                   xlabel(1 "High Medicare (Slack)" 2 "Low Medicare (No Slack)") ///
                   xtitle("") ytitle("Effect on Total Nurse HPRD") ///
                   title("Staffing Impact by Medicare Slack") legend(off) yline(0, lcolor(black))
            capture graph export "${FIGURES_DIR}/staffing_medicare_slack.png", replace
        restore

        preserve
            clear
            set obs 4
            gen group = _n
            gen beta = .
            gen se = .
            forval i = 1/4 {
                estimates restore nurse_sl_g`i'_nat
                replace beta = _b[did_treat] in `i'
                replace se = _se[did_treat] in `i'
            }
            gen hi = beta + 1.96*se
            gen lo = beta - 1.96*se
            twoway (bar beta group if group==1, color(maroon) barw(0.6)) ///
                   (bar beta group if group>1, color(gs12) barw(0.6)) ///
                   (rcap hi lo group, lcolor(black)), ///
                   xlabel(1 "Least Slack" 2 "Low/Low" 3 "High/High" 4 "Most Slack") ///
                   xtitle("") ytitle("Effect on Total Nurse HPRD") ///
                   title("Double Vulnerability: Medicare x Medicaid") legend(off) yline(0, lcolor(black))
            capture graph export "${FIGURES_DIR}/staffing_2x2_slack_interaction.png", replace
        restore

        preserve
            clear
            set obs 2
            gen group = _n
            gen beta = .
            gen se = .
            estimates restore nurse_hc_hi_ma_nat
            replace beta = _b[holdco_transition] in 1
            replace se = _se[holdco_transition] in 1
            estimates restore nurse_hc_lo_ma_nat
            replace beta = _b[holdco_transition] in 2
            replace se = _se[holdco_transition] in 2
            gen hi = beta + 1.96*se
            gen lo = beta - 1.96*se
            twoway (bar beta group if group==1, color(maroon) barw(0.6)) ///
                   (bar beta group if group==2, color(gs12) barw(0.6)) ///
                   (rcap hi lo group, lcolor(black)), ///
                   xlabel(1 "High Medicaid" 2 "Low Medicaid") ///
                   xtitle("") ytitle("Additional Effect of Holding Co Transition") ///
                   title("Asset Stripping impact by Medicaid dependence") legend(off) yline(0, lcolor(black))
            capture graph export "${FIGURES_DIR}/staffing_medicaid_holdco_interaction.png", replace
        restore
    }
}

log close
