#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path("/Users/rohanpanjwani/School/ECON_1430/Final_Project")
TABLE_PATH = ROOT / "outputs" / "tables" / "econometrics" / "staffing_medicaid_terciles_total_nurse_gold_plus_silver.csv"
TIDY_PATH = ROOT / "outputs" / "tables" / "econometrics" / "paper_medicaid_terciles_total_nurse_plot_data_gold_plus_silver.csv"


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

    mapping = {
        "Nat. low": ("National", "Low"),
        "Nat. mid": ("National", "Middle"),
        "Nat. high": ("National", "High"),
        "State low": ("Same-state", "Low"),
        "State mid": ("Same-state", "Middle"),
        "State high": ("Same-state", "High"),
        "Match low": ("Matched", "Low"),
        "Match mid": ("Matched", "Middle"),
        "Match high": ("Matched", "High"),
    }

    records: list[dict[str, object]] = []
    for label, coef_text, se_text in zip(labels, coefs, ses):
        panel, tercile = mapping[label]
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

    TIDY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TIDY_PATH.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["panel", "tercile", "coef", "se", "lb", "ub"])
        writer.writeheader()
        writer.writerows(records)

    print(f"Wrote {TIDY_PATH}")


if __name__ == "__main__":
    main()
