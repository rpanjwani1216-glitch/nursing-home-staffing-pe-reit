# Medicaid Foundation Build

Run [build_medicaid_foundation.do](/Users/rohanpanjwani/School/ECON_1430/Final_Project/stata/foundation/build_medicaid_foundation.do) from either:

- the project root, or
- the `stata/` directory
- a subdirectory such as `stata/foundation/`

## Required inputs

Raw files:

- `data/raw/ltcfocus/`
- `data/raw/outcomes/` (optional if the CMS intermediate master already exists)

Cleaned LTCFocus intermediate:

- `data/intermediate/ltcfocus/ltcfocus_medicaid_analysis.csv`
- `data/intermediate/cms/cms_facility_year_foundation.csv`
- `data/intermediate/cms/clean_control_candidates_v2.csv` for the main control pool

Rules:

- `data/raw/ltcfocus/` should contain the annual LTCFocus workbooks used to build the cleaned intermediate panel.
- `data/raw/outcomes/` may contain one or more facility-year outcome files, but the current default path is to read the existing CMS intermediate master.
- Supported formats are `.dta`, `.csv`, `.xls`, and `.xlsx`.
- Before running the Stata build, generate the cleaned LTCFocus intermediates with:
  - `python3 scripts/build_ltcfocus_intermediates.py`
- The canonical Python pipeline that prepares all cleaned intermediates for Stata is documented in [RUN_PIPELINE.md](/Users/rohanpanjwani/School/ECON_1430/Final_Project/RUN_PIPELINE.md).
- If `data/intermediate/cms/cms_facility_year_foundation.csv` exists, the Stata build will use it as the default outcome panel source.

## Expected identifiers

The script standardizes all facility IDs to a 6-digit string `ccn_str`.

It looks for CCN-like identifier variables with common names such as:

- `ccn_str`
- `ccn`
- `provnum`
- `prvdr_num`
- `federal_provider_number`
- `provider_number`
- `provider_id`

It also looks for common year variables such as:

- `year`
- `fy`
- `report_year`
- `rpt_year`

For LTCFocus, it looks for a Medicaid-share variable using common names such as:

- `paymcaid`
- `medicaid_share`
- `medicaid_pct`
- `medicaid_percent`
- `pct_medicaid`

## Outputs

When the raw data are in place and pass validation, the script will create:

- `data/intermediate/facility_treatment_timing.dta`
- `data/intermediate/facility_medicaid_baseline.dta`
- `data/intermediate/facility_year_master.dta`
- QA logs and CSV diagnostics in `outputs/qa/`

## Related Stata build

For the baseline-comparison table used to assess treated versus control homes
before takeover, use:

- [build_table1_baseline_balance.do](/Users/rohanpanjwani/School/ECON_1430/Final_Project/stata/descriptive/build_table1_baseline_balance.do)

That script reads:

- `data/intermediate/analysis/panels/regression_analysis_panel_gold_v2.dta`

and writes:

- `data/intermediate/analysis/balance/table1_baseline_facility_level_gold_v2.dta`
- `data/intermediate/analysis/balance/table1_baseline_balance_gold_v2.dta`
- `outputs/tables/balance/table1_baseline_balance_gold_v2.csv`

## Verification and diagnostics notes

- The treated timing file currently keeps the verified `non_pe_to_pe` treatment sample used for the main analysis.
- The control-side baseline builder now restricts untreated facilities to the curated `v2` control pool when that file is present.
- For controls, the pseudo-cohort baseline is a weighted average across treated cohort years.
- Because of that, `baseline_medicaid_n_years`, `baseline_window_start`, and `baseline_window_end` should be read as conservative support diagnostics for controls rather than as one literal averaging window.

## Current status

The repo now contains annual LTCFocus raw files, the cleaned LTCFocus intermediate build, the CMS intermediate master, and the `v2` control pool. The Stata script will fail fast if the cleaned LTCFocus intermediate or the CMS intermediate master is missing.
