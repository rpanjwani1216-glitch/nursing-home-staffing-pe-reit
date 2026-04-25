#!/usr/bin/env python3
"""Build cleaned LTCFocus intermediates and Medicaid baseline inputs.

This script preserves the raw annual LTCFocus workbooks in data/raw/ltcfocus
and writes cleaned, analysis-ready outputs to data/intermediate/ltcfocus.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from pandas.api.types import is_object_dtype, is_string_dtype


import sys
sys.path.insert(0, str(Path(__file__).parent))
from utils import get_intermediate_dir, get_output_dir

ROOT = Path(__file__).resolve().parents[2]
RAW_LTCFOCUS_DIR = ROOT / "data" / "raw" / "ltcfocus"
INTERMEDIATE_DIR = get_intermediate_dir(ROOT) / "ltcfocus"
CMS_INTERMEDIATE_DIR = get_intermediate_dir(ROOT) / "cms"
RESEARCH_DIR = ROOT / "research"
OUTPUTS_QA_DIR = get_output_dir(ROOT) / "qa"

TREATMENT_PATH = RESEARCH_DIR / "pe_facility_verification.csv"
CONTROL_V2_PATH = CMS_INTERMEDIATE_DIR / "clean_control_candidates_v2.csv"

FULL_OUTPUT_CSV = INTERMEDIATE_DIR / "ltcfocus_facility_year_full.csv"
FULL_OUTPUT_DTA = INTERMEDIATE_DIR / "ltcfocus_facility_year_full.dta"
SLIM_OUTPUT_CSV = INTERMEDIATE_DIR / "ltcfocus_medicaid_analysis.csv"
SLIM_OUTPUT_DTA = INTERMEDIATE_DIR / "ltcfocus_medicaid_analysis.dta"
BASELINE_OUTPUT_CSV = INTERMEDIATE_DIR / "ltcfocus_medicaid_baseline_inputs.csv"
BASELINE_OUTPUT_DTA = INTERMEDIATE_DIR / "ltcfocus_medicaid_baseline_inputs.dta"
README_PATH = INTERMEDIATE_DIR / "README.md"

INVENTORY_PATH = OUTPUTS_QA_DIR / "ltcfocus_source_inventory.csv"
BUILD_SUMMARY_PATH = OUTPUTS_QA_DIR / "ltcfocus_build_summary.json"
COVERAGE_GOLD_PATH = OUTPUTS_QA_DIR / "ltcfocus_coverage_gold_main_by_year.csv"
COVERAGE_EXPANDED_PATH = OUTPUTS_QA_DIR / "ltcfocus_coverage_gold_plus_silver_by_year.csv"
COVERAGE_CONTROLS_PATH = OUTPUTS_QA_DIR / "ltcfocus_coverage_control_v2_by_year.csv"
UNMATCHED_GOLD_PATH = OUTPUTS_QA_DIR / "ltcfocus_unmatched_gold_main.csv"
UNMATCHED_EXPANDED_PATH = OUTPUTS_QA_DIR / "ltcfocus_unmatched_gold_plus_silver.csv"
UNMATCHED_CONTROLS_PATH = OUTPUTS_QA_DIR / "ltcfocus_unmatched_control_v2.csv"
YEARS_PER_FACILITY_PATH = OUTPUTS_QA_DIR / "ltcfocus_years_of_coverage_by_sample.csv"
COHORT_WEIGHTS_PATH = OUTPUTS_QA_DIR / "ltcfocus_control_pseudocohort_weights.csv"
DUPLICATE_CCN_YEAR_PATH = OUTPUTS_QA_DIR / "ltcfocus_duplicate_ccn_year.csv"
BASELINE_GOLD_INSUFFICIENT_PATH = OUTPUTS_QA_DIR / "ltcfocus_baseline_gold_main_insufficient.csv"
BASELINE_EXPANDED_INSUFFICIENT_PATH = OUTPUTS_QA_DIR / "ltcfocus_baseline_gold_plus_silver_insufficient.csv"

EXPECTED_FILENAMES = [
    "facil2009new.xls",
    "facil2010new.xls",
    "facility_2011.xls",
    "facility_2012.xls",
    "facility_2013.xls",
    "facility_2014.xls",
    "facility_2015.xls",
    "facility_2016.xls",
    "facility_2017.xls",
    "facility_2018.xls",
    "facility_2019.xls",
    "facility_2020.xls",
    "facility_2021.xls",
    "facility_2022.xlsx",
    "facility_2023_A.xlsx",
]

TEXT_COLUMNS = {
    "PROV0475",
    "PROV2720",
    "PROV3225",
    "state",
    "alzunit",
    "anyunit",
    "multifac",
    "profit",
    "hospbase",
    "anymdex_pbj",
    "agglocare_imp",
    "agg_comm",
    "agghighcfs",
    "agghisp_mds3",
    "aggblack_mds3",
    "agg_u65",
    "pctlocare_imp",
    "pctblack_mds3",
    "pcthisp_mds3",
    "pctunder65",
    "pcthighcfs",
    "pctbedft_mds3",
    "pctwalking",
    "pctcath_mds3",
    "pctchf",
    "pctschiz_bipol",
    "pctuti",
    "pctfall30_mds3",
    "pctobese",
    "pcthmo",
}

PLACEHOLDER_VALUES = {"", ".", ". ", " .", "  .", "   .", "LNE", "N/A", "NA"}

COLUMN_CANONICAL_MAP = {
    "prov1680": "PROV1680",
    "prov0475": "PROV0475",
    "prov2720": "PROV2720",
    "prov3225": "PROV3225",
    "prov2905": "PROV2905",
}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def canonical_ccn(value: object) -> str | None:
    if pd.isna(value):
        return None
    raw = str(value).strip()
    if not re.fullmatch(r"\d{1,6}", raw):
        return None
    digits = raw.zfill(6)[-6:]
    if digits == "000000":
        return None
    return digits


def parse_year_from_name(path: Path) -> int:
    match = re.search(r"(20\d{2})", path.name)
    if not match:
        raise ValueError(f"Could not parse year from {path.name}")
    return int(match.group(1))


def clean_string_series(series: pd.Series) -> pd.Series:
    cleaned = series.astype("string").str.strip()
    cleaned = cleaned.replace(list(PLACEHOLDER_VALUES), pd.NA)
    cleaned = cleaned.replace(r"^\.+$", pd.NA, regex=True)
    cleaned = cleaned.replace(r"^\s+$", pd.NA, regex=True)
    return cleaned


def maybe_numeric(series: pd.Series) -> pd.Series:
    if series.name in TEXT_COLUMNS:
        return series
    coerced = pd.to_numeric(series, errors="coerce")
    if int(coerced.notna().sum() + series.isna().sum()) == int(len(series)):
        return coerced
    return series


def read_ltcfocus_file(path: Path) -> pd.DataFrame:
    engine = "xlrd" if path.suffix.lower() == ".xls" else "openpyxl"
    df = pd.read_excel(path, dtype=str, engine=engine)
    df.columns = [
        COLUMN_CANONICAL_MAP.get(str(col).strip().lower(), str(col).strip())
        for col in df.columns
    ]

    for col in df.columns:
        df[col] = clean_string_series(df[col])

    for col in df.columns:
        df[col] = maybe_numeric(df[col])

    source_year = parse_year_from_name(path)
    if "year" not in df.columns:
        df["year"] = source_year
    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(source_year).astype(int)
    df["source_file"] = path.name
    df["source_file_year"] = source_year
    df["ccn_str"] = df["PROV1680"].map(canonical_ccn).astype("string")
    df["facility_name_ltcfocus"] = clean_string_series(df["PROV0475"]).astype("string")
    df["state"] = clean_string_series(df["state"]).str.upper().astype("string")
    return df


def yes_no_to_binary(series: pd.Series) -> pd.Series:
    mapped = (
        clean_string_series(series)
        .str.lower()
        .map({"yes": 1, "no": 0})
        .astype("Int64")
    )
    return mapped


def build_slim_panel(full_df: pd.DataFrame) -> pd.DataFrame:
    slim = pd.DataFrame(
        {
            "ccn_str": full_df["ccn_str"].astype("string"),
            "year": pd.to_numeric(full_df["year"], errors="coerce").astype("Int64"),
            "facility_name_ltcfocus": full_df["facility_name_ltcfocus"].astype("string"),
            "state": full_df["state"].astype("string"),
            "ltcfocus_medicaid_share": pd.to_numeric(full_df["paymcaid"], errors="coerce"),
            "ltcfocus_medicare_share": pd.to_numeric(full_df["paymcare"], errors="coerce"),
            "ltcfocus_for_profit": yes_no_to_binary(full_df["profit"]),
            "ltcfocus_multifacility": yes_no_to_binary(full_df["multifac"]),
            "ltcfocus_total_beds": pd.to_numeric(full_df["totbeds"], errors="coerce"),
            "ltcfocus_residents": pd.to_numeric(full_df["nresid"], errors="coerce"),
            "ltcfocus_avg_dailycensus": pd.to_numeric(full_df["avg_dailycensus"], errors="coerce"),
            "ltcfocus_avgadl_mds3": pd.to_numeric(full_df["avgadl_mds3"], errors="coerce"),
            "ltcfocus_obs_rehosprate": pd.to_numeric(full_df["obs_rehosprate"], errors="coerce"),
            "ltcfocus_adj_rehosprate": pd.to_numeric(full_df["adj_rehosprate"], errors="coerce"),
            "ltcfocus_obs_successfuldc": pd.to_numeric(full_df["obs_successfuldc"], errors="coerce"),
            "ltcfocus_adj_successfuldc": pd.to_numeric(full_df["adj_successfuldc"], errors="coerce"),
            "source_file": full_df["source_file"].astype("string"),
            "source_file_year": pd.to_numeric(full_df["source_file_year"], errors="coerce").astype("Int64"),
        }
    )
    slim = slim.dropna(subset=["ccn_str", "year"]).copy()
    return slim.sort_values(["ccn_str", "year"]).reset_index(drop=True)


def load_treatment() -> pd.DataFrame:
    df = pd.read_csv(TREATMENT_PATH, dtype="string").fillna(pd.NA)
    df["ccn_str"] = df["ccn"].map(canonical_ccn).astype("string")
    df["treat_year"] = (
        df["ownership_effective_date"]
        .astype("string")
        .str.extract(r"(20\d{2})", expand=False)
        .astype("Int64")
    )
    df = df[df["ccn_str"].notna()].copy()
    return df


def load_control_v2() -> pd.DataFrame:
    df = pd.read_csv(CONTROL_V2_PATH, dtype="string").fillna(pd.NA)
    df["ccn_str"] = df["ccn_str"].map(canonical_ccn).astype("string")
    df = df[df["ccn_str"].notna()].copy()
    return df


def build_coverage_by_year(ccns: pd.Series, slim_df: pd.DataFrame, sample_name: str) -> pd.DataFrame:
    unique_ccns = sorted(set(ccns.dropna().astype(str)))
    rows = []
    for year in range(int(slim_df["year"].min()), int(slim_df["year"].max()) + 1):
        matched = slim_df.loc[slim_df["year"].eq(year) & slim_df["ccn_str"].isin(unique_ccns), "ccn_str"].nunique()
        rows.append(
            {
                "sample_group": sample_name,
                "year": year,
                "facilities_in_group": len(unique_ccns),
                "matched_facilities": int(matched),
                "match_rate": float(matched / len(unique_ccns)) if unique_ccns else 0.0,
            }
        )
    return pd.DataFrame(rows)


def build_unmatched(ccns: pd.Series, slim_df: pd.DataFrame, sample_name: str, facility_info: pd.DataFrame) -> pd.DataFrame:
    ltcfocus_ccns = set(slim_df["ccn_str"].dropna().astype(str))
    sample = facility_info.copy()
    sample["ccn_str"] = sample["ccn_str"].astype("string")
    sample = sample[sample["ccn_str"].isin(set(ccns.dropna().astype(str)))]
    unmatched = sample[~sample["ccn_str"].isin(ltcfocus_ccns)].copy()
    unmatched.insert(0, "sample_group", sample_name)
    return unmatched.sort_values(["state", "facility_name", "ccn_str"])


def build_year_coverage_distribution(groups: list[tuple[str, pd.DataFrame]], slim_df: pd.DataFrame) -> pd.DataFrame:
    years_per_ccn = (
        slim_df.groupby("ccn_str", as_index=False)
        .agg(years_with_ltcfocus=("year", "nunique"))
    )
    rows = []
    for sample_name, group_df in groups:
        work = group_df.copy()
        work["ccn_str"] = work["ccn_str"].astype("string")
        merged = work.merge(years_per_ccn, on="ccn_str", how="left")
        merged["years_with_ltcfocus"] = merged["years_with_ltcfocus"].fillna(0).astype(int)
        dist = (
            merged.groupby("years_with_ltcfocus", as_index=False)
            .size()
            .rename(columns={"size": "facility_count"})
        )
        dist.insert(0, "sample_group", sample_name)
        rows.append(dist)
    return pd.concat(rows, ignore_index=True)


def compute_treated_baseline(slim_df: pd.DataFrame, treated_df: pd.DataFrame, baseline_spec: str) -> pd.DataFrame:
    treated_work = treated_df[["ccn_str", "facility_name", "state", "analysis_sample", "treat_year"]].rename(
        columns={"state": "treat_state"}
    )
    merged = slim_df.merge(
        treated_work,
        on="ccn_str",
        how="inner",
    )
    pre = merged[merged["year"] < merged["treat_year"]].copy()
    if pre.empty:
        return pd.DataFrame()
    out = (
        pre.groupby(["ccn_str", "facility_name", "treat_state", "analysis_sample", "treat_year"], as_index=False)
        .agg(
            baseline_medicaid_share=("ltcfocus_medicaid_share", "mean"),
            baseline_medicaid_n_years=("ltcfocus_medicaid_share", "count"),
            baseline_medicare_share=("ltcfocus_medicare_share", "mean"),
            baseline_medicare_n_years=("ltcfocus_medicare_share", "count"),
            baseline_avgadl_mds3=("ltcfocus_avgadl_mds3", "mean"),
            baseline_avgadl_mds3_n_years=("ltcfocus_avgadl_mds3", "count"),
            baseline_window_start=("year", "min"),
            baseline_window_end=("year", "max"),
        )
    )
    out = out[out["baseline_medicaid_n_years"] >= 2].copy()
    out = out.rename(columns={"treat_state": "state"})
    out["baseline_spec"] = baseline_spec
    out["sample_role"] = "treated"
    out["baseline_method"] = "treated_all_preyears"
    out["valid_pseudocohorts"] = pd.NA
    return out


def compute_control_baseline(
    slim_df: pd.DataFrame,
    control_df: pd.DataFrame,
    treated_df: pd.DataFrame,
    baseline_spec: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    treated_weights = (
        treated_df.groupby("treat_year", as_index=False)
        .size()
        .rename(columns={"size": "treated_count", "treat_year": "cohort_year"})
    )
    treated_weights["cohort_weight"] = treated_weights["treated_count"] / treated_weights["treated_count"].sum()

    controls = control_df[["ccn_str", "provider_name_latest", "state_latest"]].copy()
    controls["key"] = 1
    weights = treated_weights.copy()
    weights["key"] = 1
    control_ltcfocus = slim_df[["ccn_str", "year", "ltcfocus_medicaid_share", "ltcfocus_medicare_share"]].copy()
    control_ltcfocus["ltcfocus_avgadl_mds3"] = slim_df["ltcfocus_avgadl_mds3"]
    control_ltcfocus = control_ltcfocus.merge(controls, on="ccn_str", how="inner")
    expanded = control_ltcfocus.merge(weights, on="key", how="inner")
    expanded = expanded[expanded["year"] < expanded["cohort_year"]].copy()
    if expanded.empty:
        return pd.DataFrame(), treated_weights.assign(baseline_spec=baseline_spec)

    by_cohort = (
        expanded.groupby(
            ["ccn_str", "provider_name_latest", "state_latest", "cohort_year", "cohort_weight"],
            as_index=False,
        )
        .agg(
            cohort_baseline_share=("ltcfocus_medicaid_share", "mean"),
            cohort_n_years=("ltcfocus_medicaid_share", "count"),
            cohort_medicare_share=("ltcfocus_medicare_share", "mean"),
            cohort_medicare_n_years=("ltcfocus_medicare_share", "count"),
            cohort_avgadl_mds3=("ltcfocus_avgadl_mds3", "mean"),
            cohort_avgadl_mds3_n_years=("ltcfocus_avgadl_mds3", "count"),
            cohort_window_start=("year", "min"),
            cohort_window_end=("year", "max"),
        )
    )
    by_cohort = by_cohort[by_cohort["cohort_n_years"] >= 2].copy()
    if by_cohort.empty:
        return pd.DataFrame(), treated_weights.assign(baseline_spec=baseline_spec)

    valid_weight_total = by_cohort.groupby("ccn_str")["cohort_weight"].transform("sum")
    by_cohort["normalized_weight"] = by_cohort["cohort_weight"] / valid_weight_total
    by_cohort["weighted_baseline_share"] = by_cohort["normalized_weight"] * by_cohort["cohort_baseline_share"]
    by_cohort["weighted_baseline_medicare"] = by_cohort["normalized_weight"] * by_cohort["cohort_medicare_share"]
    by_cohort["weighted_baseline_avgadl_mds3"] = by_cohort["normalized_weight"] * by_cohort["cohort_avgadl_mds3"]

    out = (
        by_cohort.groupby(["ccn_str", "provider_name_latest", "state_latest"], as_index=False)
        .agg(
            baseline_medicaid_share=("weighted_baseline_share", "sum"),
            baseline_medicaid_n_years=("cohort_n_years", "min"),
            baseline_medicare_share=("weighted_baseline_medicare", "sum"),
            baseline_medicare_n_years=("cohort_medicare_n_years", "min"),
            baseline_avgadl_mds3=("weighted_baseline_avgadl_mds3", "sum"),
            baseline_avgadl_mds3_n_years=("cohort_avgadl_mds3_n_years", "min"),
            baseline_window_start=("cohort_window_start", "min"),
            baseline_window_end=("cohort_window_end", "max"),
            valid_pseudocohorts=("cohort_year", "nunique"),
        )
    )
    out["facility_name"] = out["provider_name_latest"]
    out["state"] = out["state_latest"]
    out["analysis_sample"] = "control_v2"
    out["treat_year"] = pd.NA
    out["baseline_spec"] = baseline_spec
    out["sample_role"] = "control"
    out["baseline_method"] = "control_weighted_pseudocohort"
    out = out[
        [
            "baseline_spec",
            "ccn_str",
            "facility_name",
            "state",
            "sample_role",
            "analysis_sample",
            "treat_year",
            "baseline_medicaid_share",
            "baseline_medicaid_n_years",
            "baseline_medicare_share",
            "baseline_medicare_n_years",
            "baseline_avgadl_mds3",
            "baseline_avgadl_mds3_n_years",
            "baseline_window_start",
            "baseline_window_end",
            "baseline_method",
            "valid_pseudocohorts",
        ]
    ]
    return out, treated_weights.assign(baseline_spec=baseline_spec)


def export_csv_and_dta(df: pd.DataFrame, csv_path: Path, dta_path: Path | None = None) -> None:
    df.to_csv(csv_path, index=False)
    if dta_path is not None:
        safe = df.copy()
        for col in safe.columns:
            if is_string_dtype(safe[col]):
                safe[col] = safe[col].astype("string").fillna("")
            elif is_object_dtype(safe[col]):
                nonmissing = safe[col].dropna()
                numeric_candidate = pd.to_numeric(safe[col], errors="coerce")
                if len(nonmissing) == 0:
                    safe[col] = ""
                elif int(numeric_candidate.notna().sum()) == int(len(nonmissing)):
                    safe[col] = numeric_candidate
                else:
                    safe[col] = safe[col].astype("string").fillna("")
        safe.to_stata(dta_path, write_index=False, version=118)


def write_readme() -> None:
    README_PATH.write_text(
        """## LTCFocus intermediate outputs

This folder contains cleaned LTCFocus facility-year outputs built from the raw
annual workbooks in `data/raw/ltcfocus/`.

Key files:
- `ltcfocus_facility_year_full.csv`: full standardized LTCFocus panel for 2009-2023
- `ltcfocus_medicaid_analysis.csv`: slim Medicaid-analysis panel used for merges
- `ltcfocus_medicaid_baseline_inputs.csv`: facility-level baseline inputs for main and expanded study samples

Variable mapping:
- `PROV1680` -> `ccn_str`
- `PROV0475` -> `facility_name_ltcfocus`
- `paymcaid` -> `ltcfocus_medicaid_share`
- `paymcare` -> `ltcfocus_medicare_share`
- `avgadl_mds3` -> `ltcfocus_avgadl_mds3`
- `profit` -> `ltcfocus_for_profit` (`Yes`=1, `No`=0)
- `multifac` -> `ltcfocus_multifacility` (`Yes`=1, `No`=0)

Missing-value conventions cleaned during ingestion:
- blank strings
- dot placeholders such as `.`, ` .`, `   .`
- `LNE`

Raw workbooks are preserved unchanged in `data/raw/ltcfocus/`.
All downstream merges should use the cleaned intermediate outputs rather than
the raw Excel files.
""",
        encoding="utf-8",
    )


def main() -> None:
    ensure_dir(INTERMEDIATE_DIR)
    ensure_dir(OUTPUTS_QA_DIR)

    files = sorted(
        p for p in RAW_LTCFOCUS_DIR.iterdir() if p.is_file() and p.name in EXPECTED_FILENAMES
    )
    if [p.name for p in files] != EXPECTED_FILENAMES:
        raise FileNotFoundError(
            f"Expected LTCFocus files {EXPECTED_FILENAMES}, found {[p.name for p in files]}"
        )

    inventory_rows = []
    full_frames = []
    for path in files:
        df = read_ltcfocus_file(path)
        inventory_rows.append(
            {
                "source_file": path.name,
                "source_year": parse_year_from_name(path),
                "rows_read": int(len(df)),
                "sheet_assumed": "Facility",
                "unique_ccns": int(df["ccn_str"].dropna().nunique()),
                "year_min": int(df["year"].min()),
                "year_max": int(df["year"].max()),
            }
        )
        full_frames.append(df)

    inventory_df = pd.DataFrame(inventory_rows)
    inventory_df.to_csv(INVENTORY_PATH, index=False)

    full_df = pd.concat(full_frames, ignore_index=True)
    full_df = full_df.dropna(subset=["ccn_str", "year"]).copy()
    full_df = full_df.drop_duplicates().copy()
    full_df = full_df.sort_values(["ccn_str", "year", "source_file"]).reset_index(drop=True)

    duplicates = full_df[full_df.duplicated(subset=["ccn_str", "year"], keep=False)].copy()
    if not duplicates.empty:
        duplicates.to_csv(DUPLICATE_CCN_YEAR_PATH, index=False)
        full_df["_nonmissing_count"] = full_df.notna().sum(axis=1)
        sort_cols = ["ccn_str", "year", "_nonmissing_count"]
        if "accpt_id" in full_df.columns:
            sort_cols.append("accpt_id")
        full_df = (
            full_df.sort_values(sort_cols, ascending=[True, True, False] + [True] * (len(sort_cols) - 3))
            .drop_duplicates(subset=["ccn_str", "year"], keep="first")
            .drop(columns="_nonmissing_count")
            .reset_index(drop=True)
        )

    slim_df = build_slim_panel(full_df)

    export_csv_and_dta(full_df, FULL_OUTPUT_CSV, FULL_OUTPUT_DTA)
    export_csv_and_dta(slim_df, SLIM_OUTPUT_CSV, SLIM_OUTPUT_DTA)

    treatment_df = load_treatment()
    control_v2_df = load_control_v2()

    gold_df = treatment_df[treatment_df["analysis_sample"].eq("gold_main")].copy()
    expanded_df = treatment_df[treatment_df["analysis_sample"].isin(["gold_main", "silver_main"])].copy()

    gold_cov = build_coverage_by_year(gold_df["ccn_str"], slim_df, "gold_main")
    expanded_cov = build_coverage_by_year(expanded_df["ccn_str"], slim_df, "gold_plus_silver_main")
    control_cov = build_coverage_by_year(control_v2_df["ccn_str"], slim_df, "control_v2")
    gold_cov.to_csv(COVERAGE_GOLD_PATH, index=False)
    expanded_cov.to_csv(COVERAGE_EXPANDED_PATH, index=False)
    control_cov.to_csv(COVERAGE_CONTROLS_PATH, index=False)

    gold_unmatched = build_unmatched(
        gold_df["ccn_str"],
        slim_df,
        "gold_main",
        gold_df[["ccn_str", "facility_name", "state", "analysis_sample", "treat_year"]],
    )
    expanded_unmatched = build_unmatched(
        expanded_df["ccn_str"],
        slim_df,
        "gold_plus_silver_main",
        expanded_df[["ccn_str", "facility_name", "state", "analysis_sample", "treat_year"]],
    )
    control_unmatched = build_unmatched(
        control_v2_df["ccn_str"],
        slim_df,
        "control_v2",
        control_v2_df.rename(columns={"provider_name_latest": "facility_name", "state_latest": "state"})[
            ["ccn_str", "facility_name", "state"]
        ],
    )
    gold_unmatched.to_csv(UNMATCHED_GOLD_PATH, index=False)
    expanded_unmatched.to_csv(UNMATCHED_EXPANDED_PATH, index=False)
    control_unmatched.to_csv(UNMATCHED_CONTROLS_PATH, index=False)

    years_dist = build_year_coverage_distribution(
        [
            ("gold_main", gold_df[["ccn_str"]]),
            ("gold_plus_silver_main", expanded_df[["ccn_str"]]),
            ("control_v2", control_v2_df[["ccn_str"]]),
        ],
        slim_df,
    )
    years_dist.to_csv(YEARS_PER_FACILITY_PATH, index=False)

    treated_main_baseline = compute_treated_baseline(slim_df, gold_df, "gold_main_v2")
    treated_expanded_baseline = compute_treated_baseline(slim_df, expanded_df, "gold_plus_silver_v2")
    control_main_baseline, main_weights = compute_control_baseline(slim_df, control_v2_df, gold_df, "gold_main_v2")
    control_expanded_baseline, expanded_weights = compute_control_baseline(
        slim_df, control_v2_df, expanded_df, "gold_plus_silver_v2"
    )
    cohort_weights = pd.concat([main_weights, expanded_weights], ignore_index=True)
    cohort_weights.to_csv(COHORT_WEIGHTS_PATH, index=False)

    baseline_df = pd.concat(
        [
            treated_main_baseline,
            control_main_baseline,
            treated_expanded_baseline,
            control_expanded_baseline,
        ],
        ignore_index=True,
    )
    baseline_df = baseline_df.sort_values(["baseline_spec", "sample_role", "ccn_str"]).reset_index(drop=True)
    export_csv_and_dta(baseline_df, BASELINE_OUTPUT_CSV, BASELINE_OUTPUT_DTA)

    gold_missing_baseline = gold_df[~gold_df["ccn_str"].isin(set(treated_main_baseline["ccn_str"]))].copy()
    expanded_missing_baseline = expanded_df[
        ~expanded_df["ccn_str"].isin(set(treated_expanded_baseline["ccn_str"]))
    ].copy()
    gold_missing_baseline.to_csv(BASELINE_GOLD_INSUFFICIENT_PATH, index=False)
    expanded_missing_baseline.to_csv(BASELINE_EXPANDED_INSUFFICIENT_PATH, index=False)

    match_2022 = int(expanded_cov.loc[expanded_cov["year"].eq(2022), "matched_facilities"].iloc[0])
    match_2023 = int(expanded_cov.loc[expanded_cov["year"].eq(2023), "matched_facilities"].iloc[0])
    total_expanded = int(len(set(expanded_df["ccn_str"].dropna().astype(str))))

    summary = {
        "raw_files_processed": [p.name for p in files],
        "years_processed_min": int(full_df["year"].min()),
        "years_processed_max": int(full_df["year"].max()),
        "full_rows": int(len(full_df)),
        "full_unique_facilities": int(full_df["ccn_str"].nunique()),
        "slim_rows": int(len(slim_df)),
        "slim_unique_facilities": int(slim_df["ccn_str"].nunique()),
        "full_duplicate_ccn_year_rows": int(len(duplicates)),
        "gold_main_facilities": int(len(set(gold_df["ccn_str"].dropna().astype(str)))),
        "gold_plus_silver_facilities": total_expanded,
        "control_v2_facilities": int(len(set(control_v2_df["ccn_str"].dropna().astype(str)))),
        "gold_main_unmatched_facilities": int(len(gold_unmatched)),
        "gold_plus_silver_unmatched_facilities": int(len(expanded_unmatched)),
        "control_v2_unmatched_facilities": int(len(control_unmatched)),
        "gold_main_treated_with_baseline": int(len(treated_main_baseline)),
        "gold_plus_silver_treated_with_baseline": int(len(treated_expanded_baseline)),
        "gold_main_treated_missing_baseline": int(len(gold_missing_baseline)),
        "gold_plus_silver_treated_missing_baseline": int(len(expanded_missing_baseline)),
        "gold_main_controls_with_baseline": int(len(control_main_baseline)),
        "gold_plus_silver_controls_with_baseline": int(len(control_expanded_baseline)),
        "gold_plus_silver_matches_2022": match_2022,
        "gold_plus_silver_matches_2023": match_2023,
        "gold_plus_silver_unmatched_2022_expected_note": "2022 may legitimately miss facilities whose treatment entry occurs later; current observed miss is acceptable if it reflects post-2022 entry.",
        "gold_plus_silver_2023_full_match": bool(match_2023 == total_expanded),
    }
    BUILD_SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    write_readme()


if __name__ == "__main__":
    main()
