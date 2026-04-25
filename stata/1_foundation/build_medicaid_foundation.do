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
    di as error "Could not locate research/treatment_inputs/pe_facility_verification.csv. Run this script from the project root or a stata subdirectory."
    exit 601
}

local repro_int : env REPRO_INTERMEDIATE
if "`repro_int'" == "" local repro_int "intermediate"
global INTERMEDIATE "${PROJECT_ROOT}/data/`repro_int'"

local repro_out : env REPRO_OUTPUT
if "`repro_out'" == "" local repro_out "outputs"
global OUTPUTS_DIR "${PROJECT_ROOT}/`repro_out'"

global TREATMENT_CSV "${PROJECT_ROOT}/research/treatment_inputs/pe_facility_verification.csv"
global RAW_LTCFOCUS "${PROJECT_ROOT}/data/raw/ltcfocus"
global RAW_OUTCOMES "${PROJECT_ROOT}/data/raw/outcomes"
global LTCFOCUS_INTERMEDIATE "${INTERMEDIATE}/ltcfocus"
global LTCFOCUS_FULL_CSV "${LTCFOCUS_INTERMEDIATE}/ltcfocus_facility_year_full.csv"
global LTCFOCUS_ANALYSIS_CSV "${LTCFOCUS_INTERMEDIATE}/ltcfocus_medicaid_analysis.csv"
global LTCFOCUS_BASELINE_INPUTS_CSV "${LTCFOCUS_INTERMEDIATE}/ltcfocus_medicaid_baseline_inputs.csv"
global CMS_FOUNDATION_CSV "${INTERMEDIATE}/cms/cms_facility_year_foundation.csv"
global CONTROL_V2_CSV "${INTERMEDIATE}/cms/clean_control_candidates_v2.csv"
global QA_OUTPUT "${OUTPUTS_DIR}/qa"

capture mkdir "${PROJECT_ROOT}/data"
capture mkdir "${PROJECT_ROOT}/data/raw"
capture mkdir "${RAW_LTCFOCUS}"
capture mkdir "${RAW_OUTCOMES}"
capture mkdir "${INTERMEDIATE}"
capture mkdir "${LTCFOCUS_INTERMEDIATE}"
capture mkdir "${OUTPUTS_DIR}"
capture mkdir "${QA_OUTPUT}"

program define _find_first_var, rclass
    syntax, Candidates(string)
    local found ""
    foreach candidate of local candidates {
        capture confirm variable `candidate'
        if !_rc {
            local found "`candidate'"
            continue, break
        }
    }
    return local varname "`found'"
end

program define _import_source
    syntax using/
    local source "`using'"
    local source_l = lower("`source'")

    if strmatch("`source_l'", "*.dta") {
        use "`source'", clear
    }
    else if strmatch("`source_l'", "*.csv") {
        import delimited using "`source'", clear varnames(1) stringcols(_all)
    }
    else if strmatch("`source_l'", "*.xlsx") | strmatch("`source_l'", "*.xls") {
        import excel using "`source'", clear firstrow allstring
    }
    else {
        di as error "Unsupported source file type: `source'"
        exit 198
    }
end

program define _make_ccn_str
    syntax varname
    tempvar raw pad
    capture drop ccn_str
    capture confirm numeric variable `varlist'
    if !_rc {
        tostring `varlist', gen(`raw') format(%18.0f) force
    }
    else {
        gen str40 `raw' = `varlist'
    }
    replace `raw' = ustrtrim(`raw')
    replace `raw' = ustrregexra(`raw', "[^0-9]", "")
    gen str12 `pad' = "000000" + `raw'
    gen str6 ccn_str = substr(`pad', strlen(`pad') - 5, 6)
    replace ccn_str = "" if `raw' == ""
end

program define _make_source_id
    syntax varname, Newvar(name)
    tempvar raw
    capture drop `newvar'
    capture confirm numeric variable `varlist'
    if !_rc {
        tostring `varlist', gen(`raw') format(%18.0f) force
    }
    else {
        gen str80 `raw' = `varlist'
    }
    replace `raw' = ustrtrim(`raw')
    gen str80 `newvar' = `raw'
end

program define _sanitize_year
    syntax varname
    capture drop year
    capture confirm numeric variable `varlist'
    if !_rc {
        gen int year = `varlist'
    }
    else {
        gen str20 __year_raw = ustrtrim(`varlist')
        destring __year_raw, gen(year) force
        drop __year_raw
    }
end

mata:
    string vector outfiles
    outfiles = dir(st_global("RAW_OUTCOMES"), "files", "*.dta")
    outfiles = outfiles \ dir(st_global("RAW_OUTCOMES"), "files", "*.csv")
    outfiles = outfiles \ dir(st_global("RAW_OUTCOMES"), "files", "*.xls")
    outfiles = outfiles \ dir(st_global("RAW_OUTCOMES"), "files", "*.xlsx")
    st_local("outcome_n", strofreal(rows(outfiles)))
    st_local("outcome_files", invtokens(char(34) :+ outfiles :+ char(34), " "))
end
local outcome_override_path ""
if fileexists("${CMS_FOUNDATION_CSV}") {
    local outcome_n 1
    local outcome_files "\"${CMS_FOUNDATION_CSV}\""
    local outcome_override_path "${CMS_FOUNDATION_CSV}"
}
else if `outcome_n' == 0 {
    di as error "No outcome raw files found in ${RAW_OUTCOMES}, and no CMS foundation file found at ${CMS_FOUNDATION_CSV}."
    exit 601
}

if !fileexists("${LTCFOCUS_ANALYSIS_CSV}") {
    di as error "Cleaned LTCFocus analysis file not found: ${LTCFOCUS_ANALYSIS_CSV}"
    di as error "Run the Python intermediate build pipeline before running this Stata build."
    exit 601
}

local ltcfocus_path "${LTCFOCUS_ANALYSIS_CSV}"

tempfile treated_timing ltcfocus_clean outcome_master panel_with_treat panel_facilities baseline_all cohort_weights
tempfile ltcfocus_facilities outcome_facilities treated_unmatched_ltcfocus treated_unmatched_outcomes

log using "${QA_OUTPUT}/input_audit.log", replace text
di as text "Project root: ${PROJECT_ROOT}"
di as text "Verified treatment source: ${TREATMENT_CSV}"
di as text "LTCFocus cleaned analysis source: `ltcfocus_path'"
di as text "Outcome source count: `outcome_n'"
di as text "Outcome files: `outcome_files'"

import delimited using "${TREATMENT_CSV}", clear varnames(1) stringcols(_all)
count
di as text "Treatment CSV rows: " %9.0f r(N)

keep if lower(ustrtrim(transition_verified)) == "yes" & ustrtrim(transition_type) == "non_pe_to_pe"
count
di as text "Verified treated rows retained: " %9.0f r(N)

_make_ccn_str ccn
count if missing(ccn_str)
if r(N) > 0 {
    di as error "Verified treated sample has rows with missing canonical CCN."
    list facility_name ccn ownership_effective_date if missing(ccn_str), noobs abbreviate(32)
    exit 459
}

duplicates tag ccn_str, gen(dup_ccn)
count if dup_ccn > 0
if r(N) > 0 {
    preserve
    keep if dup_ccn > 0
    export delimited using "${QA_OUTPUT}/duplicate_treated_ccn.csv", replace
    restore
    di as error "Duplicate verified treated CCNs found; see outputs/qa/duplicate_treated_ccn.csv"
    exit 459
}
drop dup_ccn

gen str20 ownership_effective_date_clean = ustrtrim(ownership_effective_date)
gen treat_month = monthly(ownership_effective_date_clean, "MY")
format treat_month %tm
gen treat_year = year(dofm(treat_month))

count if missing(treat_year)
if r(N) > 0 {
    preserve
    keep if missing(treat_year)
    export delimited using "${QA_OUTPUT}/unparseable_treat_dates.csv", replace
    restore
    di as error "Some verified treated rows have unparseable ownership_effective_date values; see outputs/qa/unparseable_treat_dates.csv"
    exit 459
}

keep ccn_str facility_name state deal_id treat_year treat_month verification_tier
gen treated_ever = 1
gen str20 verification_source_note = cond(verification_tier == "silver", "keep_verified_silver", "keep_verified_gold")
order ccn_str facility_name state deal_id treated_ever treat_year treat_month verification_tier
save `treated_timing', replace
save "${INTERMEDIATE}/facility_treatment_timing.dta", replace

preserve
contract treat_year
rename _freq treated_count
egen treated_total = total(treated_count)
gen cohort_weight = treated_count / treated_total
export delimited using "${QA_OUTPUT}/treated_cohort_weights.csv", replace
save `cohort_weights', replace
restore

use `treated_timing', clear
count
di as text "Treatment timing file saved with treated rows: " %9.0f r(N)

import delimited using "`ltcfocus_path'", clear varnames(1) stringcols(_all)
count
di as text "LTCFocus cleaned rows: " %9.0f r(N)

capture confirm variable ccn_str
if _rc {
    di as error "Cleaned LTCFocus analysis file must contain ccn_str."
    exit 111
}
capture confirm variable year
if _rc {
    di as error "Cleaned LTCFocus analysis file must contain year."
    exit 111
}
capture confirm variable ltcfocus_medicaid_share
if _rc {
    di as error "Cleaned LTCFocus analysis file must contain ltcfocus_medicaid_share."
    exit 111
}

replace ccn_str = ustrtrim(ccn_str)
replace ccn_str = ustrregexra(ccn_str, "[^0-9]", "")
replace ccn_str = substr("000000" + ccn_str, strlen("000000" + ccn_str) - 5, 6) if !missing(ccn_str)

gen str20 __year_raw = ustrtrim(year)
destring __year_raw, gen(year_clean) force
drop year
rename year_clean year

gen str30 __medicaid_raw = ustrtrim(ltcfocus_medicaid_share)
replace __medicaid_raw = subinstr(__medicaid_raw, "%", "", .)
replace __medicaid_raw = subinstr(__medicaid_raw, ",", "", .)
destring __medicaid_raw, gen(medicaid_share) force
drop __medicaid_raw

local ltcfocus_year_var "year"
local ltcfocus_medicaid_var "ltcfocus_medicaid_share"
local ltcfocus_id_note "cleaned_intermediate_ccn_str"
local medicaid_scale_note "as_provided"

count if missing(year)
if r(N) > 0 {
    di as error "Cleaned LTCFocus panel contains rows with missing year."
    exit 459
}

count if missing(ccn_str)
if r(N) > 0 {
    di as error "Cleaned LTCFocus panel contains rows with missing ccn_str."
    exit 459
}

keep if !missing(ccn_str) & !missing(year)
duplicates tag ccn_str year, gen(dup_ccn_year)
count if dup_ccn_year > 0
if r(N) > 0 {
    preserve
    keep if dup_ccn_year > 0
    export delimited using "${QA_OUTPUT}/duplicate_ltcfocus_ccn_year.csv", replace
    restore
    di as error "Duplicate LTCFocus ccn_str x year rows found; see outputs/qa/duplicate_ltcfocus_ccn_year.csv"
    exit 459
}
drop dup_ccn_year
save `ltcfocus_clean', replace

use `ltcfocus_clean', clear
keep ccn_str
duplicates drop
save `ltcfocus_facilities', replace

use `treated_timing', clear
merge 1:1 ccn_str using `ltcfocus_facilities'
preserve
keep if _merge == 1
export delimited using "${QA_OUTPUT}/treated_unmatched_ltcfocus.csv", replace
restore
count if _merge == 1
if r(N) > 0 {
    di as error "Verified treated facilities unmatched to LTCFocus found; see outputs/qa/treated_unmatched_ltcfocus.csv"
    exit 459
}
drop _merge

clear
save `outcome_master', emptyok replace
local first_outcome = 1

foreach outcome_file of local outcome_files {
    local outcome_path "${RAW_OUTCOMES}/`outcome_file'"
    if "`outcome_override_path'" != "" {
        local outcome_path "`outcome_override_path'"
    }
    di as text "Processing outcome file: `outcome_path'"
    _import_source using "`outcome_path'"

    local outcome_ccn_candidates "ccn_str ccn provnum prvdr_num federal_provider_number provider_number provider_id facility_ccn"
    local outcome_year_candidates "year fy fiscal_year report_year rpt_year"

    _find_first_var, candidates("`outcome_ccn_candidates'")
    local outcome_ccn_var "`r(varname)'"
    if "`outcome_ccn_var'" == "" {
        di as error "Could not identify a CCN-compatible identifier in outcome file `outcome_file'."
        exit 111
    }

    _find_first_var, candidates("`outcome_year_candidates'")
    local outcome_year_var "`r(varname)'"
    if "`outcome_year_var'" == "" {
        di as error "Could not identify a year variable in outcome file `outcome_file'."
        exit 111
    }

    _make_ccn_str `outcome_ccn_var'
    _sanitize_year `outcome_year_var'
    keep if !missing(ccn_str) & !missing(year)

    duplicates tag ccn_str year, gen(dup_ccn_year)
    count if dup_ccn_year > 0
    if r(N) > 0 {
        local outcome_stub = strtoname("`outcome_file'")
        preserve
        keep if dup_ccn_year > 0
        export delimited using "${QA_OUTPUT}/duplicate_outcome_ccn_year_`outcome_stub'.csv", replace
        restore
        di as error "Outcome file `outcome_file' has duplicate ccn_str x year rows."
        exit 459
    }
    drop dup_ccn_year

    tempfile current_outcome
    save `current_outcome', replace

    if `first_outcome' {
        use `current_outcome', clear
        save `outcome_master', replace
        local first_outcome = 0
    }
    else {
        use `outcome_master', clear
        ds ccn_str year, not
        local master_vars `r(varlist)'
        tempfile existing_master
        save `existing_master', replace

        use `current_outcome', clear
        ds ccn_str year, not
        local current_vars `r(varlist)'
        local overlap : list master_vars & current_vars
        if "`overlap'" != "" {
            di as error "Outcome files contain overlapping non-key variables: `overlap'"
            di as error "Rename upstream or consolidate variables before rerunning."
            exit 459
        }

        merge 1:1 ccn_str year using `existing_master', nogen keep(1 2 3)
        save `outcome_master', replace
    }
}

use `outcome_master', clear
duplicates tag ccn_str year, gen(dup_master)
count if dup_master > 0
if r(N) > 0 {
    di as error "Master outcome panel has duplicate ccn_str x year rows after merge."
    exit 459
}
drop dup_master
save `outcome_master', replace

use `outcome_master', clear
keep ccn_str
duplicates drop
save `outcome_facilities', replace

use `treated_timing', clear
merge 1:1 ccn_str using `outcome_facilities'
preserve
keep if _merge == 1
export delimited using "${QA_OUTPUT}/treated_unmatched_outcomes.csv", replace
restore
count if _merge == 1
di as text "Verified treated facilities unmatched to outcome panel: " %9.0f r(N)
if r(N) > 0 {
    di as error "Verified treated facilities are missing from the outcome panel; see outputs/qa/treated_unmatched_outcomes.csv"
    exit 459
}
drop _merge

di as text "LTCFocus year range and Medicaid-share summary"
use `ltcfocus_clean', clear
summ year medicaid_share
di as text "LTCFocus variable selection: year=`ltcfocus_year_var' medicaid=`ltcfocus_medicaid_var' id_note=`ltcfocus_id_note' scale=`medicaid_scale_note'"

di as text "Outcome master year range"
use `outcome_master', clear
summ year
log close

log using "${QA_OUTPUT}/baseline_medicaid_diagnostics.log", replace text

use `outcome_master', clear
merge m:1 ccn_str using `treated_timing', nogen keep(1 3)
replace treated_ever = 0 if missing(treated_ever)
save `panel_with_treat', replace

preserve
keep ccn_str treated_ever
duplicates drop
save `panel_facilities', replace
restore

tempfile control_v2
local use_control_v2 0
if fileexists("${CONTROL_V2_CSV}") {
    import delimited using "${CONTROL_V2_CSV}", clear varnames(1) stringcols(_all)
    keep ccn_str
    replace ccn_str = ustrtrim(ccn_str)
    replace ccn_str = ustrregexra(ccn_str, "[^0-9]", "")
    replace ccn_str = substr("000000" + ccn_str, strlen("000000" + ccn_str) - 5, 6) if !missing(ccn_str)
    keep if !missing(ccn_str)
    duplicates drop
    save `control_v2', replace
    local use_control_v2 1
}

use `ltcfocus_clean', clear
merge m:1 ccn_str using `treated_timing', keep(3) nogen
keep if year < treat_year
bysort ccn_str: egen baseline_medicaid_share = mean(medicaid_share)
bysort ccn_str: egen baseline_medicaid_n_years = count(medicaid_share)
bysort ccn_str: egen baseline_window_start = min(year)
bysort ccn_str: egen baseline_window_end = max(year)
bysort ccn_str: keep if _n == 1
gen str32 baseline_method = "treated_all_preyears"
keep ccn_str treated_ever treat_year baseline_medicaid_share baseline_medicaid_n_years baseline_window_start baseline_window_end baseline_method
preserve
keep if baseline_medicaid_n_years < 2
export delimited using "${QA_OUTPUT}/treated_insufficient_medicaid_baseline.csv", replace
restore
keep if baseline_medicaid_n_years >= 2
tempfile treated_baseline
save `treated_baseline', replace

use `ltcfocus_clean', clear
merge m:1 ccn_str using `panel_facilities', keep(3) nogen
keep if treated_ever == 0
if `use_control_v2' {
    merge m:1 ccn_str using `control_v2', keep(3) nogen
}
tempfile control_ltcfocus
save `control_ltcfocus', replace

use `cohort_weights', clear
rename treat_year cohort_year
save `cohort_weights', replace
export delimited using "${QA_OUTPUT}/control_pseudocohort_weights.csv", replace

use `control_ltcfocus', clear
joinby using `cohort_weights'
keep if year < cohort_year
bysort ccn_str cohort_year: egen cohort_baseline_share = mean(medicaid_share)
bysort ccn_str cohort_year: egen cohort_n_years = count(medicaid_share)
bysort ccn_str cohort_year: egen cohort_window_start = min(year)
bysort ccn_str cohort_year: egen cohort_window_end = max(year)
bysort ccn_str cohort_year: keep if _n == 1
keep if cohort_n_years >= 2
bysort ccn_str: egen valid_weight_total = total(cohort_weight)
gen normalized_weight = cohort_weight / valid_weight_total
gen weighted_baseline_share = normalized_weight * cohort_baseline_share
bysort ccn_str: egen baseline_medicaid_share = total(weighted_baseline_share)
bysort ccn_str: egen baseline_medicaid_n_years = min(cohort_n_years)
bysort ccn_str: egen baseline_window_start = min(cohort_window_start)
bysort ccn_str: egen baseline_window_end = max(cohort_window_end)
bysort ccn_str: egen valid_pseudocohorts = count(cohort_year)
bysort ccn_str: keep if _n == 1
gen treated_ever = 0
gen treat_year = .
gen str32 baseline_method = "control_weighted_pseudocohort"
label variable baseline_medicaid_n_years "Conservative support: min valid pre-years across control pseudo-cohorts"
label variable baseline_window_start "Earliest year used by any valid control pseudo-cohort baseline"
label variable baseline_window_end "Latest year used by any valid control pseudo-cohort baseline"
keep ccn_str treated_ever treat_year baseline_medicaid_share baseline_medicaid_n_years baseline_window_start baseline_window_end baseline_method valid_pseudocohorts
tempfile control_baseline
save `control_baseline', replace

use `treated_baseline', clear
append using `control_baseline'
duplicates tag ccn_str, gen(dup_baseline)
count if dup_baseline > 0
if r(N) > 0 {
    di as error "Duplicate facility rows found in Medicaid baseline file."
    exit 459
}
drop dup_baseline
save `baseline_all', replace
save "${INTERMEDIATE}/facility_medicaid_baseline.dta", replace

use `baseline_all', clear
count
di as text "Facility Medicaid baseline rows saved: " %9.0f r(N)
bysort treated_ever: summ baseline_medicaid_share baseline_medicaid_n_years
export delimited using "${QA_OUTPUT}/facility_medicaid_baseline_preview.csv", replace
log close

log using "${QA_OUTPUT}/merge_diagnostics.log", replace text

use `panel_with_treat', clear
merge m:1 ccn_str using `baseline_all', keepusing(baseline_medicaid_share baseline_medicaid_n_years baseline_window_start baseline_window_end baseline_method valid_pseudocohorts)
replace treated_ever = 0 if missing(treated_ever)
gen baseline_medicaid_missing = (_merge == 1 | missing(baseline_medicaid_share))
drop _merge

count if treated_ever == 1 & missing(treat_year)
if r(N) > 0 {
    di as error "Treated facilities with missing treat_year remain after merge."
    exit 459
}

preserve
keep if baseline_medicaid_missing
export delimited using "${QA_OUTPUT}/facilities_missing_medicaid_baseline.csv", replace
restore

gen post_treat = 0
replace post_treat = year >= treat_year if treated_ever == 1 & !missing(treat_year)

gen event_time = .
replace event_time = year - treat_year if treated_ever == 1 & !missing(treat_year)

count if baseline_medicaid_missing
di as text "Rows missing Medicaid baseline before eligibility filter: " %9.0f r(N)

drop if baseline_medicaid_missing

count
di as text "Final facility-year master rows after Medicaid-baseline eligibility filter: " %9.0f r(N)

preserve
keep ccn_str treated_ever
duplicates drop
count if treated_ever == 1
di as text "Treated facilities in final master: " %9.0f r(N)
count if treated_ever == 0
di as text "Control facilities in final master: " %9.0f r(N)
restore

save "${INTERMEDIATE}/facility_year_master.dta", replace
log close

di as result "Medicaid dependence foundation build completed."
di as result "Saved:"
di as result "  ${INTERMEDIATE}/facility_treatment_timing.dta"
di as result "  ${INTERMEDIATE}/facility_medicaid_baseline.dta"
di as result "  ${INTERMEDIATE}/facility_year_master.dta"
