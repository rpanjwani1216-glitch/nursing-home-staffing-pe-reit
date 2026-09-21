# Stata analysis

Run `do stata/run_all_stata.do` from the repository root. The master file:

1. imports the six tracked CSV panels into a local Stata cache;
2. recreates baseline-balance tables;
3. runs the PE, REIT, Medicaid-heterogeneity, and star-rating models; and
4. recreates the paper figures.

The Stata cache lives at `data/analysis/_stata/` and generated results live at
`outputs/generated/`. Both directories are ignored by git.

Folder roles:

- `2_descriptive/`: baseline and balance tables
- `3_econometrics/`: main regressions, event studies, and diagnostics
- `4_figures/`: publication figures
- `5_output/`: optional table rendering wrapper
