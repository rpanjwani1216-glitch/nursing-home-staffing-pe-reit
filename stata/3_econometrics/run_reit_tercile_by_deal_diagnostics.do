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
global TABLES_DIR "${PROJECT_ROOT}/outputs/intermediate/tables/econometrics_reit"
global QA_DIR "${PROJECT_ROOT}/outputs/intermediate/qa/econometrics_reit"

capture mkdir "${TABLES_DIR}"
capture mkdir "${QA_DIR}"

log using "${QA_DIR}/run_reit_tercile_by_deal_diagnostics.log", replace text

use "${ANALYSIS_DIR}/reit_staffing_panel_extended.dta", clear
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
    quietly _pctile baseline_medicaid_share, p(33.333333 66.666667)
    local medicaid_p33 = r(r1)
    local medicaid_p67 = r(r2)
restore

gen byte medicaid_tercile = .
replace medicaid_tercile = 1 if !missing(baseline_medicaid_share) & baseline_medicaid_share < `medicaid_p33'
replace medicaid_tercile = 2 if !missing(baseline_medicaid_share) & baseline_medicaid_share >= `medicaid_p33' & baseline_medicaid_share < `medicaid_p67'
replace medicaid_tercile = 3 if !missing(baseline_medicaid_share) & baseline_medicaid_share >= `medicaid_p67'

tempname posth
postfile `posth' str8 deal_id str8 tercile double coef se lb ub int nobs int treated_facilities using "${TABLES_DIR}/reit_tercile_by_deal_directcare_raw.dta", replace

foreach deal in REIT001 REIT002 REIT003 {
    foreach terc in 1 2 3 {
        quietly count if deal_id == "`deal'" & medicaid_tercile == `terc' & sample_role == "treated"
        local tfac = r(N)
        quietly count if deal_id == "`deal'" & medicaid_tercile == `terc' & sample_role == "treated" & post_treat == 1
        local tpost = r(N)
        if `tfac' > 0 & `tpost' > 0 {
            capture noisily areg ltcfocus_directcare_hprd did_treat i.year if (sample_role == "control" | deal_id == "`deal'") & medicaid_tercile == `terc', absorb(ccn_id) vce(cluster ccn_id)
            if _rc == 0 {
                local b = _b[did_treat]
                local s = _se[did_treat]
                local lb = `b' - 1.96*`s'
                local ub = `b' + 1.96*`s'
                local n = e(N)
                local terc_lab = cond(`terc'==1, "Low", cond(`terc'==2, "Middle", "High"))
                post `posth' ("`deal'") ("`terc_lab'") (`b') (`s') (`lb') (`ub') (`n') (`tfac')
            }
        }
    }
}

postclose `posth'
use "${TABLES_DIR}/reit_tercile_by_deal_directcare_raw.dta", clear
export delimited using "${TABLES_DIR}/reit_tercile_by_deal_directcare.csv", replace

log close
