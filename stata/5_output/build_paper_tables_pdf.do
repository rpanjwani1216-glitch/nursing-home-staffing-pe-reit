version 17
set more off

if "${PROJECT_ROOT}" == "" {
    global PROJECT_ROOT "`c(pwd)'"
}

shell python3 "${PROJECT_ROOT}/scripts/analysis/build_tables.py"
if _rc exit _rc
