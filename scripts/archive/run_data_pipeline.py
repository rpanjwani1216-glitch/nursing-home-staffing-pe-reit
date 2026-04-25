#!/usr/bin/env python3
"""Master data pipeline orchestrator.

Runs the full raw-to-regression-ready Python pipeline in the canonical order.

Important:
- The regression-ready analysis panels are still built by the two dedicated
  scripts below.
- A later experimental "unified" builder changed the panel contract and broke
  downstream assumptions in Stata and repo documentation.
- This wrapper intentionally keeps the known-good entrypoints as canonical.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

def run_script(name: str):
    print(f"\n>>> Executing {name}...")
    script_path = SCRIPTS / name
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SCRIPTS) + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run([sys.executable, str(script_path)], capture_output=False, env=env)
    if result.returncode != 0:
        print(f"!!! Error: {name} failed with return code {result.returncode}")
        sys.exit(result.returncode)

def main():
    # 1. Foundation
    run_script("build_pe_treatment_dataset.py")
    run_script("build_cms_foundation_panel.py")
    run_script("refresh_cms_deficiency_history.py")
    run_script("refresh_cms_provider_history.py")
    run_script("build_ltcfocus_intermediates.py")
    
    # 2. Control Pools
    run_script("build_control_candidate_pools.py")
    
    # 3. Analysis Panels
    # Keep the two dedicated builders as canonical. Downstream Stata code and
    # repo documentation assume the schema produced by these scripts.
    run_script("build_regression_analysis_panel.py")
    run_script("build_regression_analysis_panel_same_state.py")
    
    # 4. Optional / Robustness
    # run_script("build_matched_control_panel.py") # Requires Stata baseline file first

    print("\n✅ Python Data Pipeline completed successfully.")

if __name__ == "__main__":
    main()
