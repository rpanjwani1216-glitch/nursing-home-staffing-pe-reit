# Effects of PE and REIT Takeovers on Nursing Home Staffing

**ECON 1430 Final Paper — Rohan Panjwani, Brown University**

This is an analysis-only replication package for the paper examining how
private-equity (PE) and real-estate-investment-trust (REIT) acquisitions affect
nursing-home staffing. It begins with the six analysis-ready panel files used
in the paper and reproduces the descriptive tables, econometric estimates,
figures, and formatted tables.

The raw-data download and panel-construction code is intentionally kept out of
the main branch. The complete historical pipeline is preserved on the
[`data-construction-archive`](https://github.com/rpanjwani1216-glitch/nursing-home-staffing-pe-reit/tree/data-construction-archive)
branch for provenance and auditing.

## Findings at a glance

- PE acquisitions reduce total nurse HPRD by approximately 0.19–0.20 in the
  primary TWFE/CSDID specifications, with larger effects among high-Medicaid
  facilities.
- REIT acquisitions reduce total nurse HPRD by approximately 0.43 in the
  same-state TWFE specification.
- Results are reported for national, same-state, and propensity-score-matched
  control designs.

## Repository layout

```text
data/analysis/                 Six analysis-ready CSV panels and documentation
research/treatment_inputs/     Treatment rosters and cohort summaries
research/verification/         Ownership-verification documentation
stata/                         Descriptive, econometric, and figure code
scripts/analysis/              Python post-processing and table rendering
outputs/reference/             Published reference tables and figures
outputs/generated/             Recreated outputs (ignored by git)
run_all.sh                     Portable analysis runner
```

See [`data/analysis/README.md`](data/analysis/README.md) for panel definitions,
row counts, key variables, and checksums.

## Requirements

- Stata 17 or newer
- Stata packages: `csdid`, `drdid`, `estout`, `stackdid`, and `wildbootstrap`
- Python 3.9 or newer with packages from `requirements.txt`
- Optional for rendered table PDFs/PNGs: `pdflatex` and `pdftoppm`

Install the Python dependencies with:

```bash
python3 -m pip install -r requirements.txt
```

Install the required Stata packages from the Stata command prompt if needed:

```stata
ssc install csdid
ssc install drdid
ssc install estout
ssc install stackdid
ssc install wildbootstrap
```

## Reproduce the analysis

From the repository root, either run the complete workflow:

```bash
bash run_all.sh
```

or run the Stata portion directly:

```stata
do stata/run_all_stata.do
```

The first Stata step imports the tracked CSV panels and creates temporary
`.dta` files under `data/analysis/_stata/`. Generated results are written to
`outputs/generated/`; the committed paper outputs remain unchanged under
`outputs/reference/`.

If Stata is not available as `stata-mp`, set `STATA_CMD` before running the
shell entry point, for example:

```bash
STATA_CMD="/Applications/Stata/StataSE.app/Contents/MacOS/stata-se" bash run_all.sh
```

For a faster workflow check that skips only the slow wild-cluster bootstrap,
set `REPRO_QUICK=1`. A normal run includes that robustness calculation. The
exploratory HoldCo subgroup event study is not part of the published output; it
can be requested separately with `RUN_EXPLORATORY_HOLDCO=1`.

## Data sources and citation

The analysis panels combine publicly available CMS data, LTCFocus public-use
data, and hand-verified acquisition cohorts. The construction branch documents
the exact source vintages and transformations.

Any publication or research report using these panels should include the
following required LTCFocus reference:

> LTCFocus Public Use Data sponsored by the National Institute on Aging
> (P01 AG027296) through a cooperative agreement with the Brown University
> School of Public Health. Available at [www.ltcfocus.org](https://www.ltcfocus.org/).
> [https://doi.org/10.26300/h9a2-2c26](https://doi.org/10.26300/h9a2-2c26)

See [`CITATION.md`](CITATION.md) for a copy-ready citation.
