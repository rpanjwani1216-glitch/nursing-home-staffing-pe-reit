#!/usr/bin/env python3
"""Build treated-only facility-year inspection panels.

These panels are convenience intermediates for understanding how the treated
facilities look over time before running the final Stata analysis workflow.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from pandas.api.types import is_object_dtype, is_string_dtype


from utils import get_intermediate_dir, get_output_dir

ROOT = Path(__file__).resolve().parents[1]
RESEARCH_DIR = ROOT / "research"
INTERMEDIATE_ROOT = get_intermediate_dir(ROOT)
CMS_DIR = INTERMEDIATE_ROOT / "cms"
LTCFOCUS_DIR = INTERMEDIATE_ROOT / "ltcfocus"
TREATED_DIR = INTERMEDIATE_ROOT / "treated"

TREATMENT_PATH = RESEARCH_DIR / "pe_facility_verification.csv"
CMS_FOUNDATION_PATH = CMS_DIR / "cms_facility_year_foundation.csv"
LTCFOCUS_PATH = LTCFOCUS_DIR / "ltcfocus_medicaid_analysis.csv"

GOLD_CSV = TREATED_DIR / "treated_gold_main_facility_year_panel.csv"
GOLD_DTA = TREATED_DIR / "treated_gold_main_facility_year_panel.dta"
EXPANDED_CSV = TREATED_DIR / "treated_gold_plus_silver_facility_year_panel.csv"
EXPANDED_DTA = TREATED_DIR / "treated_gold_plus_silver_facility_year_panel.dta"
SUMMARY_JSON = TREATED_DIR / "treated_facility_year_panel_summary.json"
README_PATH = TREATED_DIR / "README.md"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def canonical_ccn(value: object) -> str | None:
    if pd.isna(value):
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if not digits:
        return None
    digits = digits.zfill(6)[-6:]
    if digits == "000000":
        return None
    return digits


def extract_treat_year(value: object) -> int | None:
    if pd.isna(value):
        return None
    match = re.search(r"(20\d{2})", str(value))
    if not match:
        return None
    return int(match.group(1))


def export_csv_and_dta(df: pd.DataFrame, csv_path: Path, dta_path: Path) -> None:
    df.to_csv(csv_path, index=False)
    safe = df.copy()
    for col in safe.columns:
        if is_string_dtype(safe[col]):
            safe[col] = safe[col].astype("string").fillna("")
        elif is_object_dtype(safe[col]):
            numeric_candidate = pd.to_numeric(safe[col], errors="coerce")
            nonmissing = safe[col].dropna()
            if len(nonmissing) == 0:
                safe[col] = ""
            elif int(numeric_candidate.notna().sum()) == int(len(nonmissing)):
                safe[col] = numeric_candidate
            else:
                safe[col] = safe[col].astype("string").fillna("")
    safe.to_stata(dta_path, write_index=False, version=118)


def load_treatment() -> pd.DataFrame:
    df = pd.read_csv(TREATMENT_PATH, dtype="string").fillna(pd.NA)
    df["ccn_str"] = df["ccn"].map(canonical_ccn).astype("string")
    df["treat_year"] = df["ownership_effective_date"].map(extract_treat_year).astype("Int64")
    df = df[df["analysis_sample"].isin(["gold_main", "silver_main"])].copy()
    keep_cols = [
        "ccn_str",
        "facility_name",
        "deal_id",
        "pe_firm",
        "platform_name",
        "state",
        "city",
        "address",
        "analysis_sample",
        "transition_type",
        "transition_verified",
        "verification_tier",
        "ownership_effective_date",
        "treat_year",
        "source_platform_link",
        "source_facility_link",
        "pre_owner_name",
        "pre_operator_name",
        "post_operator_name",
        "verification_notes",
    ]
    out = df[keep_cols].drop_duplicates(subset=["ccn_str"]).copy()
    rename_map = {
        "facility_name": "facility_name_treat",
        "state": "state_treat",
        "city": "city_treat",
        "address": "address_treat",
    }
    return out.rename(columns=rename_map)


def load_cms_foundation() -> pd.DataFrame:
    df = pd.read_csv(CMS_FOUNDATION_PATH, dtype={"ccn_str": "string"}, low_memory=False)
    df["ccn_str"] = df["ccn_str"].map(canonical_ccn).astype("string")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    rename_map = {
        "facility_name": "facility_name_cms",
        "state": "state_cms",
        "deal_id": "deal_id_cms",
        "treat_year": "treat_year_cms",
        "verification_tier": "verification_tier_cms",
        "verified_treated": "verified_treated_cms",
        "post_treatment_year": "post_treatment_year_cms",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    return df[df["ccn_str"].notna() & df["year"].notna()].copy()


def load_ltcfocus() -> pd.DataFrame:
    df = pd.read_csv(LTCFOCUS_PATH, dtype={"ccn_str": "string"}, low_memory=False)
    df["ccn_str"] = df["ccn_str"].map(canonical_ccn).astype("string")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    return df[df["ccn_str"].notna() & df["year"].notna()].copy()


def first_nonmissing(series: pd.Series):
    nonmissing = series.dropna()
    if len(nonmissing) == 0:
        return pd.NA
    return nonmissing.iloc[0]


def collapse_facility_year_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    grouped = (
        df.sort_values(["ccn_str", "year"])
        .groupby(["ccn_str", "year"], as_index=False, dropna=False)
        .agg(first_nonmissing)
    )
    return grouped.sort_values(["ccn_str", "year"]).reset_index(drop=True)


def build_panel(treatment_df: pd.DataFrame, cms_df: pd.DataFrame, ltcfocus_df: pd.DataFrame, sample_name: str) -> pd.DataFrame:
    subset = treatment_df[treatment_df["analysis_sample"].isin(["gold_main"] if sample_name == "gold_main" else ["gold_main", "silver_main"])].copy()
    year_shell = pd.concat(
        [
            cms_df.loc[cms_df["ccn_str"].isin(subset["ccn_str"]), ["ccn_str", "year"]],
            ltcfocus_df.loc[ltcfocus_df["ccn_str"].isin(subset["ccn_str"]), ["ccn_str", "year"]],
        ],
        ignore_index=True,
    ).drop_duplicates()
    merged = year_shell.merge(subset, on="ccn_str", how="inner")
    merged = merged.merge(cms_df, on=["ccn_str", "year"], how="left")
    merged = merged.merge(
        ltcfocus_df,
        on=["ccn_str", "year"],
        how="left",
        suffixes=("", "_ltcfocus"),
    )

    merged["sample_spec"] = sample_name
    merged["treated_ever"] = 1
    merged["post_treat"] = (merged["year"] >= merged["treat_year"]).astype("Int64")
    merged.loc[merged["treat_year"].isna(), "post_treat"] = pd.NA
    merged["event_time"] = merged["year"] - merged["treat_year"]
    if "verified_treated_cms" in merged.columns:
        merged["verified_treated_cms"] = 1
    if "post_treatment_year_cms" in merged.columns:
        merged["post_treatment_year_cms"] = merged["post_treat"]
    merged = collapse_facility_year_rows(merged)

    preferred_cols = [
        "sample_spec",
        "analysis_sample",
        "ccn_str",
        "facility_name_treat",
        "facility_name_cms",
        "facility_name_ltcfocus",
        "year",
        "treat_year",
        "event_time",
        "post_treat",
        "deal_id",
        "pe_firm",
        "platform_name",
        "state_treat",
        "state_cms",
        "city_treat",
        "treated_ever",
        "transition_type",
        "transition_verified",
        "verification_tier",
        "ownership_effective_date",
        "ltcfocus_medicaid_share",
        "ltcfocus_medicare_share",
        "ltcfocus_avg_dailycensus",
        "ltcfocus_obs_rehosprate",
        "ltcfocus_adj_rehosprate",
        "form671_medicaid_share_mean",
        "pbj_mean_rn_hprd",
        "pbj_mean_nurse_hprd",
        "deficiency_citations",
        "deficiency_actual_harm_or_ij_citations",
        "survey_summary_total_health_deficiencies",
        "source_platform_link",
        "source_facility_link",
        "verification_notes",
    ]
    cols = [c for c in preferred_cols if c in merged.columns]
    other_cols = [c for c in merged.columns if c not in cols]
    merged = merged[cols + other_cols].sort_values(["ccn_str", "year"]).reset_index(drop=True)
    return merged


def write_readme() -> None:
    README_PATH.write_text(
        """## Treated facility-year panels

This folder contains treated-only facility-year panels derived from the
national CMS foundation panel, the integrated treatment file, and cleaned
LTCFocus Medicaid data.

Files:
- `treated_gold_main_facility_year_panel.csv`: only the strict gold treatment sample
- `treated_gold_plus_silver_facility_year_panel.csv`: the expanded treated sample

Each row is one treated facility-year and includes:
- treatment timing (`treat_year`, `event_time`, `post_treat`)
- treatment metadata (`deal_id`, `analysis_sample`, verification fields)
- CMS outcome and source-coverage fields from the national foundation
- year-by-year LTCFocus Medicaid and related covariates

These files are inspection/analysis intermediates for understanding treated
facilities over time. The source of truth for treatment classification remains
`research/pe_facility_verification.csv`.
""",
        encoding="utf-8",
    )


def main() -> None:
    ensure_dir(TREATED_DIR)

    treatment_df = load_treatment()
    cms_df = load_cms_foundation()
    ltcfocus_df = load_ltcfocus()

    gold_panel = build_panel(treatment_df, cms_df, ltcfocus_df, "gold_main")
    expanded_panel = build_panel(treatment_df, cms_df, ltcfocus_df, "gold_plus_silver")

    export_csv_and_dta(gold_panel, GOLD_CSV, GOLD_DTA)
    export_csv_and_dta(expanded_panel, EXPANDED_CSV, EXPANDED_DTA)

    summary = {
        "gold_main_rows": int(len(gold_panel)),
        "gold_plus_silver_rows": int(len(expanded_panel)),
        "gold_main_unique_facilities": int(gold_panel["ccn_str"].nunique()),
        "gold_plus_silver_unique_facilities": int(expanded_panel["ccn_str"].nunique()),
        "gold_main_duplicate_ccn_year_rows": int(gold_panel.duplicated(subset=["ccn_str", "year"]).sum()),
        "gold_plus_silver_duplicate_ccn_year_rows": int(expanded_panel.duplicated(subset=["ccn_str", "year"]).sum()),
        "gold_main_year_min": int(gold_panel["year"].min()) if not gold_panel.empty else None,
        "gold_main_year_max": int(gold_panel["year"].max()) if not gold_panel.empty else None,
        "gold_plus_silver_year_min": int(expanded_panel["year"].min()) if not expanded_panel.empty else None,
        "gold_plus_silver_year_max": int(expanded_panel["year"].max()) if not expanded_panel.empty else None,
        "gold_main_with_ltcfocus_rows": int(gold_panel["ltcfocus_medicaid_share"].notna().sum()),
        "gold_plus_silver_with_ltcfocus_rows": int(expanded_panel["ltcfocus_medicaid_share"].notna().sum()),
        "gold_main_with_pbj_rows": int(gold_panel["pbj_mean_nurse_hprd"].notna().sum()),
        "gold_plus_silver_with_pbj_rows": int(expanded_panel["pbj_mean_nurse_hprd"].notna().sum()),
        "gold_main_with_deficiency_rows": int(gold_panel["deficiency_citations"].notna().sum()),
        "gold_plus_silver_with_deficiency_rows": int(expanded_panel["deficiency_citations"].notna().sum()),
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_readme()


if __name__ == "__main__":
    main()
