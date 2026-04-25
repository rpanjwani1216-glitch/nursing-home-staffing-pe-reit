#!/usr/bin/env python3
"""Export Table 1 baseline balance results into presentation-ready formats."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES_DIR = ROOT / "outputs" / "tables" / "balance"

SECTION_MAP = {
    "provider_certified_beds": "Facility characteristics",
    "provider_avg_residents_per_day": "Facility characteristics",
    "chain_affiliated": "Facility characteristics",
    "for_profit": "Facility characteristics",
    "pbj_mean_rn_hprd": "Baseline operations",
    "pbj_mean_nurse_hprd": "Baseline operations",
    "provider_staffing_rating": "Baseline operations",
    "provider_health_rating": "Baseline ratings",
    "provider_overall_rating": "Baseline ratings",
    "form671_medicare_census_mean": "Payer mix and utilization",
}

SECTION_ORDER = [
    "Facility characteristics",
    "Baseline operations",
    "Baseline ratings",
    "Payer mix and utilization",
]


def fmt_num(value: float | int | None, digits: int = 3) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):.{digits}f}"


def build_formatted_rows(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for section in SECTION_ORDER:
        section_df = df[df["section"].eq(section)].copy()
        if section_df.empty:
            continue
        rows.append(
            {
                "section": section,
                "row_type": "section",
                "row_label": section,
                "control_mean": "",
                "diff_estimate": "",
                "std_diff": "",
                "n_control": "",
                "n_treated": "",
                "row_order": -1,
            }
        )
        for _, row in section_df.iterrows():
            rows.append(
                {
                    "section": section,
                    "row_type": "estimate",
                    "row_label": row["row_label"],
                    "control_mean": fmt_num(row["control_mean"]),
                    "diff_estimate": fmt_num(row["diff_estimate"]),
                    "std_diff": fmt_num(row["std_diff"]),
                    "n_control": int(row["n_control"]) if not pd.isna(row["n_control"]) else "",
                    "n_treated": int(row["n_treated"]) if not pd.isna(row["n_treated"]) else "",
                    "row_order": int(row["row_order"]),
                }
            )
            rows.append(
                {
                    "section": section,
                    "row_type": "se",
                    "row_label": "",
                    "control_mean": "",
                    "diff_estimate": f"({fmt_num(row['diff_se'])})" if not pd.isna(row["diff_se"]) else "",
                    "std_diff": "",
                    "n_control": "",
                    "n_treated": "",
                    "row_order": int(row["row_order"]),
                }
            )
    return pd.DataFrame(rows)


def build_latex(df: pd.DataFrame) -> str:
    lines = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\caption{Baseline Comparison of Treated and Control Nursing Homes}",
        r"\label{tab:baseline_balance_gold_v2}",
        r"\begin{tabular}{lccccc}",
        r"\toprule",
        r"& Control mean & Difference: treated-control & Std. diff. & $N$ control & $N$ treated \\",
        r"\midrule",
    ]

    for section in SECTION_ORDER:
        section_df = df[df["section"].eq(section)].copy()
        if section_df.empty:
            continue
        lines.append(rf"\multicolumn{{6}}{{l}}{{\textit{{{section}}}}} \\")
        for _, row in section_df.iterrows():
            lines.append(
                f"{row['row_label']} & {fmt_num(row['control_mean'])} & {fmt_num(row['diff_estimate'])} & {fmt_num(row['std_diff'])} & {int(row['n_control'])} & {int(row['n_treated'])} \\\\"
            )
            lines.append(
                f" &  & ({fmt_num(row['diff_se'])}) &  &  &  \\\\"
            )
        lines.append(r"\addlinespace")

    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\begin{minipage}{0.92\linewidth}",
            r"\footnotesize",
            r"\textit{Notes:} Control means are computed from the pseudo-cohort baseline control sample aligned to the treated cohort timing. Treated means use only pre-treatment years. Differences are estimated from facility-level regressions of each baseline characteristic on a treated indicator with robust standard errors reported in parentheses.",
            r"\end{minipage}",
            r"\end{table}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    stem = sys.argv[1] if len(sys.argv) > 1 else "table1_baseline_balance_gold_v2"
    input_csv = TABLES_DIR / f"{stem}.csv"
    formatted_csv = TABLES_DIR / f"{stem}_formatted.csv"
    formatted_dta = TABLES_DIR / f"{stem}_formatted.dta"
    latex_tex = TABLES_DIR / f"{stem}.tex"

    df = pd.read_csv(input_csv)
    df["section"] = df["variable"].map(SECTION_MAP)
    df = df.sort_values(["row_order"]).reset_index(drop=True)

    formatted = build_formatted_rows(df)
    formatted.to_csv(formatted_csv, index=False)

    safe = formatted.copy()
    for col in safe.columns:
        safe[col] = safe[col].astype(str)
    safe.to_stata(formatted_dta, write_index=False, version=118)

    latex_tex.write_text(build_latex(df), encoding="utf-8")
    print(f"Wrote {formatted_csv}")
    print(f"Wrote {formatted_dta}")
    print(f"Wrote {latex_tex}")


if __name__ == "__main__":
    main()
