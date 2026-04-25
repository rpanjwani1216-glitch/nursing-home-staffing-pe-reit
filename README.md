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

All data are publicly available. Raw data files are not tracked in git (14 GB total)
but can be downloaded automatically — see **Reproducing the Paper** below.

| Source | Description | Download |
|--------|-------------|----------|
| **LTCFocus** (Brown University) | Facility-year staffing (HPRD), payer mix, bed counts | [ltcfocus.org/data](https://ltcfocus.org/data) — free registration required |
| **CMS PBJ Nurse Staffing** | Daily nurse staffing by facility-quarter (2017–2023) | [data.cms.gov](https://data.cms.gov/quality-of-care/payroll-based-journal-daily-nurse-staffing) — automated via manifest |
| **CMS SNF All Owners** | Monthly ownership snapshots (2022–present) | [data.cms.gov](https://data.cms.gov/provider-characteristics/hospitals-and-other-facilities/skilled-nursing-facility-all-owners) — automated via manifest |
| **CMS SNF CHOW** | Change of Ownership filings (2022–present) | [data.cms.gov](https://data.cms.gov/provider-characteristics/hospitals-and-other-facilities/skilled-nursing-facility-change-of-ownership) — automated via manifest |
| **CMS SNF Enrollments** | Provider enrollment snapshots (2022–present) | [data.cms.gov](https://data.cms.gov/provider-characteristics/hospitals-and-other-facilities/skilled-nursing-facility-enrollments) — automated via manifest |
| **CMS Care Compare** | Star ratings, deficiencies, provider info (2016–2023 archived) | [CMS archive](https://data.cms.gov/provider-data/archived-data/nursing-homes) — automated via manifest |
| **CMS Form 671** | LTC facility characteristics (2023–present) | [data.cms.gov](https://data.cms.gov/provider-data/dataset/4pq5-n9py) — automated via manifest |

Download manifests (exact versioned URLs for every CMS file used) are tracked in git at
`data/manifests/` and read automatically by `scripts/download_raw_data.py`.

PE ownership was verified via CHOW filings + internet search (trade press, HealthcareComps, ProPublica). See `research/verification/ownership_transition_verification_notes.md`.

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

### Option A — Full pipeline from raw data

```bash
# 1. Download CMS data automatically + get LTCFocus instructions:
python3 scripts/download_raw_data.py

# 2. Follow the printed LTCFocus instructions (free registration at ltcfocus.org),
#    place the annual XLS files in data/raw/ltcfocus/, then run the full pipeline:
bash run_all.sh

# Final tables → outputs/final/pe/tables/ and outputs/final/reit/tables/
# Final figures → outputs/final/pe/figures/ and outputs/final/reit/figures/
```

`run_all.sh` runs the download script first (Step 0) and skips files that already exist,
so it is safe to re-run at any point.

### Option B — Stata only (final panels already built)

The final analysis panels are tracked in git at `data/final/panels/` as CSVs.
If you only want to re-run the econometrics and produce outputs without rebuilding
the data from scratch:

```stata
* In Stata, run the master do file:
do stata/run_all_stata.do
```

This reads from `data/final/panels/`, runs all regressions and figures, and writes
to `outputs/final/`.
