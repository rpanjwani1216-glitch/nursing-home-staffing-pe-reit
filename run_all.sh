#!/usr/bin/env bash
# =============================================================================
# run_all.sh — Full reproducibility pipeline (shell entry point)
# Effects of PE and REIT Takeovers on Nursing Home Staffing
# Rohan Panjwani, ECON 1430, Brown University
#
# Usage:
#   bash run_all.sh
#
# Note:
#   run_all.sh is for shell users.
#   stata/run_all_stata.do is the Stata-only entry point (runs all .do files).
#   scripts/run_data_pipeline.py is the Python-only entry point.
#
# Requirements:
#   - Python 3.9+  with pandas, numpy, scipy, scikit-learn, statsmodels
#   - Stata 17+    with csdid, drdid, estout installed
#   - pdflatex     (/Library/TeX/texbin/pdflatex)
#   - pdftoppm     (/opt/homebrew/bin/pdftoppm)
#
# Raw data must be placed in data/raw/ before running.
# See README.md for data sources and directory layout.
# =============================================================================

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
STATA="/Applications/Stata/StataSE.app/Contents/MacOS/stata-se"
PYTHON="python3"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

echo "============================================================"
echo "  ECON 1430 Final Project — Full Pipeline"
echo "  Root: $ROOT"
echo "============================================================"

# ── STEP 1: Build PE treatment dataset ───────────────────────────────────────
echo ""
echo "[1/8] Building PE treatment dataset..."
$PYTHON "$ROOT/scripts/pipeline/build_pe_treatment_dataset.py" \
  2>&1 | tee "$LOG_DIR/build_pe_treatment_dataset.log"

# ── STEP 2: Build CMS foundation data ────────────────────────────────────────
echo ""
echo "[2/8] Building CMS foundation panel..."
$PYTHON "$ROOT/scripts/pipeline/build_cms_foundation_panel.py" \
  2>&1 | tee "$LOG_DIR/build_cms_foundation_panel.log"

# ── STEP 3: Build LTCFocus intermediates ─────────────────────────────────────
echo ""
echo "[3/8] Building LTCFocus intermediates..."
$PYTHON "$ROOT/scripts/pipeline/build_ltcfocus_intermediates.py" \
  2>&1 | tee "$LOG_DIR/build_ltcfocus_intermediates.log"

# ── STEP 4: Build analysis panels (PE gold+silver and REIT) ──────────────────
echo ""
echo "[4/8] Building analysis panels..."
$PYTHON "$ROOT/scripts/pipeline/build_regression_analysis_panel_gold_plus_silver.py" \
  2>&1 | tee "$LOG_DIR/build_pe_panel.log"
$PYTHON "$ROOT/scripts/pipeline/build_regression_analysis_panel_gold_plus_silver_same_state.py" \
  2>&1 | tee "$LOG_DIR/build_pe_panel_same_state.log"
$PYTHON "$ROOT/scripts/pipeline/build_gold_plus_silver_matched_panel.py" \
  2>&1 | tee "$LOG_DIR/build_pe_panel_matched.log"
$PYTHON "$ROOT/scripts/pipeline/build_reit_extended_staffing_panel.py" \
  2>&1 | tee "$LOG_DIR/build_reit_panel.log"
$PYTHON "$ROOT/scripts/pipeline/build_reit_matched_panel.py" \
  2>&1 | tee "$LOG_DIR/build_reit_panel_matched.log"

# ── STEP 5: Stata — Medicaid foundation ──────────────────────────────────────
echo ""
echo "[5/8] Building Medicaid foundation (Stata)..."
$STATA -b do "$ROOT/stata/1_foundation/build_medicaid_foundation.do" \
  2>&1 | tee "$LOG_DIR/build_medicaid_foundation.log"

# ── STEP 6: Stata — Main econometrics ────────────────────────────────────────
echo ""
echo "[6/8] Running PE strengthening regressions (Stata)..."
$STATA -b do "$ROOT/stata/3_econometrics/run_paper_strengthening_gold_plus_silver.do" \
  2>&1 | tee "$LOG_DIR/run_pe_strengthening.log"

echo ""
echo "[6b/8] Running REIT econometrics (Stata)..."
$STATA -b do "$ROOT/stata/3_econometrics/run_reit_staffing_econometrics.do" \
  2>&1 | tee "$LOG_DIR/run_reit_econometrics.log"

echo ""
echo "[6c/8] Running REIT Medicaid heterogeneity (Stata)..."
$STATA -b do "$ROOT/stata/3_econometrics/run_reit_medicaid_heterogeneity.do" \
  2>&1 | tee "$LOG_DIR/run_reit_medicaid_heterogeneity.log"

echo ""
echo "[6d/8] Running star rating econometrics (Stata)..."
$STATA -b do "$ROOT/stata/3_econometrics/run_star_rating_econometrics_gold_plus_silver.do" \
  2>&1 | tee "$LOG_DIR/run_star_rating_econometrics.log"

# ── STEP 7: Build paper support outputs and figures ──────────────────────────
echo ""
echo "[7/8] Building paper support outputs and figures..."
$PYTHON "$ROOT/scripts/pipeline/build_paper_support_outputs_gold_plus_silver.py" \
  2>&1 | tee "$LOG_DIR/build_pe_support_outputs.log"
$PYTHON "$ROOT/scripts/pipeline/build_reit_support_outputs.py" \
  2>&1 | tee "$LOG_DIR/build_reit_support_outputs.log"

$STATA -b do "$ROOT/stata/4_figures/build_paper_support_figures_gold_plus_silver.do" \
  2>&1 | tee "$LOG_DIR/build_pe_support_figures.log"
$STATA -b do "$ROOT/stata/4_figures/build_clean_pe_paper_figures.do" \
  2>&1 | tee "$LOG_DIR/build_pe_figures.log"
$STATA -b do "$ROOT/stata/4_figures/build_medicaid_tercile_figures_gold_plus_silver.do" \
  2>&1 | tee "$LOG_DIR/build_pe_medicaid_figures.log"
$STATA -b do "$ROOT/stata/4_figures/build_reit_support_figures.do" \
  2>&1 | tee "$LOG_DIR/build_reit_figures.log"
$STATA -b do "$ROOT/stata/4_figures/build_reit_medicaid_tercile_figures.do" \
  2>&1 | tee "$LOG_DIR/build_reit_medicaid_figures.log"

# ── STEP 8: Compile final tables to PDF/PNG ──────────────────────────────────
echo ""
echo "[8/8] Compiling final tables (PDF + PNG)..."
$PYTHON "$ROOT/scripts/pipeline/build_paper_tables_pdf.py" \
  2>&1 | tee "$LOG_DIR/build_paper_tables_pdf.log"
$STATA -b do "$ROOT/stata/5_output/build_paper_tables_pdf.do" \
  2>&1 | tee "$LOG_DIR/build_paper_tables_stata.log"

echo ""
echo "============================================================"
echo "  Pipeline complete."
echo "  Final tables:  outputs/final/pe/tables/"
echo "                 outputs/final/reit/tables/"
echo "  Final figures: outputs/final/pe/figures/"
echo "                 outputs/final/reit/figures/"
echo "  Stata entry:   stata/run_all_stata.do"
echo "============================================================"
