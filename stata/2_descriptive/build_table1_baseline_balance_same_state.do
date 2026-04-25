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

global ANALYSIS_DIR "${PROJECT_ROOT}/data/final"
global ANALYSIS_PANEL_DTA "${ANALYSIS_DIR}/panels/regression_analysis_panel_gold_plus_silver_v2_same_state.dta"
global ANALYSIS_BALANCE_DIR "${ANALYSIS_DIR}/balance"
global OUTPUTS_DIR "${PROJECT_ROOT}/outputs"
global TABLES_DIR "${OUTPUTS_DIR}/tables/balance"
global QA_OUTPUT "${PROJECT_ROOT}/outputs/intermediate/qa/tables"

capture mkdir "${OUTPUTS_DIR}"
capture mkdir "${OUTPUTS_DIR}/tables"
capture mkdir "${TABLES_DIR}"
capture mkdir "${ANALYSIS_BALANCE_DIR}"
capture mkdir "${QA_OUTPUT}"

if !fileexists("${ANALYSIS_PANEL_DTA}") {
    di as error "Same-state analysis panel not found: ${ANALYSIS_PANEL_DTA}"
    di as error "Run python3 scripts/build_regression_analysis_panel_same_state.py first."
    exit 601
}

log using "${QA_OUTPUT}/table1_baseline_balance_same_state.log", replace text
di as text "Using analysis panel: ${ANALYSIS_PANEL_DTA}"

use "${ANALYSIS_PANEL_DTA}", clear

capture confirm variable sample_main_staffing
if _rc {
    di as error "The analysis panel must contain sample_main_staffing."
    exit 111
}
keep if sample_main_staffing == 1

capture confirm variable sample_role
if _rc {
    di as error "The analysis panel must contain sample_role."
    exit 111
}

gen byte treated_ever = sample_role == "treated"
label var treated_ever "Treated facility (=1)"

gen byte chain_affiliated = !missing(provider_chain_id) if !missing(provider_chain_id)
replace chain_affiliated = 0 if missing(chain_affiliated)
label var chain_affiliated "Chain affiliated (=1)"

gen str80 __ownership_lc = lower(provider_ownership_type)
gen byte for_profit = regexm(__ownership_lc, "for profit") if !missing(__ownership_lc)
replace for_profit = 0 if missing(for_profit)
drop __ownership_lc
label var for_profit "For profit (=1)"

label var provider_certified_beds "Certified beds"
label var provider_avg_residents_per_day "Average residents per day"
label var pbj_mean_rn_hprd "RN hours per resident day"
label var pbj_mean_nurse_hprd "Total nurse hours per resident day"
label var provider_health_rating "Health inspection rating"
label var provider_overall_rating "Overall rating"
label var provider_staffing_rating "Staffing rating"
label var form671_medicare_census_mean "Medicare census"

local table_vars ///
    provider_certified_beds ///
    provider_avg_residents_per_day ///
    pbj_mean_rn_hprd ///
    pbj_mean_nurse_hprd ///
    provider_health_rating ///
    provider_overall_rating ///
    provider_staffing_rating ///
    chain_affiliated ///
    for_profit

preserve
    keep if treated_ever == 1
    keep ccn_str treat_year
    duplicates drop
    contract treat_year
    rename treat_year cohort_year
    rename _freq treated_count
    egen treated_total = total(treated_count)
    gen cohort_weight = treated_count / treated_total
    tempfile cohort_weights
    save `cohort_weights', replace
restore

preserve
    keep if treated_ever == 1 & year < treat_year
    collapse (mean) `table_vars' (count) baseline_support_years = year, by(ccn_str treated_ever)
    tempfile treated_baseline
    save `treated_baseline', replace
restore

preserve
    keep if treated_ever == 0
    gen byte join_key = 1
    tempfile controls_only
    save `controls_only', replace
restore

preserve
    use `cohort_weights', clear
    gen byte join_key = 1
    tempfile cohort_weights_x
    save `cohort_weights_x', replace
restore

preserve
    use `controls_only', clear
    joinby join_key using `cohort_weights_x'
    drop join_key
    keep if year < cohort_year
    tempfile control_long
    save `control_long', replace
restore

preserve
    use `control_long', clear
    keep ccn_str
    duplicates drop
    gen byte treated_ever = 0
    tempfile control_baseline
    save `control_baseline', replace
restore

preserve
    use `control_long', clear
    capture drop valid_pseudocohorts baseline_window_start baseline_window_end
    bysort ccn_str cohort_year: gen cohort_tag = _n == 1
    bysort ccn_str: egen valid_pseudocohorts = total(cohort_tag)
    bysort ccn_str cohort_year: egen cohort_start = min(year)
    bysort ccn_str cohort_year: egen cohort_end = max(year)
    bysort ccn_str: egen baseline_window_start = min(cohort_start)
    bysort ccn_str: egen baseline_window_end = max(cohort_end)
    keep ccn_str valid_pseudocohorts baseline_window_start baseline_window_end
    duplicates drop
    tempfile control_support
    save `control_support', replace
restore

foreach var of local table_vars {
    preserve
        use `control_long', clear
        collapse (mean) cohort_mean = `var', by(ccn_str cohort_year cohort_weight)
        gen weight_component = cohort_weight if !missing(cohort_mean)
        bysort ccn_str: egen valid_weight_total = total(weight_component)
        gen weighted_component = (cohort_weight / valid_weight_total) * cohort_mean if !missing(cohort_mean) & valid_weight_total > 0
        bysort ccn_str: egen `var' = total(weighted_component)
        keep ccn_str `var'
        duplicates drop
        tempfile onevar
        save `onevar', replace
    restore

    use `control_baseline', clear
    merge 1:1 ccn_str using `onevar', nogen
    save `control_baseline', replace
}

use `control_baseline', clear
merge 1:1 ccn_str using `control_support', nogen
save `control_baseline', replace

use `treated_baseline', clear
gen valid_pseudocohorts = .
gen baseline_window_start = .
gen baseline_window_end = .
append using `control_baseline'

save "${ANALYSIS_BALANCE_DIR}/table1_baseline_facility_level_gold_plus_silver_v2_same_state.dta", replace
export delimited using "${ANALYSIS_BALANCE_DIR}/table1_baseline_facility_level_gold_plus_silver_v2_same_state.csv", replace

tempname results_handle
tempfile results_long
postfile `results_handle' ///
    str40 variable ///
    str80 row_label ///
    double control_mean ///
    double treated_mean ///
    double diff_estimate ///
    double diff_se ///
    double std_diff ///
    double n_control ///
    double n_treated ///
    using `results_long', replace

foreach var of local table_vars {
    quietly summarize `var' if treated_ever == 0
    local control_mean = r(mean)
    local control_sd = r(sd)
    local n_control = r(N)

    quietly summarize `var' if treated_ever == 1
    local treated_mean = r(mean)
    local treated_sd = r(sd)
    local n_treated = r(N)

    quietly regress `var' treated_ever, vce(robust)
    local diff_estimate = _b[treated_ever]
    local diff_se = _se[treated_ever]

    local std_diff = .
    local pooled_sd = sqrt(((`control_sd')^2 + (`treated_sd')^2) / 2)
    if `pooled_sd' > 0 {
        local std_diff = (`treated_mean' - `control_mean') / `pooled_sd'
    }

    local row_label "`var'"
    if "`var'" == "provider_certified_beds" local row_label "Certified beds"
    if "`var'" == "provider_avg_residents_per_day" local row_label "Average residents per day"
    if "`var'" == "pbj_mean_rn_hprd" local row_label "RN hours per resident day"
    if "`var'" == "pbj_mean_nurse_hprd" local row_label "Total nurse hours per resident day"
    if "`var'" == "provider_health_rating" local row_label "Health inspection rating"
    if "`var'" == "provider_overall_rating" local row_label "Overall rating"
    if "`var'" == "provider_staffing_rating" local row_label "Staffing rating"
    if "`var'" == "chain_affiliated" local row_label "Chain affiliated (=1)"
    if "`var'" == "for_profit" local row_label "For profit (=1)"

    post `results_handle' ///
        ("`var'") ///
        ("`row_label'") ///
        (`control_mean') ///
        (`treated_mean') ///
        (`diff_estimate') ///
        (`diff_se') ///
        (`std_diff') ///
        (`n_control') ///
        (`n_treated')
}

postclose `results_handle'

use `results_long', clear
gen row_order = .
replace row_order = 1 if variable == "provider_certified_beds"
replace row_order = 2 if variable == "provider_avg_residents_per_day"
replace row_order = 3 if variable == "pbj_mean_rn_hprd"
replace row_order = 4 if variable == "pbj_mean_nurse_hprd"
replace row_order = 5 if variable == "provider_health_rating"
replace row_order = 6 if variable == "provider_overall_rating"
replace row_order = 7 if variable == "provider_staffing_rating"
replace row_order = 8 if variable == "chain_affiliated"
replace row_order = 9 if variable == "for_profit"
sort row_order

save "${ANALYSIS_BALANCE_DIR}/table1_baseline_balance_gold_plus_silver_v2_same_state.dta", replace
export delimited using "${TABLES_DIR}/table1_baseline_balance_gold_plus_silver_v2_same_state.csv", replace

gen str20 control_mean_s = cond(missing(control_mean), "", strofreal(control_mean, "%9.3f"))
gen str20 diff_estimate_s = cond(missing(diff_estimate), "", strofreal(diff_estimate, "%9.3f"))
gen str20 diff_se_s = cond(missing(diff_se), "", strofreal(diff_se, "%9.3f"))
gen str20 std_diff_s = cond(missing(std_diff), "", strofreal(std_diff, "%9.3f"))
gen str20 n_control_s = cond(missing(n_control), "", strofreal(n_control, "%9.0f"))
gen str20 n_treated_s = cond(missing(n_treated), "", strofreal(n_treated, "%9.0f"))

tempname texhandle
file open `texhandle' using "${TABLES_DIR}/table1_baseline_balance_gold_plus_silver_v2_same_state.tex", write replace text
file write `texhandle' "\begin{table}[!htbp]" _n
file write `texhandle' "\centering" _n
file write `texhandle' "\caption{Baseline Comparison of Treated and Same-State Control Nursing Homes}" _n
file write `texhandle' "\label{tab:baseline_balance_gold_plus_silver_v2_same_state}" _n
file write `texhandle' "\begin{tabular}{lccccc}" _n
file write `texhandle' "\toprule" _n
file write `texhandle' "& Control mean & Difference: treated-control & Std. diff. & \$N\$ control & \$N\$ treated \\\\" _n
file write `texhandle' "\midrule" _n
quietly forvalues i = 1/`=_N' {
    local row_label = row_label[`i']
    local control_mean_s = control_mean_s[`i']
    local diff_estimate_s = diff_estimate_s[`i']
    local diff_se_s = diff_se_s[`i']
    local std_diff_s = std_diff_s[`i']
    local n_control_s = n_control_s[`i']
    local n_treated_s = n_treated_s[`i']
    file write `texhandle' "`row_label' & `control_mean_s' & `diff_estimate_s' & `std_diff_s' & `n_control_s' & `n_treated_s' \\\\" _n
    file write `texhandle' " &  & (`diff_se_s') &  &  &  \\\\" _n
}
file write `texhandle' "\bottomrule" _n
file write `texhandle' "\end{tabular}" _n
file write `texhandle' "\begin{minipage}{0.92\linewidth}" _n
file write `texhandle' "\footnotesize" _n
file write `texhandle' "\textit{Notes:} Control means are computed from the pseudo-cohort baseline same-state control sample aligned to the treated cohort timing. Treated means use only pre-treatment years. Differences are estimated from facility-level regressions of each baseline characteristic on a treated indicator with robust standard errors reported in parentheses." _n
file write `texhandle' "\end{minipage}" _n
file write `texhandle' "\end{table}" _n
file close `texhandle'

di as result "Same-state baseline Table 1 artifacts created."
log close
