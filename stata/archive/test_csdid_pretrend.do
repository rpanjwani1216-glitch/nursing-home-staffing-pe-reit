version 17
clear all
set more off
use "/Users/rohanpanjwani/School/ECON_1430/Final_Project/data/intermediate/analysis/panels/regression_analysis_panel_gold_v2.dta", clear
keep if sample_main_staffing == 1
encode ccn_str, gen(ccn_id)
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
csdid pbj_mean_nurse_hprd baseline_medicaid_share if high_medicaid==1, ivar(ccn_id) time(year) gvar(gvar_treat) method(dripw)
estat pretrend, window(-3 -1)
return list
ereturn list
