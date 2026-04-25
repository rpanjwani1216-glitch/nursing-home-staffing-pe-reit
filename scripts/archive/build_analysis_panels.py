#!/usr/bin/env python3
"""Compatibility wrapper for building regression-ready analysis panels.

This script exists because a previous thread introduced a "unified" analysis
panel builder under this filename. That rewrite diverged from the schema used
by the rest of the repo and from the documented canonical workflow.

To keep old references working without breaking downstream code, this wrapper
simply runs the two established panel builders:

- build_regression_analysis_panel.py
- build_regression_analysis_panel_same_state.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run_script(name: str) -> None:
    script_path = SCRIPTS / name
    print(f"Running {name}...")
    result = subprocess.run([sys.executable, str(script_path)], cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    run_script("build_regression_analysis_panel.py")
    run_script("build_regression_analysis_panel_same_state.py")
    print("Finished building canonical analysis panels.")


if __name__ == "__main__":
    main()
