version 17
clear all
set more off

if "${PROJECT_ROOT}" == "" {
    global PROJECT_ROOT "`c(pwd)'"
}

capture confirm file "${PROJECT_ROOT}/data/analysis/pe_national.csv"
if _rc {
    di as error "Run this file from the repository root or through stata/run_all_stata.do."
    exit 601
}

global ANALYSIS_CSV "${PROJECT_ROOT}/data/analysis"
global ANALYSIS_STATA "${PROJECT_ROOT}/data/analysis/_stata"
capture mkdir "${ANALYSIS_STATA}"

program define _prepare_panel
    syntax, CSV(string) DTA(string) CCNCOL(integer)

    di as text "Preparing `csv'"
    import delimited using "${ANALYSIS_CSV}/`csv'", clear ///
        varnames(1) encoding(UTF-8) stringcols(`ccncol')

    capture confirm variable ccn_str
    if _rc {
        di as error "`csv' does not contain ccn_str."
        exit 111
    }

    capture confirm variable year
    if _rc {
        di as error "`csv' does not contain year."
        exit 111
    }

    foreach v in any_private_equity_owner any_reit_owner any_trust_owner ///
        any_investment_firm_owner any_holding_company_owner ///
        any_management_company_owner {
        capture confirm string variable `v'
        if _rc == 0 {
            tempvar parsed_bool
            gen byte `parsed_bool' = .
            replace `parsed_bool' = 1 if inlist(lower(strtrim(`v')), "true", "1")
            replace `parsed_bool' = 0 if inlist(lower(strtrim(`v')), "false", "0")
            drop `v'
            rename `parsed_bool' `v'
        }
    }

    isid ccn_str year
    compress
    save "${ANALYSIS_STATA}/`dta'", replace
end

_prepare_panel, csv(pe_national.csv) dta(pe_national.dta) ccncol(5)
_prepare_panel, csv(pe_same_state.csv) dta(pe_same_state.dta) ccncol(5)
_prepare_panel, csv(pe_matched.csv) dta(pe_matched.dta) ccncol(5)
_prepare_panel, csv(reit_national.csv) dta(reit_national.dta) ccncol(3)
_prepare_panel, csv(reit_same_state.csv) dta(reit_same_state.dta) ccncol(3)
_prepare_panel, csv(reit_matched.csv) dta(reit_matched.dta) ccncol(3)

program drop _prepare_panel
di as result "Prepared six Stata analysis panels in ${ANALYSIS_STATA}."
