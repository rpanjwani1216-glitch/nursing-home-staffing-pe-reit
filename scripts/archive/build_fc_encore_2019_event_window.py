#!/usr/bin/env python3
"""Build a 2017-2021 event-window panel for the FC Encore cohort."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INVESTIGATED_PATH = (
    ROOT
    / "research"
    / "reit_ownership_investigation"
    / "reit_consecutive_homes_investigated.csv"
)
LTCFOCUS_PATH = ROOT / "data" / "intermediate" / "ltcfocus" / "ltcfocus_facility_year_full.csv"
PBJ_PATH = ROOT / "data" / "intermediate" / "cms" / "pbj_nurse_facility_year.csv"
PROVIDER_PATH = ROOT / "data" / "intermediate" / "cms" / "care_compare_provider_info_year.csv"
HEALTH_PATH = ROOT / "data" / "intermediate" / "cms" / "care_compare_health_deficiencies_year.csv"
SURVEY_PATH = ROOT / "data" / "intermediate" / "cms" / "care_compare_survey_summary_year.csv"

RESEARCH_DIR = ROOT / "research" / "fc_encore_2019_event_window"
PANEL_PATH = RESEARCH_DIR / "fc_encore_2019_event_window_panel.csv"
COVERAGE_PATH = RESEARCH_DIR / "fc_encore_2019_event_window_coverage.csv"
SUMMARY_PATH = RESEARCH_DIR / "fc_encore_2019_event_window_summary.json"

YEARS = list(range(2017, 2022))
DEAL_YEAR = 2019


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def canonical_ccn(value: object) -> str | None:
    if pd.isna(value):
        return None
    digits = "".join(ch for ch in str(value).strip() if ch.isdigit())
    if not digits:
        return None
    digits = digits.zfill(6)[-6:]
    if digits == "000000":
        return None
    return digits


def load_fc_encore_cohort() -> pd.DataFrame:
    investigated = pd.read_csv(INVESTIGATED_PATH, dtype="string").fillna(pd.NA)
    mask = (
        investigated["owner_name_raw_primary"].astype("string").str.contains("FC ENCORE", case=False, na=False)
        | investigated["owner_cluster"].astype("string").str.contains("FC ENCORE", case=False, na=False)
    )
    cohort = investigated.loc[mask, ["ccn_str", "facility_name", "state", "owner_name_raw_primary", "owner_cluster"]].copy()
    cohort["ccn_str"] = cohort["ccn_str"].map(canonical_ccn).astype("string")
    return cohort.rename(columns={"facility_name": "facility_name_reit_file"}).reset_index(drop=True)


def build_base_panel(cohort: pd.DataFrame) -> pd.DataFrame:
    years = pd.DataFrame({"year": YEARS})
    cohort = cohort.copy()
    cohort["key"] = 1
    years["key"] = 1
    panel = cohort.merge(years, on="key", how="outer").drop(columns="key")
    panel["event_time"] = panel["year"] - DEAL_YEAR
    return panel.sort_values(["ccn_str", "year"]).reset_index(drop=True)


def load_ltcfocus(ccns: set[str]) -> pd.DataFrame:
    df = pd.read_csv(LTCFOCUS_PATH, dtype="string").fillna(pd.NA)
    df["ccn_str"] = df["ccn_str"].map(canonical_ccn).astype("string")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df = df[df["ccn_str"].isin(ccns) & df["year"].between(min(YEARS), max(YEARS))].copy()
    out = pd.DataFrame(
        {
            "ccn_str": df["ccn_str"],
            "year": df["year"].astype(int),
            "ltcfocus_facility_name": df.get("facility_name_ltcfocus"),
            "ltcfocus_state": df.get("state"),
            "ltcfocus_total_beds": pd.to_numeric(df.get("totbeds"), errors="coerce"),
            "ltcfocus_residents": pd.to_numeric(df.get("nresid"), errors="coerce"),
            "ltcfocus_avg_dailycensus": pd.to_numeric(df.get("avg_dailycensus"), errors="coerce"),
            "ltcfocus_medicaid_share": pd.to_numeric(df.get("paymcaid"), errors="coerce"),
            "ltcfocus_medicare_share": pd.to_numeric(df.get("paymcare"), errors="coerce"),
            "ltcfocus_rn_hprd": pd.to_numeric(df.get("rnhrppd"), errors="coerce"),
            "ltcfocus_lpn_hprd": pd.to_numeric(df.get("lpnhrppd"), errors="coerce"),
            "ltcfocus_cna_hprd": pd.to_numeric(df.get("cnahrppd"), errors="coerce"),
            "ltcfocus_directcare_hprd": pd.to_numeric(df.get("dchrppd"), errors="coerce"),
            "ltcfocus_obs_rehosprate": pd.to_numeric(df.get("obs_rehosprate"), errors="coerce"),
            "ltcfocus_adj_rehosprate": pd.to_numeric(df.get("adj_rehosprate"), errors="coerce"),
        }
    )
    return out.drop_duplicates(subset=["ccn_str", "year"]).reset_index(drop=True)


def load_pbj(ccns: set[str]) -> pd.DataFrame:
    df = pd.read_csv(PBJ_PATH, dtype={"ccn_str": str})
    df["ccn_str"] = df["ccn_str"].map(canonical_ccn)
    df = df[df["ccn_str"].isin(ccns) & df["year"].between(min(YEARS), max(YEARS))].copy()
    return df[[
        "ccn_str",
        "year",
        "pbj_source_files",
        "pbj_days_observed",
        "pbj_mean_census",
        "pbj_total_rn_hours",
        "pbj_total_nurse_hours",
        "pbj_mean_rn_hprd",
        "pbj_mean_nurse_hprd",
    ]].drop_duplicates(subset=["ccn_str", "year"]).reset_index(drop=True)


def load_provider(ccns: set[str]) -> pd.DataFrame:
    df = pd.read_csv(PROVIDER_PATH, dtype={"ccn_str": str}).fillna(pd.NA)
    df["ccn_str"] = df["ccn_str"].map(canonical_ccn)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df = df[df["ccn_str"].isin(ccns) & df["year"].between(min(YEARS), max(YEARS))].copy()
    cols = {
        "Provider Name": "cms_provider_name",
        "Ownership Type": "cms_ownership_type",
        "Legal Business Name": "cms_legal_business_name",
        "Chain Name": "cms_chain_name",
        "Overall Rating": "cms_overall_rating",
        "Health Inspection Rating": "cms_health_rating",
        "QM Rating": "cms_qm_rating",
        "Staffing Rating": "cms_staffing_rating",
        "RN Staffing Rating": "cms_rn_staffing_rating",
        "Reported Total Nurse Staffing Hours per Resident per Day": "cms_reported_total_nurse_hprd",
        "Provider Changed Ownership in Last 12 Months": "cms_chow_last_12mos",
        "Total Weighted Health Survey Score": "cms_total_weighted_health_survey_score",
        "Number of Substantiated Complaints": "cms_substantiated_complaints",
    }
    out = df[["ccn_str", "year"] + list(cols)].rename(columns=cols)
    return out.drop_duplicates(subset=["ccn_str", "year"]).reset_index(drop=True)


def load_health(ccns: set[str]) -> pd.DataFrame:
    df = pd.read_csv(HEALTH_PATH, dtype={"ccn_str": str})
    df["ccn_str"] = df["ccn_str"].map(canonical_ccn)
    df = df[df["ccn_str"].isin(ccns) & df["year"].between(min(YEARS), max(YEARS))].copy()
    return df.drop_duplicates(subset=["ccn_str", "year"]).reset_index(drop=True)


def load_survey(ccns: set[str]) -> pd.DataFrame:
    df = pd.read_csv(SURVEY_PATH, dtype={"ccn_str": str})
    df["ccn_str"] = df["ccn_str"].map(canonical_ccn)
    df = df[df["ccn_str"].isin(ccns) & df["year"].between(min(YEARS), max(YEARS))].copy()
    return df.drop_duplicates(subset=["ccn_str", "year"]).reset_index(drop=True)


def build_coverage(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, frame in panel.groupby("year", sort=True):
        rows.append(
            {
                "year": int(year),
                "facilities_in_cohort": int(frame["ccn_str"].nunique()),
                "facilities_with_ltcfocus_staffing": int(frame["ltcfocus_rn_hprd"].notna().sum()),
                "facilities_with_pbj_staffing": int(frame["pbj_mean_nurse_hprd"].notna().sum()),
                "facilities_with_care_compare_staffing": int(frame["cms_reported_total_nurse_hprd"].notna().sum()),
                "facilities_with_health_deficiencies": int(frame["deficiency_citations"].notna().sum()),
                "facilities_with_survey_summary": int(frame["survey_summary_total_health_deficiencies"].notna().sum()),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    ensure_dir(RESEARCH_DIR)
    cohort = load_fc_encore_cohort()
    ccns = set(cohort["ccn_str"].dropna().astype(str))

    panel = build_base_panel(cohort)
    panel = panel.merge(load_ltcfocus(ccns), on=["ccn_str", "year"], how="left")
    panel = panel.merge(load_pbj(ccns), on=["ccn_str", "year"], how="left")
    panel = panel.merge(load_provider(ccns), on=["ccn_str", "year"], how="left")
    panel = panel.merge(load_health(ccns), on=["ccn_str", "year"], how="left")
    panel = panel.merge(load_survey(ccns), on=["ccn_str", "year"], how="left")
    panel = panel.sort_values(["ccn_str", "year"]).reset_index(drop=True)

    coverage = build_coverage(panel)
    panel.to_csv(PANEL_PATH, index=False)
    coverage.to_csv(COVERAGE_PATH, index=False)

    summary = {
        "facilities_in_cohort": int(cohort["ccn_str"].nunique()),
        "ccns": sorted(ccns),
        "deal_year": DEAL_YEAR,
        "years": YEARS,
        "event_window": {"t_minus_2": 2017, "t0": 2019, "t_plus_2": 2021},
        "source_files": {
            "cohort_source": str(INVESTIGATED_PATH),
            "ltcfocus": str(LTCFOCUS_PATH),
            "pbj": str(PBJ_PATH),
            "care_compare_provider": str(PROVIDER_PATH),
            "care_compare_health": str(HEALTH_PATH),
            "care_compare_survey": str(SURVEY_PATH),
        },
        "transaction_sources": {
            "seller_advisor_page": "https://hl.com/about-us/transactions/houlihan-lokey-advises-fc-encore/",
            "omega_trade_press": "https://skillednursingnews.com/2019/11/omega-closes-735m-skilled-nursing-deal-confirms-consulate-as-primary-operator/",
        },
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {PANEL_PATH}")
    print(f"Wrote {COVERAGE_PATH}")
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
