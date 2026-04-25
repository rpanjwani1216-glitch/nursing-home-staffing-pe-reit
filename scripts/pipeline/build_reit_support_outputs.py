#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
TABLE_DIR = ROOT / "outputs" / "intermediate" / "tables" / "econometrics_reit"


PANEL_ORDER = ["National", "Same-state", "Matched"]
TERM_ORDER_EVENT = ["Tm2", "Tm1", "Tp0", "Tp1", "Tp2"]


def clean_cell(cell: str) -> str:
    cell = cell.strip()
    if cell.startswith('="') and cell.endswith('"'):
        return cell[2:-1]
    if cell.startswith('"') and cell.endswith('"'):
        return cell[1:-1]
    return cell


def parse_float(text: str | None) -> float | None:
    if not text:
        return None
    stripped = clean_cell(text).strip().strip("()").replace("*", "")
    if stripped in {"", "."}:
        return None
    try:
        return float(stripped)
    except ValueError:
        return None


def safe_col(name: str) -> str:
    safe = re.sub(r"[^0-9A-Za-z_]+", "_", name).strip("_")
    if re.match(r"^\d", safe):
        safe = f"c_{safe}"
    return safe[:30]


def write_data(df: pd.DataFrame, stem: str) -> None:
    out_csv = TABLE_DIR / f"{stem}.csv"
    out_dta = TABLE_DIR / f"{stem}.dta"
    df.to_csv(out_csv, index=False)
    dta_df = df.copy()
    dta_df.columns = [safe_col(col) for col in dta_df.columns]
    dta_df.to_stata(out_dta, write_index=False, version=118)


def parse_esttab_csv(path: Path) -> tuple[str, pd.DataFrame]:
    with path.open(newline="") as fh:
        raw_rows = [[clean_cell(cell) for cell in row] for row in csv.reader(fh)]

    rows = [row for row in raw_rows if any(cell != "" for cell in row)]
    title = rows[0][0] if rows else ""

    header_rows: list[list[str]] = []
    data_start = 1
    for idx in range(1, len(rows)):
        label = rows[idx][0]
        if label and label not in {"Standard errors in parentheses", "* p<0.10, ** p<0.05, *** p<0.01"}:
            data_start = idx
            break
        header_rows.append(rows[idx])

    column_labels: list[str] = []
    for row in reversed(header_rows):
        candidates = [cell for cell in row[1:] if cell]
        if candidates and not all(re.fullmatch(r"\(\d+\)", cell or "") for cell in candidates):
            column_labels = row[1:]
            break
    if not any(column_labels):
        n_cols = max(len(rows[data_start]) - 1, 0)
        column_labels = PANEL_ORDER[:n_cols]

    records: list[dict[str, object]] = []
    idx = data_start
    while idx < len(rows):
        row = rows[idx]
        label = row[0]
        if label in {"Observations", "Standard errors in parentheses"} or label.startswith("* p<"):
            break
        next_row = rows[idx + 1] if idx + 1 < len(rows) else None
        se_row = next_row[1:] if next_row and next_row[0] == "" else [""] * len(column_labels)
        for col, coef_text, se_text in zip(column_labels, row[1:], se_row):
            records.append(
                {
                    "term": label,
                    "column": col,
                    "coef": parse_float(coef_text),
                    "se": parse_float(se_text),
                }
            )
        idx += 2 if next_row and next_row[0] == "" else 1

    return title, pd.DataFrame.from_records(records)


def build_main_coef_plot_data() -> None:
    _, directcare = parse_esttab_csv(TABLE_DIR / "reit_staffing_main_directcare.csv")
    _, rn = parse_esttab_csv(TABLE_DIR / "reit_staffing_main_rn.csv")

    rows = []
    for outcome, df in [("Direct-care HPRD", directcare), ("RN HPRD", rn)]:
        sub = df[df["term"] == "did_treat"].copy()
        for panel in PANEL_ORDER:
            rec = sub[sub["column"] == panel].iloc[0]
            coef = rec["coef"]
            se = rec["se"]
            rows.append(
                {
                    "panel": panel,
                    "outcome": outcome,
                    "coef": coef,
                    "se": se,
                    "lb": coef - 1.96 * se if coef is not None and se is not None else None,
                    "ub": coef + 1.96 * se if coef is not None and se is not None else None,
                }
            )
    write_data(pd.DataFrame(rows), "paper_main_coef_plot_data_reit")


def build_event_plot_data() -> None:
    for stem, outstem in [
        ("reit_csdid_event_directcare.csv", "reit_csdid_event_directcare_plot_data"),
        ("reit_csdid_event_rn.csv", "reit_csdid_event_rn_plot_data"),
    ]:
        _, df = parse_esttab_csv(TABLE_DIR / stem)
        df = df[df["term"].isin(TERM_ORDER_EVENT)].copy()
        df["panel"] = df["column"]
        df["event_order"] = df["term"].map({"Tm2": 0, "Tm1": 1, "Tp0": 2, "Tp1": 3, "Tp2": 4})
        df["lb"] = df["coef"] - 1.96 * df["se"]
        df["ub"] = df["coef"] + 1.96 * df["se"]
        write_data(df[["panel", "term", "event_order", "coef", "se", "lb", "ub"]], outstem)


def main() -> None:
    build_main_coef_plot_data()
    build_event_plot_data()
    print(f"Wrote REIT support outputs to {TABLE_DIR}")


if __name__ == "__main__":
    main()
