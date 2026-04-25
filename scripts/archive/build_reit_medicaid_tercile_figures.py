#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from utils import export_csv_and_dta


ROOT = Path("/Users/rohanpanjwani/School/ECON_1430/Final_Project")
TABLE_PATH = ROOT / "outputs" / "tables" / "econometrics_reit" / "reit_staffing_medicaid_terciles_directcare.csv"
TIDY_CSV = ROOT / "outputs" / "tables" / "econometrics_reit" / "paper_medicaid_terciles_directcare_reit_plot_data.csv"
TIDY_DTA = ROOT / "outputs" / "tables" / "econometrics_reit" / "paper_medicaid_terciles_directcare_reit_plot_data.dta"


def clean_cell(cell: str) -> str:
    cell = cell.strip()
    if cell.startswith('="') and cell.endswith('"'):
        return cell[2:-1]
    if cell.startswith('"') and cell.endswith('"'):
        return cell[1:-1]
    return cell


def parse_float(text: str) -> float | None:
    text = clean_cell(text).replace("*", "").strip().strip("()")
    if text in {"", "."}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def main() -> None:
    with TABLE_PATH.open(newline="") as fh:
        rows = [[clean_cell(c) for c in row] for row in csv.reader(fh)]

    rows = [row for row in rows if any(cell != "" for cell in row)]
    labels = rows[2][1:]
    coefs = rows[3][1:]
    ses = rows[4][1:]
    mapping_by_position = [
        ("National", "Low"),
        ("National", "Middle"),
        ("National", "High"),
        ("Same-state", "Low"),
        ("Same-state", "Middle"),
        ("Same-state", "High"),
        ("Matched", "Low"),
        ("Matched", "Middle"),
        ("Matched", "High"),
    ]

    records: list[dict[str, object]] = []
    for idx, (label, coef_text, se_text) in enumerate(zip(labels, coefs, ses)):
        panel, tercile = mapping_by_position[idx]
        coef = parse_float(coef_text)
        se = parse_float(se_text)
        lb = coef - 1.96 * se if coef is not None and se is not None else None
        ub = coef + 1.96 * se if coef is not None and se is not None else None
        records.append(
            {
                "panel": panel,
                "tercile": tercile,
                "coef": coef,
                "se": se,
                "lb": lb,
                "ub": ub,
            }
        )

    df = pd.DataFrame(records)
    export_csv_and_dta(df, TIDY_CSV, TIDY_DTA)
    print(f"Wrote {TIDY_CSV} and {TIDY_DTA}")


if __name__ == "__main__":
    main()
