# Project Handoff

This file is meant to let a new collaborator, RA, or AI assistant pick up the project with minimal ramp-up.

It explains:

- what this repo is trying to do
- how the PE and REIT analysis tracks differ
- where the final paper-ready files live
- what has already been debugged
- what is still tentative or incomplete
- what to do next

## 1. What this project is

This is a nursing-home ownership and quality/staffing project with two linked but distinct empirical tracks:

1. **PE study**
   - The main, more mature paper track.
   - Focuses on private-equity ownership transitions.
   - Main results are already organized into a final paper package.

2. **REIT study**
   - A later extension built to analyze real-estate-ownership transitions that resemble “financialized” restructuring rather than straightforward operator takeovers.
   - Built around a pooled set of major REIT-related deals plus associated event-window and verification work.
   - Substantial progress has been made, including matched controls and Medicaid heterogeneity, but interpretation is more delicate than in the PE paper.

The workflow is intentionally split:

- **Python**: raw-data cleaning, panel construction, matching support files, plot-data preparation
- **Stata**: FE DiD, `csdid`, stacked DiD, tables, and most final figures

Short version:

- Python builds the data.
- Stata estimates the models.

## 2. High-level repo map

Important top-level folders and files:

- `data/raw/`
  - raw CMS, LTCFocus, and other source data
- `data/intermediate/`
  - cleaned intermediates
- `outputs/tables/`
  - econometric tables, balance tables
- `outputs/figures/`
  - figure outputs
- `outputs/qa/`
  - logs and QA artifacts
- `research/`
  - treatment verification files, event-window builds, and final paper packages
- `scripts/`
  - Python builders
- `stata/`
  - Stata analysis scripts
- `RUN_PIPELINE.md`
  - existing pipeline-oriented documentation

Useful final-package folders:

- `research/final_tables_figures_pe/`
- `research/final_tables_figures_reit/`

## 3. PE track: current status

The PE track is the closest thing to the “main paper.”

### Main PE design

The working PE specification is the **gold plus silver** design.

Core features:

- facility-year panel
- national, same-state, and matched control designs
- main staffing outcomes:
  - total nurse HPRD
  - RN HPRD
- Medicaid heterogeneity:
  - continuous interaction
  - high/low split
  - Medicaid terciles

### Main PE result summary

The strongest PE result is the reduction in **total nurse HPRD** after PE takeover.

Interpretation from the last stable pass:

- FE DiD: negative and significant for total nurse HPRD across national, same-state, and matched controls
- `csdid` event study:
  - stable `t-2` and `t-1`
  - negative and significant `t+1` and `t+2`
- Medicaid heterogeneity:
  - strongest in the higher-Medicaid group / top tercile
  - this is shown most cleanly with the FE DiD tercile figures and tables

RN effects exist, but they are weaker than total nurse.

### Final PE paper package

Folder:

- `research/final_tables_figures_pe/`

Important contents:

- clean main staffing coefficient figure
- total-nurse `csdid` figures for national / same-state / matched
- Medicaid tercile FE DiD figures
- main PE staffing tables
- Medicaid functional-form summary

See:

- `research/final_tables_figures_pe/README.md`

## 4. REIT track: current status

The REIT track is now substantial, but it is more heterogeneous than the PE track.

### Main REIT cohorts

The pooled REIT treatment file currently stacks:

- `REIT001`: AHR / Trilogy (2015)
- `REIT002`: Omega / Consulate / FC Encore broader verified subset (2019)
- `REIT003`: Welltower / Aurora reverse-engineered subset (2021)

There is also a large 2011 HCR/Healthpeak ManorCare event-window build in `research/`, but the current pooled REIT regression panel uses the canonical `reit_facility_verification.csv` build rather than every historical exploratory subset.

Main treatment file:

- `research/reit_facility_verification.csv`

### REIT ownership / transaction reconstruction work

There is a large amount of source-based ownership investigation already done:

- `research/reit_ownership_investigation/`

Important contents include:

- `reit_consecutive_homes_investigated.csv`
- `reit_consecutive_homes_verified_public.csv`
- `reit_owner_cluster_public_verification.csv`

These files document:

- current owner identification
- whether the owner appears to be a REIT or REIT affiliate
- REIT ownership clusters
- observed CHOW dates where available
- prior-owner information where recoverable

### REIT event-window builds already created

These are separate, deal-specific research objects:

- `research/trilogy_2015_event_window/`
- `research/fc_encore_2019_event_window/`
- `research/omega_consulate_2019_event_window/`
- `research/welltower_aurora_reverse_engineered/`
- `research/healthpeak_hcr_2011_event_window/`

These are useful for deal-specific work, but the current REIT econometrics rely on the extended pooled REIT staffing panel.

### Main REIT panel

Main pooled REIT staffing panels:

- `data/intermediate/analysis/panels/reit_staffing_panel_extended.csv`
- `data/intermediate/analysis/panels/reit_staffing_panel_extended_same_state.csv`
- `data/intermediate/analysis/panels/reit_staffing_panel_extended_same_state_matched.csv`

Summary files:

- `data/intermediate/analysis/panels/reit_staffing_panel_extended_summary.json`
- `data/intermediate/analysis/matching/matched_control_sample_reit_same_state_summary.json`

### Important REIT bug that was fixed

This matters a lot.

Originally, the REIT extended staffing panel was dropping post-2018 staffing for later cohorts because the builder only read the old LTCFocus staffing columns:

- `dchrppd`
- `rnhrppd`
- etc.

But later years were carried in PBJ-style LTCFocus columns:

- `dchprd_pbj`
- `rnhprd_pbj`
- etc.

This meant `REIT002` and `REIT003` were effectively losing post-treatment staffing in the original panel.

This was fixed by coalescing the legacy staffing columns with the PBJ-era columns in:

- `scripts/build_reit_extended_staffing_panel.py`

After that fix:

- post-treatment staffing exists for all three main pooled REIT cohorts
- the earlier absurdly large direct-care estimate came down to a more plausible size

### REIT matched controls

A matched REIT branch has now been built.

Builder:

- `scripts/build_reit_matched_panel.py`

Current winning matched spec:

- `linear_totalbeds_occupancypct_directcarehprd_medicaidshare`

From:

- `data/intermediate/analysis/matching/matched_control_sample_reit_same_state_summary.json`

Key matched summary numbers:

- treated facilities: `62`
- matched controls: `186`
- matched panel rows: `3476`

### Main REIT econometrics

Main Stata scripts:

- `stata/econometrics/run_reit_staffing_econometrics.do`
- `stata/econometrics/run_reit_medicaid_heterogeneity.do`
- `stata/econometrics/build_reit_support_figures.do`
- `stata/econometrics/build_reit_medicaid_tercile_figures.do`

Python support parsers:

- `scripts/build_reit_support_outputs.py`
- `scripts/build_reit_medicaid_tercile_figures.py`

### Current REIT result summary

After the staffing fix and matched build:

- direct-care FE DiD is negative in national, same-state, and matched
- RN FE DiD is also negative, though smaller
- `csdid` event studies are negative post-treatment, especially at `t+2`

Current main REIT tables:

- `outputs/tables/econometrics_reit/reit_staffing_main_directcare.csv`
- `outputs/tables/econometrics_reit/reit_staffing_main_rn.csv`
- `outputs/tables/econometrics_reit/reit_csdid_event_directcare.csv`
- `outputs/tables/econometrics_reit/reit_csdid_event_rn.csv`

### REIT Medicaid heterogeneity

This has now been run in national, same-state, and matched designs.

Important outputs:

- `reit_staffing_heterogeneity_directcare.csv`
- `reit_staffing_high_low_directcare.csv`
- `reit_staffing_medicaid_terciles_directcare.csv`

And the direct-care tercile figures:

- `paper_medicaid_terciles_directcare_reit_combined.*`
- `paper_medicaid_terciles_directcare_reit_reit_v2.*`
- `paper_medicaid_terciles_directcare_reit_reit_v2_same_state.*`
- `paper_medicaid_terciles_directcare_reit_reit_v2_same_state_matched.*`

### Important REIT interpretation caveat

The REIT Medicaid heterogeneity does **not** look like the PE Medicaid heterogeneity.

Current REIT pattern:

- lower-Medicaid terciles show larger direct-care reductions
- high-Medicaid terciles look smaller / weaker

This initially looked odd, but two diagnostics already help explain it:

1. **Slack / baseline-level story**
   - low-Medicaid REIT homes start with much higher direct-care staffing and much higher Medicare share
   - they likely had more staffing to cut in levels

2. **Deal composition story**
   - the pooled REIT sample is balanced across low/middle/high terciles overall
   - but the **deal mix inside each tercile is highly uneven**
   - e.g. `REIT001` is concentrated in low-Medicaid homes, while later cohorts contribute much more of the middle/high groups

So:

- pooled REIT Medicaid heterogeneity is valid as an **aggregate exploratory result**
- but it should not be oversold as a pure within-deal causal Medicaid mechanism

Useful diagnostic files:

- `outputs/tables/econometrics_reit/reit_tercile_by_deal_directcare.csv`
- `outputs/tables/econometrics_reit/paper_medicaid_terciles_directcare_reit_plot_data.csv`

## 5. Final paper-ready folders

### PE final package

- `research/final_tables_figures_pe/`

Use this for the PE paper.

### REIT final package

- `research/final_tables_figures_reit/`

This now includes:

- main coefficient figure
- direct-care and RN event-study figures
- matched event-study figures
- Medicaid tercile direct-care figures including matched
- main REIT staffing tables
- REIT Medicaid heterogeneity tables

See:

- `research/final_tables_figures_reit/README.md`

## 6. Current clustering / inference conventions

Main FE DiD models are clustered at the **facility level**:

- `vce(cluster ccn_id)`

This is true for:

- PE main FE DiD
- REIT main FE DiD
- REIT Medicaid heterogeneity FE DiD

The PE side also contains some wild-bootstrap robustness work, but that is not the default main inference choice.

## 7. What is final vs exploratory

### PE: effectively final

The PE track is close to paper-ready.

Recommended PE main claims:

- total nurse HPRD falls after PE takeover
- event-study pretrends are reasonable
- higher-Medicaid homes appear more negatively affected

### REIT: usable but more exploratory

The REIT track is now coherent and reproducible, but the paper-style interpretation needs more caution because:

- the pooled treatment bundles different transaction types
- REIT ownership is not always the same as operator takeover
- Medicaid heterogeneity is confounded by deal composition
- some REIT cohorts are stronger than others from a source-verification standpoint

Recommended REIT main claims:

- pooled REIT-linked transitions are associated with lower direct-care staffing
- RN staffing also declines, though more modestly
- results persist in matched controls
- Medicaid heterogeneity is suggestive but exploratory

## 8. Important scripts and what they do

### Core PE-side scripts

- `scripts/build_pe_treatment_dataset.py`
- `scripts/build_cms_foundation_panel.py`
- `scripts/build_ltcfocus_intermediates.py`
- `scripts/build_control_candidate_pools.py`
- `scripts/build_regression_analysis_panel.py`
- `scripts/build_regression_analysis_panel_same_state.py`
- `scripts/build_gold_plus_silver_matched_panel.py`
- `stata/econometrics/run_paper_strengthening_gold_plus_silver.do`
- `stata/econometrics/build_clean_pe_paper_figures.do`
- `stata/econometrics/build_medicaid_tercile_figures_gold_plus_silver.do`

### Core REIT-side scripts

- `scripts/build_reit_extended_staffing_panel.py`
- `scripts/build_reit_matched_panel.py`
- `scripts/build_reit_support_outputs.py`
- `scripts/build_reit_medicaid_tercile_figures.py`
- `stata/econometrics/run_reit_staffing_econometrics.do`
- `stata/econometrics/run_reit_medicaid_heterogeneity.do`
- `stata/econometrics/build_reit_support_figures.do`
- `stata/econometrics/build_reit_medicaid_tercile_figures.do`

### Research / reconstruction scripts

- `scripts/build_reit_ownership_investigation.py`
- `scripts/build_trilogy_2015_event_window.py`
- `scripts/build_fc_encore_2019_event_window.py`
- `scripts/build_omega_consulate_2019_event_window.py`
- `scripts/build_welltower_aurora_reverse_engineered_subset.py`

## 9. Suggested rebuild order

If the goal is to regenerate the **current** PE + REIT state, use this order.

### Python

```bash
python3 scripts/build_pe_treatment_dataset.py
python3 scripts/build_cms_foundation_panel.py
python3 scripts/refresh_cms_deficiency_history.py
python3 scripts/refresh_cms_provider_history.py
python3 scripts/build_ltcfocus_intermediates.py
python3 scripts/build_control_candidate_pools.py
python3 scripts/build_regression_analysis_panel.py
python3 scripts/build_regression_analysis_panel_same_state.py
python3 scripts/build_gold_plus_silver_matched_panel.py
python3 scripts/build_reit_extended_staffing_panel.py
python3 scripts/build_reit_matched_panel.py
python3 scripts/build_reit_support_outputs.py
python3 scripts/build_reit_medicaid_tercile_figures.py
```

### Stata

```bash
stata-se -b do stata/econometrics/run_paper_strengthening_gold_plus_silver.do
stata-se -b do stata/econometrics/build_clean_pe_paper_figures.do
stata-se -b do stata/econometrics/build_medicaid_tercile_figures_gold_plus_silver.do
stata-se -b do stata/econometrics/run_reit_staffing_econometrics.do
stata-se -b do stata/econometrics/run_reit_medicaid_heterogeneity.do
stata-se -b do stata/econometrics/build_reit_support_figures.do
stata-se -b do stata/econometrics/build_reit_medicaid_tercile_figures.do
```

On this machine, Stata binary used most recently was:

- `/Applications/Stata/StataSE.app/Contents/MacOS/stata-se`

## 10. Known quirks / debugging notes

### 1. Blank matched REIT direct-care figure

This happened once because the final package had a stale bad export.

The actual matched plot-data were fine.

If this happens again:

- rerun `stata/econometrics/build_reit_support_figures.do`
- then recopy the fresh figure into `research/final_tables_figures_reit/`

### 2. REIT support-data parsers assume current esttab layouts

The REIT parsers are now tuned to the current CSV structure.

If Stata table formatting changes, the parsers may need small adjustments.

### 3. `RUN_PIPELINE.md` is partly stale for REIT

It still references some older REIT scripts that are no longer the full picture.

Use this handoff file plus the actual current scripts as the source of truth.

## 11. Best next steps

If continuing the PE paper:

1. Write the manuscript using `research/final_tables_figures_pe/`
2. Keep RN and stacked-DiD material as secondary / appendix unless needed

If continuing the REIT extension:

1. Decide whether the REIT paper should stay **pooled** or become more **deal-specific**
2. Treat Medicaid heterogeneity as exploratory unless doing more within-deal work
3. If a next diagnostic is desired, the most natural one is:
   - low-Medicaid / high-Medicare vs low-Medicaid / low-Medicare
4. If publishing the REIT track, be explicit that REIT treatment often changes the ownership/financial structure rather than necessarily the operating entity

## 12. Bottom line

If someone opens this repo fresh:

- the **PE paper** is the stable main paper
- the **REIT paper** is a credible extension with a now-functional matched branch
- final paper-ready files are already organized in `research/final_tables_figures_pe/` and `research/final_tables_figures_reit/`
- the biggest REIT bug that mattered has already been fixed
- the main remaining challenge is interpretation, not pipeline breakage

