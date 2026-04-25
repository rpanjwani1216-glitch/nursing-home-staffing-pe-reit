#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path("/Users/rohanpanjwani/School/ECON_1430/Final_Project")
TABLE_DIR = ROOT / "outputs" / "tables" / "econometrics"
FIG_DIR = ROOT / "outputs" / "figures" / "econometrics"
PANEL_MAIN = ROOT / "data" / "intermediate" / "analysis" / "panels" / "regression_analysis_panel_gold_v2.dta"


PANEL_ORDER = ["National", "Same-state", "Matched"]
TERM_ORDER_PRE = ["Pre_avg", "Tm2", "Tm1"]
TERM_ORDER_EVENT = ["Pre_avg", "Post_avg", "Tm2", "Tm1", "Tp0", "Tp1", "Tp2"]
GROUP_ORDER_MEDICAID = ["Nat. high", "Nat. low", "State high", "State low", "Match high", "Match low"]
GROUP_ORDER_HOLDCO = ["Nat. holdco", "Nat. no holdco", "State holdco", "State no holdco", "Match holdco", "Match no holdco"]
STAR_EVENT_FILES = [
    ("csdid_event_health_rating.csv", "health_rating", "Health rating"),
    ("csdid_event_overall_rating.csv", "overall_rating", "Overall rating"),
    ("csdid_event_staffing_rating.csv", "staffing_rating", "Staffing rating"),
    ("csdid_event_qm_rating.csv", "qm_rating", "QM rating"),
]


def clean_cell(cell: str) -> str:
    cell = cell.strip()
    if cell.startswith('="') and cell.endswith('"'):
        return cell[2:-1]
    if cell.startswith('"') and cell.endswith('"'):
        return cell[1:-1]
    return cell


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
    if not column_labels and header_rows:
        column_labels = header_rows[-1][1:]
    if column_labels and all(re.fullmatch(r"\(\d+\)", cell or "") for cell in column_labels if cell):
        column_labels = []
    if not any(column_labels):
        n_cols = max(len(rows[data_start]) - 1, 0)
        if "by Medicaid group" in title:
            column_labels = GROUP_ORDER_MEDICAID[:n_cols]
        elif "by holdco exposure" in title:
            column_labels = GROUP_ORDER_HOLDCO[:n_cols]
        elif n_cols == 3:
            column_labels = PANEL_ORDER[:n_cols]
        else:
            column_labels = [f"col_{idx + 1}" for idx in range(n_cols)]

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
            coef_text = coef_text.strip()
            se_text = se_text.strip()
            stars = "".join(ch for ch in coef_text if ch == "*")
            coef_num = parse_float(coef_text)
            se_num = parse_float(se_text)
            p_val = two_sided_p(coef_num, se_num) if coef_num is not None and se_num not in (None, 0) else np.nan
            records.append(
                {
                    "term": label,
                    "column": col,
                    "coef_text": coef_text,
                    "se_text": se_text,
                    "coef": coef_num,
                    "se": se_num,
                    "stars": stars,
                    "p_value": p_val,
                }
            )
        idx += 2 if next_row and next_row[0] == "" else 1

    return title, pd.DataFrame.from_records(records)


def parse_float(text: str | None) -> float | None:
    if not text:
        return None
    stripped = text.strip().strip("()")
    stripped = stripped.replace("*", "")
    if stripped in {".", ""}:
        return None
    try:
        return float(stripped)
    except ValueError:
        return None


def two_sided_p(coef: float | None, se: float | None) -> float:
    if coef is None or se in (None, 0):
        return np.nan
    z = abs(coef / se)
    return math.erfc(z / math.sqrt(2.0))


def format_estimate(coef: float | None, se: float | None, stars: str = "", decimals: int = 3) -> str:
    if coef is None:
        return ""
    coef_fmt = f"{coef:.{decimals}f}{stars}"
    if se is None:
        return coef_fmt
    return f"{coef_fmt} ({se:.{decimals}f})"


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


def write_table(df: pd.DataFrame, stem: str, caption: str | None = None) -> None:
    out_tex = TABLE_DIR / f"{stem}.tex"
    write_data(df, stem)
    latex = df.to_latex(index=False, escape=False, caption=caption)
    out_tex.write_text(latex)


def build_overall_pretrend_summary() -> None:
    mappings = {
        "RN HPRD": parse_esttab_csv(TABLE_DIR / "csdid_event_rn.csv")[1],
        "Total nurse HPRD": parse_esttab_csv(TABLE_DIR / "csdid_event_total_nurse.csv")[1],
    }
    rows = []
    for outcome, df in mappings.items():
        sub = df[df["term"].isin(TERM_ORDER_PRE)].copy()
        for term in TERM_ORDER_PRE:
            row = {"Outcome": outcome, "Term": term}
            term_df = sub[sub["term"] == term]
            for panel in PANEL_ORDER:
                panel_df = term_df[term_df["column"] == panel]
                if panel_df.empty:
                    row[panel] = ""
                    row[f"{panel}_p"] = np.nan
                else:
                    obs = panel_df.iloc[0]
                    row[panel] = format_estimate(obs["coef"], obs["se"], obs["stars"])
                    row[f"{panel}_p"] = obs["p_value"]
            rows.append(row)
    table_df = pd.DataFrame(rows)
    write_table(table_df, "paper_pretrend_summary", "Pre-treatment event-study summary")


def build_overall_event_plot_data() -> None:
    for stem, out_stem in [
        ("csdid_event_total_nurse.csv", "csdid_event_total_nurse_plot_data"),
        ("csdid_event_rn.csv", "csdid_event_rn_plot_data"),
    ]:
        _, df = parse_esttab_csv(TABLE_DIR / stem)
        df = df[df["term"].isin(TERM_ORDER_EVENT)].copy()
        df["panel"] = df["column"]
        df["event_order"] = df["term"].map(
            {"Tm2": 0, "Tm1": 1, "Pre_avg": 2, "Tp0": 3, "Post_avg": 4, "Tp1": 5, "Tp2": 6}
        )
        df["lb"] = df["coef"] - 1.96 * df["se"]
        df["ub"] = df["coef"] + 1.96 * df["se"]
        write_data(df[["panel", "term", "event_order", "coef", "se", "lb", "ub"]], out_stem)


def build_star_pretrend_summary() -> None:
    rows = []
    for filename, _, outcome_label in STAR_EVENT_FILES:
        _, df = parse_esttab_csv(TABLE_DIR / filename)
        sub = df[df["term"].isin(TERM_ORDER_PRE)].copy()
        for term in TERM_ORDER_PRE:
            row = {"Outcome": outcome_label, "Term": term}
            term_df = sub[sub["term"] == term]
            for panel in PANEL_ORDER:
                panel_df = term_df[term_df["column"] == panel]
                if panel_df.empty:
                    row[panel] = ""
                    row[f"{panel}_p"] = np.nan
                else:
                    obs = panel_df.iloc[0]
                    row[panel] = format_estimate(obs["coef"], obs["se"], obs["stars"])
                    row[f"{panel}_p"] = obs["p_value"]
            rows.append(row)
    table_df = pd.DataFrame(rows)
    write_table(table_df, "paper_star_pretrend_summary", "Pre-treatment event-study summary: star ratings")


def build_star_event_plot_data() -> None:
    for filename, stem, _ in STAR_EVENT_FILES:
        _, df = parse_esttab_csv(TABLE_DIR / filename)
        df = df[df["term"].isin(TERM_ORDER_EVENT)].copy()
        df["panel"] = df["column"]
        df["event_order"] = df["term"].map(
            {"Tm2": 0, "Tm1": 1, "Pre_avg": 2, "Tp0": 3, "Post_avg": 4, "Tp1": 5, "Tp2": 6}
        )
        df["lb"] = df["coef"] - 1.96 * df["se"]
        df["ub"] = df["coef"] + 1.96 * df["se"]
        write_data(df[["panel", "term", "event_order", "coef", "se", "lb", "ub"]], f"csdid_event_{stem}_plot_data")


def build_leave_one_deal_table() -> None:
    loo = pd.read_stata(TABLE_DIR / "leave_one_deal_out_raw.dta")
    baseline = pd.read_stata(TABLE_DIR / "paper_main_coef_plot_data.dta")
    total = loo[loo["outcome"] == "Total nurse HPRD"].copy()
    row_order = ["All deals"] + [f"Exclude {deal} ({n} homes)" for deal, n in total[["omitted_deal", "omitted_facilities"]].drop_duplicates().sort_values("omitted_deal").itertuples(index=False)]
    rows = []
    base_lookup = baseline[baseline["outcome"] == "Total nurse HPRD"].set_index("panel")
    rows.append(
        {
            "Specification": "All deals",
            "National": format_estimate(base_lookup.loc["National", "coef"], base_lookup.loc["National", "se"]),
            "Same_state": format_estimate(base_lookup.loc["Same-state", "coef"], base_lookup.loc["Same-state", "se"]),
            "Matched": format_estimate(base_lookup.loc["Matched", "coef"], base_lookup.loc["Matched", "se"]),
            "Treated_facilities_left": 31,
        }
    )
    for deal, n_homes in total[["omitted_deal", "omitted_facilities"]].drop_duplicates().sort_values("omitted_deal").itertuples(index=False):
        sub = total[total["omitted_deal"] == deal].set_index("panel")
        rows.append(
            {
                "Specification": f"Exclude {deal} ({n_homes} homes)",
                "National": format_estimate(sub.loc["National", "coef"], sub.loc["National", "se"]),
                "Same_state": format_estimate(sub.loc["Same-state", "coef"], sub.loc["Same-state", "se"]),
                "Matched": format_estimate(sub.loc["Matched", "coef"], sub.loc["Matched", "se"]),
                "Treated_facilities_left": int(sub.loc["National", "treated_facilities_left"]),
            }
        )
    table_df = pd.DataFrame(rows)
    table_df["Specification"] = pd.Categorical(table_df["Specification"], categories=row_order, ordered=True)
    table_df = table_df.sort_values("Specification").reset_index(drop=True)
    write_table(table_df, "paper_leave_one_deal_out_total_nurse", "Leave-one-deal-out robustness: total nurse staffing")


def build_medicaid_pretrend_summary() -> None:
    _, df = parse_esttab_csv(TABLE_DIR / "csdid_event_total_nurse_high_low.csv")
    df = df[df["term"].isin(TERM_ORDER_PRE)].copy()
    col_order = GROUP_ORDER_MEDICAID
    rows = []
    for term in TERM_ORDER_PRE:
        row = {"Term": term}
        term_df = df[df["term"] == term]
        for col in col_order:
            obs = term_df[term_df["column"] == col].iloc[0]
            row[safe_col(col)] = format_estimate(obs["coef"], obs["se"], obs["stars"])
            row[f"{safe_col(col)}_p"] = obs["p_value"]
        rows.append(row)
    table_df = pd.DataFrame(rows)
    write_table(table_df, "paper_medicaid_pretrend_summary", "Medicaid-group pretrend diagnostics")


def build_medicaid_pretrend_plot_data() -> None:
    _, df = parse_esttab_csv(TABLE_DIR / "csdid_event_total_nurse_high_low.csv")
    df = df[df["term"].isin(TERM_ORDER_PRE)].copy()
    df["panel"] = df["column"].str.extract(r"^(Nat\.|State|Match)")[0].replace({"Nat.": "National", "State": "Same-state", "Match": "Matched"})
    df["group"] = np.where(df["column"].str.contains("high"), "High Medicaid", "Low Medicaid")
    df["term_order"] = df["term"].map({"Tm2": 0, "Tm1": 1, "Pre_avg": 2})
    df["lb"] = df["coef"] - 1.96 * df["se"]
    df["ub"] = df["coef"] + 1.96 * df["se"]
    write_data(df[["panel", "group", "term", "term_order", "coef", "se", "lb", "ub"]], "paper_medicaid_pretrend_plot_data")


def build_medicaid_functional_form_summary() -> None:
    _, cont = parse_esttab_csv(TABLE_DIR / "staffing_heterogeneity_total_nurse.csv")
    _, split = parse_esttab_csv(TABLE_DIR / "staffing_high_low_total_nurse.csv")
    _, terc = parse_esttab_csv(TABLE_DIR / "staffing_medicaid_terciles_total_nurse.csv")

    rows = []
    cont_map = {
        "National": "pbj_mean_nurse_hprd",
        "Same-state": "pbj_mean_nurse_hprd",
        "Matched": "pbj_mean_nurse_hprd",
    }
    cont_panels = list(PANEL_ORDER)
    cont_term = "did_treat # baseline_medicaid_centered"
    cont_df = cont[cont["term"] == cont_term].reset_index(drop=True)
    rows.append(
        {
            "Specification": "Continuous interaction",
            "National": format_estimate(cont_df.iloc[0]["coef"], cont_df.iloc[0]["se"], cont_df.iloc[0]["stars"]),
            "Same_state": format_estimate(cont_df.iloc[1]["coef"], cont_df.iloc[1]["se"], cont_df.iloc[1]["stars"]),
            "Matched": format_estimate(cont_df.iloc[2]["coef"], cont_df.iloc[2]["se"], cont_df.iloc[2]["stars"]),
        }
    )

    split_cols = [("Nat. high", "Median split: high"), ("Nat. low", "Median split: low"), ("State high", "Median split: high"), ("State low", "Median split: low"), ("Match high", "Median split: high"), ("Match low", "Median split: low")]
    split_df = split[split["term"] == "did_treat"].copy()
    for label in ["Median split: low", "Median split: high"]:
        row = {"Specification": label, "National": "", "Same_state": "", "Matched": ""}
        mapping = {
            "National": "Nat. low" if label.endswith("low") else "Nat. high",
            "Same_state": "State low" if label.endswith("low") else "State high",
            "Matched": "Match low" if label.endswith("low") else "Match high",
        }
        for panel_key, col in mapping.items():
            obs = split_df[split_df["column"] == col].iloc[0]
            row[panel_key] = format_estimate(obs["coef"], obs["se"], obs["stars"])
        rows.append(row)

    terc_df = terc[terc["term"] == "did_treat"].copy()
    for tercile, suffix in [("low", "Tercile 1"), ("mid", "Tercile 2"), ("high", "Tercile 3")]:
        row = {"Specification": suffix, "National": "", "Same_state": "", "Matched": ""}
        mapping = {
            "National": f"Nat. {tercile}",
            "Same_state": f"State {tercile}",
            "Matched": f"Match {tercile}",
        }
        for panel_key, col in mapping.items():
            obs = terc_df[terc_df["column"] == col].iloc[0]
            row[panel_key] = format_estimate(obs["coef"], obs["se"], obs["stars"])
        rows.append(row)

    table_df = pd.DataFrame(rows)
    write_table(table_df, "paper_medicaid_functional_form_summary", "Functional-form checks for Medicaid heterogeneity")


def build_medicaid_descriptive_scatter_data() -> None:
    cols = [
        "ccn_str",
        "analysis_facility_name",
        "analysis_state",
        "ever_treated",
        "baseline_medicaid_share",
        "event_time",
        "pbj_mean_nurse_hprd",
        "sample_main_staffing",
    ]
    df = pd.read_stata(PANEL_MAIN, columns=cols)
    treated = df[(df["ever_treated"] == 1) & (df["sample_main_staffing"] == 1)].copy()
    treated = treated.dropna(subset=["baseline_medicaid_share", "event_time", "pbj_mean_nurse_hprd"])
    pre = treated[treated["event_time"].isin([-2, -1])].groupby(["ccn_str", "analysis_facility_name", "analysis_state", "baseline_medicaid_share"], as_index=False)["pbj_mean_nurse_hprd"].mean().rename(columns={"pbj_mean_nurse_hprd": "pre_avg"})
    post = treated[treated["event_time"].isin([0, 1, 2])].groupby(["ccn_str", "analysis_facility_name", "analysis_state", "baseline_medicaid_share"], as_index=False)["pbj_mean_nurse_hprd"].mean().rename(columns={"pbj_mean_nurse_hprd": "post_avg"})
    plot_df = pre.merge(post, on=["ccn_str", "analysis_facility_name", "analysis_state", "baseline_medicaid_share"], how="inner")
    plot_df["post_minus_pre"] = plot_df["post_avg"] - plot_df["pre_avg"]
    plot_df["label"] = plot_df["analysis_facility_name"] + " (" + plot_df["analysis_state"] + ")"

    plot_df["label_flag"] = 0
    annotate = pd.concat([plot_df.nsmallest(3, "baseline_medicaid_share"), plot_df.nlargest(3, "baseline_medicaid_share")]).drop_duplicates("ccn_str")
    plot_df.loc[plot_df["ccn_str"].isin(annotate["ccn_str"]), "label_flag"] = 1
    write_data(plot_df, "paper_baseline_medicaid_vs_staffing_change_data")


def build_holdco_coef_plot_data() -> None:
    _, df = parse_esttab_csv(TABLE_DIR / "mechanism_holdco_interaction.csv")
    df = df[df["term"].isin(["holdco_transition", "high_medicaid=1 # holdco_transition"])].copy()
    term_map = {
        "holdco_transition": "HoldCo transition",
        "high_medicaid=1 # holdco_transition": "High Medicaid × HoldCo",
    }
    df["term_label"] = df["term"].map(term_map)
    df["lb"] = df["coef"] - 1.96 * df["se"]
    df["ub"] = df["coef"] + 1.96 * df["se"]
    write_data(df[["column", "term_label", "coef", "se", "lb", "ub"]], "paper_holdco_coef_plot_data")


def build_slack_support_plot_data() -> None:
    supports = []
    for panel_name, stem in [("National", "nat"), ("Same-state", "state"), ("Matched", "match")]:
        df = pd.read_stata(TABLE_DIR / f"mechanism_support_{stem}.dta")
        df["panel"] = panel_name
        supports.append(df)
    support = pd.concat(supports, ignore_index=True)
    support["slack_label"] = support["slack_group"].map({1: "Least slack", 2: "Low/Low", 3: "High/High", 4: "Most slack"})
    support["cell_label"] = (
        "Treated: "
        + support["treated_facility"].astype(int).astype(str)
        + " | All: "
        + support["facility_count"].astype(int).astype(str)
    )
    write_data(
        support[
            [
                "panel",
                "high_medicare",
                "high_medicaid",
                "slack_group",
                "slack_label",
                "facility_count",
                "treated_facility",
                "holdco_transition",
                "cell_label",
            ]
        ],
        "paper_slack_support_plot_data",
    )


def build_holdco_csdid_summary() -> None:
    _, df = parse_esttab_csv(TABLE_DIR / "csdid_event_total_nurse_holdco_groups.csv")
    df = df[df["term"].isin(TERM_ORDER_EVENT)].copy()
    rows = []
    for term in TERM_ORDER_EVENT:
        row = {"Term": term}
        term_df = df[df["term"] == term]
        for col in GROUP_ORDER_HOLDCO:
            obs = term_df[term_df["column"] == col].iloc[0]
            row[safe_col(col)] = format_estimate(obs["coef"], obs["se"], obs["stars"])
            row[f"{safe_col(col)}_p"] = obs["p_value"]
        rows.append(row)
    table_df = pd.DataFrame(rows)
    write_table(table_df, "paper_holdco_csdid_summary", "Exploratory staggered DID by holdco exposure")


def build_holdco_event_plot_data() -> None:
    _, df = parse_esttab_csv(TABLE_DIR / "csdid_event_total_nurse_holdco_groups.csv")
    df = df[df["term"].isin(["Tm2", "Tm1", "Tp0", "Tp1", "Tp2"])].copy()
    df["panel"] = df["column"].str.extract(r"^(Nat\.|State|Match)")[0].replace({"Nat.": "National", "State": "Same-state", "Match": "Matched"})
    df["group"] = np.where(df["column"].str.contains("no holdco"), "No HoldCo", "HoldCo")
    df["event_order"] = df["term"].map({"Tm2": 0, "Tm1": 1, "Tp0": 2, "Tp1": 3, "Tp2": 4})
    df["lb"] = df["coef"] - 1.96 * df["se"]
    df["ub"] = df["coef"] + 1.96 * df["se"]
    write_data(df[["panel", "group", "term", "event_order", "coef", "se", "lb", "ub"]], "paper_holdco_event_plot_data")


def main() -> None:
    build_overall_event_plot_data()
    build_overall_pretrend_summary()
    if (TABLE_DIR / "paper_star_main_coef_plot_data.dta").exists():
        build_star_pretrend_summary()
        build_star_event_plot_data()
    build_leave_one_deal_table()
    build_medicaid_pretrend_summary()
    build_medicaid_pretrend_plot_data()
    build_medicaid_functional_form_summary()
    build_medicaid_descriptive_scatter_data()
    build_holdco_coef_plot_data()
    build_slack_support_plot_data()
    build_holdco_csdid_summary()
    build_holdco_event_plot_data()
    print("Paper-support outputs written to:")
    print(TABLE_DIR)
    print(FIG_DIR)


if __name__ == "__main__":
    main()
