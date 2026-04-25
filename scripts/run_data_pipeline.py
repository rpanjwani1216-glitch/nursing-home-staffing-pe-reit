#!/usr/bin/env python3
"""Master Python pipeline orchestrator.

Run this script to build all analysis-ready datasets from raw inputs.

Prerequisites
-------------
Raw data must already exist under:
  data/raw/outcomes/cms/      — CMS facility, staffing, and deficiency files
  data/raw/ltcfocus/          — Annual LTCFocus workbooks (.xlsx)
  research/treatment_inputs/  — Hand-curated PE and REIT facility lists

Usage
-----
  python scripts/run_data_pipeline.py

The script runs each pipeline stage in order, printing progress.  Each stage
is a standalone script under scripts/pipeline/ and can also be run individually.

Pipeline order
--------------
  1.  build_pe_treatment_dataset.py
  2.  build_cms_foundation_panel.py
  3.  build_ltcfocus_intermediates.py
  4.  build_regression_analysis_panel_gold_plus_silver.py
  5.  build_regression_analysis_panel_gold_plus_silver_same_state.py
  6.  build_gold_plus_silver_matched_panel.py
  7.  build_reit_extended_staffing_panel.py
  8.  build_reit_matched_panel.py
  9.  build_paper_support_outputs_gold_plus_silver.py
  10. build_reit_support_outputs.py
  11. build_paper_tables_pdf.py
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPELINE_DIR = ROOT / "scripts" / "pipeline"

STEPS = [
    "build_pe_treatment_dataset.py",
    "build_cms_foundation_panel.py",
    "build_ltcfocus_intermediates.py",
    "build_regression_analysis_panel_gold_plus_silver.py",
    "build_regression_analysis_panel_gold_plus_silver_same_state.py",
    "build_gold_plus_silver_matched_panel.py",
    "build_reit_extended_staffing_panel.py",
    "build_reit_matched_panel.py",
    "build_paper_support_outputs_gold_plus_silver.py",
    "build_reit_support_outputs.py",
    "build_paper_tables_pdf.py",
]


def run_step(step_name: str, step_num: int, total: int) -> None:
    script = PIPELINE_DIR / step_name
    print(f"\n{'=' * 66}")
    print(f"  Step {step_num}/{total}: {step_name}")
    print(f"{'=' * 66}")
    t0 = time.time()
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
    )
    elapsed = time.time() - t0
    if result.returncode != 0:
        print(f"\nERROR: {step_name} failed (exit code {result.returncode}).")
        sys.exit(result.returncode)
    print(f"  Done in {elapsed:.1f}s")


def main() -> None:
    total = len(STEPS)
    print(f"\nStarting full data pipeline ({total} steps)")
    print(f"Project root: {ROOT}")
    overall_t0 = time.time()
    for i, step in enumerate(STEPS, start=1):
        run_step(step, i, total)
    elapsed = time.time() - overall_t0
    print(f"\n{'=' * 66}")
    print(f"  ALL PIPELINE STEPS COMPLETE  ({elapsed:.1f}s total)")
    print(f"{'=' * 66}\n")


if __name__ == "__main__":
    main()
