# Effects of PE and REIT Takeovers on Nursing Home Staffing

**ECON 1430 Final Paper — Rohan Panjwani, Brown University**

This repository contains the full data pipeline, econometric analysis, and paper outputs examining how private equity (PE) and real estate investment trust (REIT) acquisitions of nursing homes affect nursing staffing levels.

---

## Findings at a Glance

- **PE acquisitions** reduce total nurse HPRD by ~0.19–0.20 (TWFE/CSDID), concentrated among high-Medicaid facilities.
- **REIT acquisitions** reduce total nurse HPRD by ~0.43 (TWFE same-state), with the effect building sharply to −0.29 HPRD by t+2 in the event study.
- Results are robust across three control designs: national, same-state, and propensity-score matched.

---

## Repository Structure

```
├── run_all.sh                        # Single entry point — runs full pipeline
├── README.md
├── .gitignore
│
├── data/
│   ├── raw/                          # Raw data (not tracked in git; see below)
│   └── intermediate/                 # Built by Python pipeline
│
├── scripts/                          # Python data pipeline
│   ├── build_cms_foundation_panel.py
│   ├── build_ltcfocus_intermediates.py
│   ├── build_pe_treatment_dataset.py
│   ├── build_regression_analysis_panel_gold_plus_silver.py
│   ├── build_regression_analysis_panel_gold_plus_silver_same_state.py
│   ├── build_gold_plus_silver_matched_panel.py
│   ├── build_reit_extended_staffing_panel.py
│   ├── build_reit_matched_panel.py
│   ├── build_paper_support_outputs_gold_plus_silver.py
│   ├── build_reit_support_outputs.py
│   ├── build_paper_tables_pdf.py     # Compiles .tex → PDF + PNG
│   └── archive/                      # Superseded scripts (kept for reference)
│
├── stata/
│   ├── setup_macros.do
│   ├── run_all_analysis.do           # Stata-only entry point
│   ├── foundation/
│   │   └── build_medicaid_foundation.do
│   ├── descriptive/
│   │   ├── build_table1_baseline_balance_same_state.do
│   │   └── build_table1_baseline_balance_same_state_matched.do
│   ├── econometrics/
│   │   ├── run_staffing_econometrics.do
│   │   ├── run_paper_strengthening_gold_plus_silver.do
│   │   ├── run_reit_staffing_econometrics.do
│   │   ├── run_reit_medicaid_heterogeneity.do
│   │   ├── run_reit_tercile_by_deal_diagnostics.do
│   │   ├── build_clean_pe_paper_figures.do
│   │   ├── build_medicaid_tercile_figures_gold_plus_silver.do
│   │   ├── build_reit_support_figures.do
│   │   ├── build_reit_medicaid_tercile_figures.do
│   │   └── build_paper_tables_pdf.do
│   └── archive/                      # Superseded do files
│
├── outputs/
│   ├── intermediate/                 # Working outputs (gitignored)
│   │   ├── tables/econometrics/      # PE regression tables (.tex, .csv, .dta)
│   │   ├── tables/econometrics_reit/ # REIT regression tables
│   │   ├── figures/econometrics/     # PE figures (.pdf, .png)
│   │   ├── figures/econometrics_reit/# REIT figures
│   │   └── qa/                       # QA/validation outputs
│   └── final/                        # Paper-ready outputs (tracked in git)
│       ├── pe/
│       │   ├── tables/               # Compiled PDF + PNG tables
│       │   └── figures/              # Final PE figures
│       └── reit/
│           ├── tables/               # Compiled PDF + PNG tables
│           └── figures/              # Final REIT figures
│
├── research/
│   ├── pe_facility_verification.csv  # Hand-verified PE facility roster
│   ├── reit_facility_verification.csv
│   ├── pe_acquisition_deals.csv
│   ├── ownership_transition_verification_notes.md
│   ├── reit_ownership_investigation/ # REIT cohort construction workfiles
│   └── [deal-specific event windows] # fc_encore, omega_consulate, trilogy, welltower
│
└── logs/                             # Pipeline run logs
```

---

## Data Sources

All data are publicly available:

| Source | Description | Location |
|--------|-------------|----------|
| **LTCFocus** (Brown University) | Facility-year staffing (HPRD), payer mix, bed counts | `data/raw/ltcfocus/` |
| **CMS CHOW filings** | Change of Ownership notifications | `data/raw/cms/chow/` |
| **CMS Provider of Services** | Facility characteristics, ownership flags | `data/raw/cms/pos/` |
| **CMS Nursing Home Compare** | Star ratings | `data/raw/cms/nhc/` |
| **ProPublica Nursing Home Inspect** | PE ownership verification | Public URL |

PE ownership was verified via CHOW filings + internet search (trade press, HealthcareComps, ProPublica). See `research/ownership_transition_verification_notes.md`.

REIT cohorts were identified via CMS `any_reit_owner` flag + cluster verification. Welltower/Aurora (REIT003) was reverse-engineered from a 2021 exit event traced back to the 2011 Genesis/Welltower deal using LTCFocus 2009–2013 data.

---

## Treatment Definitions

**PE:** 52 facilities (31 gold + 21 silver) across 8 PE deals, 2014–2020. Gold = verified by ≥2 independent sources; silver = single-source verified.

**REIT:** 3 REIT deals — American Healthcare REIT/Trilogy (2015), Omega Healthcare/Consulate (2019), Welltower/Genesis (2011) — with original acquisitions spanning 2011–2019. Panel data covers 2009–2023. Treatment year = year of REIT acquisition of the operating company or facility lease.

---

## Empirical Strategy

- **Primary:** Two-way fixed effects DiD (facility + year FEs), clustered SEs at facility level
- **Robustness:** Callaway–Sant'Anna (2021) CSDID, event-study aggregation by ℓ = t−g
- **Heterogeneity:** Medicaid share terciles (stratified regressions); High vs. Low Medicaid split
- **Control designs:** National pool, same-state pool, 3:1 nearest-neighbor propensity-score matched within state

---

## Requirements

```
Python 3.9+:  pandas, numpy, scipy, scikit-learn, statsmodels
Stata 17+:    csdid, drdid, estout  (install via ssc)
LaTeX:        pdflatex  (/Library/TeX/texbin/)
poppler:      pdftoppm  (brew install poppler)
```

---

## Reproducing the Paper

```bash
# 1. Place raw data in data/raw/ (see Data Sources above)
# 2. Run the full pipeline:
bash run_all.sh

# Final tables → outputs/final/pe/tables/ and outputs/final/reit/tables/
# Final figures → outputs/final/pe/figures/ and outputs/final/reit/figures/
```
