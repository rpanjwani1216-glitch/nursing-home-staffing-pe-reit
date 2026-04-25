#!/usr/bin/env python3
"""
Compile all final paper tables into publication-quality PDFs and PNGs.

For each .tex fragment (esttab output):
  1. Strip year fixed-effect rows
  2. Wrap in a full LaTeX document
  3. Compile with pdflatex
  4. Convert to PNG with pdftoppm
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]
SRC_PE      = ROOT / "outputs/intermediate/tables/econometrics"
SRC_REIT    = ROOT / "outputs/intermediate/tables/econometrics_reit"
OUT_PE      = ROOT / "outputs/final/pe/tables"
OUT_REIT    = ROOT / "outputs/final/reit/tables"

import shutil as _shutil
PDFLATEX = _shutil.which("pdflatex") or "/Library/TeX/texbin/pdflatex"
PDFTOPPM = _shutil.which("pdftoppm") or "/opt/homebrew/bin/pdftoppm"


def strip_year_fe(src: str) -> str:
    """Remove year dummy coefficient rows from an esttab .tex fragment."""
    # Remove blocks like:  [1em]\n20XX.year ... \n (0.xxx) \n
    src = re.sub(
        r"\[1em\]\s*\n\s*20\d{2}\.year[^\n]*\n[^\n]*\n",
        "",
        src,
    )
    # Catch any remaining year rows not preceded by [1em]
    src = re.sub(
        r"^\s*20\d{2}\.year[^\n]*\n[^\n]*\n",
        "",
        src,
        flags=re.MULTILINE,
    )
    return src


def add_fe_rows(src: str, ncols: int) -> str:
    """Insert Year FE / Facility FE indicator rows above Observations."""
    yes = " & Yes" * ncols
    fe_block = (
        f"Year FE{yes} \\\\\n"
        f"Facility FE{yes} \\\\\n"
        "\\hline\n"
    )
    return src.replace("\\hline\nObservations", fe_block + "Observations")


def latex_wrapper(body: str, landscape: bool = False, small: bool = False) -> str:
    """Return a complete LaTeX document wrapping the table body."""
    geo = (
        "\\usepackage[landscape,margin=0.55in,top=0.5in,bottom=0.5in]{geometry}"
        if landscape
        else "\\usepackage[margin=1.1in,top=0.9in,bottom=0.8in]{geometry}"
    )
    font = "\\small" if small else ""
    return f"""\\documentclass[11pt]{{article}}
\\usepackage[T1]{{fontenc}}
\\usepackage{{lmodern}}
\\usepackage{{booktabs}}
\\usepackage{{array}}
\\usepackage{{caption}}
\\usepackage{{adjustbox}}
{geo}
\\renewcommand{{\\arraystretch}}{{1.2}}
\\begin{{document}}
\\thispagestyle{{empty}}
{font}
{body}
\\end{{document}}
"""


def compile_table(
    tex_src: Path,
    out_dir: Path,
    stem: str,
    landscape: bool = False,
    small: bool = False,
    ncols: int = 3,
) -> None:
    """Wrap, compile, and convert one table."""
    body = tex_src.read_text()
    body = strip_year_fe(body)
    body = add_fe_rows(body, ncols)

    doc  = latex_wrapper(body, landscape=landscape, small=small)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        tex_path = tmp / f"{stem}.tex"
        tex_path.write_text(doc)

        # Run pdflatex twice (for floats)
        for _ in range(2):
            result = subprocess.run(
                [PDFLATEX, "-interaction=nonstopmode", f"{stem}.tex"],
                cwd=tmp,
                capture_output=True,
                text=True,
            )

        pdf_tmp = tmp / f"{stem}.pdf"
        if not pdf_tmp.exists():
            print(f"  ✗ pdflatex failed for {stem}")
            # Print last 20 lines of log for debugging
            log = (tmp / f"{stem}.log")
            if log.exists():
                lines = log.read_text().splitlines()
                print("\n".join(lines[-20:]))
            return

        # Copy PDF
        pdf_out = out_dir / f"{stem}.pdf"
        shutil.copy(pdf_tmp, pdf_out)

        # Convert to PNG at 300 dpi
        png_base = tmp / stem
        subprocess.run(
            [PDFTOPPM, "-r", "300", "-f", "1", "-l", "1", "-png",
             str(pdf_tmp), str(png_base)],
            capture_output=True,
        )
        # pdftoppm names output as stem-1.png
        candidates = list(tmp.glob(f"{stem}*.png"))
        if candidates:
            shutil.copy(candidates[0], out_dir / f"{stem}.png")
            print(f"  ✓ {stem}.pdf + .png")
        else:
            print(f"  ✓ {stem}.pdf  (PNG conversion failed)")


# ─────────────────────────────────────────────────────────────────────────────
# PE TABLES
# ─────────────────────────────────────────────────────────────────────────────
print("\n── PE tables ──")

compile_table(
    SRC_PE / "staffing_main_total_nurse_gold_plus_silver.tex",
    OUT_PE, "pe_main_staffing",
    ncols=3,
)

compile_table(
    SRC_PE / "csdid_event_total_nurse_gold_plus_silver.tex",
    OUT_PE, "pe_csdid_event",
    ncols=3,
)

compile_table(
    SRC_PE / "staffing_medicaid_terciles_total_nurse_gold_plus_silver.tex",
    OUT_PE, "pe_medicaid_terciles",
    landscape=True, small=True, ncols=9,
)

compile_table(
    SRC_PE / "paper_medicaid_functional_form_summary_gold_plus_silver.tex",
    OUT_PE, "pe_medicaid_functional_form",
    ncols=3,
)

# ─────────────────────────────────────────────────────────────────────────────
# REIT TABLES
# ─────────────────────────────────────────────────────────────────────────────
print("\n── REIT tables ──")

compile_table(
    SRC_REIT / "reit_staffing_main_directcare.tex",
    OUT_REIT, "reit_main_directcare",
    ncols=3,
)

compile_table(
    SRC_REIT / "reit_staffing_main_rn.tex",
    OUT_REIT, "reit_main_rn",
    ncols=3,
)

compile_table(
    SRC_REIT / "reit_csdid_event_directcare.tex",
    OUT_REIT, "reit_csdid_event_directcare",
    ncols=3,
)

compile_table(
    SRC_REIT / "reit_csdid_event_rn.tex",
    OUT_REIT, "reit_csdid_event_rn",
    ncols=3,
)

compile_table(
    SRC_REIT / "reit_staffing_medicaid_terciles_directcare.tex",
    OUT_REIT, "reit_medicaid_terciles",
    landscape=True, small=True, ncols=9,
)

compile_table(
    SRC_REIT / "reit_staffing_high_low_directcare.tex",
    OUT_REIT, "reit_high_low_directcare",
    landscape=True, small=True, ncols=6,
)

print("\nDone.")
