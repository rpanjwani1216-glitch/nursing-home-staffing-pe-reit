#!/usr/bin/env python3
"""Build a broader 2017-2021 Omega/Consulate event-window panel from a verified 30-facility subset."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESEARCH_DIR = ROOT / "research" / "omega_consulate_2019_event_window"
LTCFOCUS_PATH = ROOT / "data" / "intermediate" / "ltcfocus" / "ltcfocus_facility_year_full.csv"
PBJ_PATH = ROOT / "data" / "intermediate" / "cms" / "pbj_nurse_facility_year.csv"
PROVIDER_PATH = ROOT / "data" / "intermediate" / "cms" / "care_compare_provider_info_year.csv"
HEALTH_PATH = ROOT / "data" / "intermediate" / "cms" / "care_compare_health_deficiencies_year.csv"
SURVEY_PATH = ROOT / "data" / "intermediate" / "cms" / "care_compare_survey_summary_year.csv"

PANEL_PATH = RESEARCH_DIR / "omega_consulate_2019_event_window_panel.csv"
COVERAGE_PATH = RESEARCH_DIR / "omega_consulate_2019_event_window_coverage.csv"
ROSTER_PATH = RESEARCH_DIR / "omega_consulate_2019_verified_roster.csv"
UNMATCHED_PATH = RESEARCH_DIR / "omega_consulate_2019_unmatched_facilities.csv"
SUMMARY_PATH = RESEARCH_DIR / "omega_consulate_2019_event_window_summary.json"

YEARS = list(range(2017, 2022))
DEAL_YEAR = 2019

STATE_MAP = {
    "VIRGINIA": "VA",
    "NORTH CAROLINA": "NC",
    "MISSISSIPPI": "MS",
    "PENNSYLVANIA": "PA",
}

FACILITY_LIST = [
    ("OHI Asset (VA) Ashland, LLC", "Ashland Nursing and Rehabilitation Center", "Ashland, Virginia", "495362", "fuzzy_provider_name"),
    ("FC Encore Cary, LLC", "Cary Health and Rehabilitation Center", "Cary, North Carolina", None, "unmatched"),
    ("CSE Woodfin LP", "Emerald Ridge Rehabilitation and Care Center", "Asheville, North Carolina", "345447", "fuzzy_provider_name"),
    ("FC Encore Albemarle, LLC", "Forrest Oakes Healthcare Center", "Albemarle, North Carolina", "345442", "exact_provider_name"),
    ("CSE Lenoir LP", "Gateway Rehabilitation and Healthcare", "Lenoir, North Carolina", "345329", "exact_provider_name"),
    ("FC Encore Natchez, LLC", "Glenburney Health Care and Rehabilitation Center", "Natchez, Mississippi", "255173", "exact_provider_name"),
    ("FC Encore Union, LLC", "Hilltop Manor Health and Rehabilitation Center", "Union, Mississippi", "255260", "exact_provider_name"),
    ("FC Encore Kannapolis, LLC", "Transitional Health Services of Kannapolis", "Kannapolis, North Carolina", "345258", "exact_provider_name"),
    ("Mifflin Re Owner LLC", "Locust Grove Retirement Village", "Mifflin, Pennsylvania", "395350", "exact_provider_name"),
    ("Mifflin Re Owner LLC", "The Cottage at Locust Grove", "Mifflin, Pennsylvania", None, "unmatched_non_snf_or_name_gap"),
    ("Hazleton Re Owner LLC", "Luther Ridge at Seiders Hill", "Pottsville, Pennsylvania", None, "unmatched_non_snf_or_name_gap"),
    ("Hazleton Re Owner LLC", "The Manor at St. Luke Village", "Hazleton, Pennsylvania", "395636", "fuzzy_provider_name"),
    ("FC Encore McComb, LLC", "Courtyard Rehabilitation and Healthcare", "McComb, Mississippi", "255145", "exact_provider_name"),
    ("OHI Asset (VA) Norfolk, LLC", "Consulate Health Care of Norfolk", "Norfolk, Virginia", "495273", "exact_provider_name"),
    ("FC Encore Rutherfordton, LLC", "Oak Grove Healthcare Center", "Rutherfordton, North Carolina", "345464", "fuzzy_provider_name"),
    ("CSE Arden LP", "The Oaks at Sweeten Creek", "Arden, North Carolina", "345477", "exact_provider_name"),
    ("Hazleton Re Owner LLC", "The Pavilion at St. Luke Village", "Hazleton, Pennsylvania", "395265", "fuzzy_provider_name"),
    ("Selinsgrove Re Owner LLC", "Amity Village", "Selinsgrove, Pennsylvania", None, "unmatched_non_snf_or_name_gap"),
    ("Everett Re Owner LLC", "The Manor at Penn Village", "Everett, Pennsylvania", "395172", "fuzzy_provider_name"),
    ("Everett Re Owner LLC", "Pennsfield Apartments", "Everett, Pennsylvania", None, "unmatched_non_snf_or_name_gap"),
    ("Everett Re Owner LLC", "Pennknoll Village", "Everett, Pennsylvania", "395422", "exact_provider_name"),
    ("FC Encore Meridian, LLC", "The Oaks Rehabilitation and Healthcare Center", "Meridian, Mississippi", "255261", "exact_provider_name"),
    ("FC Encore Starkville, LLC", "Starkville Manor Health Care and Rehabilitation Center", "Starkville, Mississippi", "255172", "fuzzy_provider_name"),
    ("FC Encore Andrews, LLC", "Valley View Care and Rehabilitation Center", "Andrews, North Carolina", "345426", "fuzzy_provider_name"),
    ("CSE Walnut Cove LP", "Walnut Cove Health and Rehabilitation Center", "Walnut Cove, North Carolina", "345089", "exact_provider_name"),
    ("CSE Knightdale LP", "Wellington Rehabilitation and Healthcare", "Knightdale, North Carolina", "345436", "exact_provider_name"),
    ("FC Encore Archdale, LLC", "Westwood Health and Rehabilitation Center", "Archdale, North Carolina", "345450", "fuzzy_provider_name"),
    ("FC Encore Yadkinville, LLC", "Willowbrook Rehabilitation and Care Center", "Yadkinville, North Carolina", "345466", "exact_provider_name"),
    ("FC Encore Charlotte, LLC", "Wilora Lake Healthcare Center", "Charlotte, North Carolina", "345473", "exact_provider_name"),
    ("FC Encore Winona, LLC", "Winona Manor Health Care and Rehabilitation Center", "Winona, Mississippi", "255171", "exact_provider_name"),
]


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


def normalize_name(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", str(value).upper()).strip()


def build_roster() -> pd.DataFrame:
    roster = pd.DataFrame(
        FACILITY_LIST,
        columns=["omega_landlord", "facility_name_source", "city_state_source", "ccn_str", "match_method"],
    )
    roster["city_source"] = roster["city_state_source"].str.split(",").str[0].str.strip()
    roster["state_full"] = roster["city_state_source"].str.split(",").str[-1].str.strip().str.upper()
    roster["state"] = roster["state_full"].map(STATE_MAP)
    roster["ccn_str"] = roster["ccn_str"].map(canonical_ccn).astype("string")

    provider = pd.read_csv(PROVIDER_PATH, dtype={"ccn_str": str}).fillna(pd.NA)
    provider["ccn_str"] = provider["ccn_str"].map(canonical_ccn)
    provider["name_norm"] = provider["Provider Name"].map(normalize_name)
    provider["state"] = provider["State"].astype("string").str.upper()
    provider_latest = (
        provider.sort_values(["ccn_str", "year"])
        .drop_duplicates(subset=["ccn_str"], keep="last")
        [["ccn_str", "Provider Name", "state"]]
        .rename(columns={"Provider Name": "provider_name_latest", "state": "provider_state"})
    )
    roster = roster.merge(provider_latest, on="ccn_str", how="left")
    return roster.drop(columns="state_full")


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
        }
    )
    return out.drop_duplicates(subset=["ccn_str", "year"]).reset_index(drop=True)


def load_pbj(ccns: set[str]) -> pd.DataFrame:
    df = pd.read_csv(PBJ_PATH, dtype={"ccn_str": str})
    df["ccn_str"] = df["ccn_str"].map(canonical_ccn)
    df = df[df["ccn_str"].isin(ccns) & df["year"].between(min(YEARS), max(YEARS))].copy()
    return df.drop_duplicates(subset=["ccn_str", "year"]).reset_index(drop=True)


def load_provider(ccns: set[str]) -> pd.DataFrame:
    df = pd.read_csv(PROVIDER_PATH, dtype={"ccn_str": str}).fillna(pd.NA)
    df["ccn_str"] = df["ccn_str"].map(canonical_ccn)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df = df[df["ccn_str"].isin(ccns) & df["year"].between(min(YEARS), max(YEARS))].copy()
    keep = [
        "ccn_str",
        "year",
        "Provider Name",
        "Ownership Type",
        "Legal Business Name",
        "Chain Name",
        "Overall Rating",
        "Health Inspection Rating",
        "QM Rating",
        "Staffing Rating",
        "RN Staffing Rating",
        "Reported Total Nurse Staffing Hours per Resident per Day",
        "Provider Changed Ownership in Last 12 Months",
        "Total Weighted Health Survey Score",
        "Number of Substantiated Complaints",
    ]
    out = df[keep].rename(
        columns={
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
    )
    return out.drop_duplicates(subset=["ccn_str", "year"]).reset_index(drop=True)


def load_health(ccns: set[str]) -> pd.DataFrame:
    df = pd.read_csv(HEALTH_PATH, dtype={"ccn_str": str})
    df["ccn_str"] = df["ccn_str"].map(canonical_ccn)
    return df[df["ccn_str"].isin(ccns) & df["year"].between(min(YEARS), max(YEARS))].drop_duplicates(subset=["ccn_str", "year"]).reset_index(drop=True)


def load_survey(ccns: set[str]) -> pd.DataFrame:
    df = pd.read_csv(SURVEY_PATH, dtype={"ccn_str": str})
    df["ccn_str"] = df["ccn_str"].map(canonical_ccn)
    return df[df["ccn_str"].isin(ccns) & df["year"].between(min(YEARS), max(YEARS))].drop_duplicates(subset=["ccn_str", "year"]).reset_index(drop=True)


def build_panel(roster: pd.DataFrame) -> pd.DataFrame:
    matched = roster[roster["ccn_str"].notna()].copy()
    ccns = set(matched["ccn_str"].astype(str))
    years = pd.DataFrame({"year": YEARS})
    matched["key"] = 1
    years["key"] = 1
    panel = matched.merge(years, on="key", how="outer").drop(columns="key")
    panel["event_time"] = panel["year"] - DEAL_YEAR
    panel = panel.merge(load_ltcfocus(ccns), on=["ccn_str", "year"], how="left")
    panel = panel.merge(load_pbj(ccns), on=["ccn_str", "year"], how="left")
    panel = panel.merge(load_provider(ccns), on=["ccn_str", "year"], how="left")
    panel = panel.merge(load_health(ccns), on=["ccn_str", "year"], how="left")
    panel = panel.merge(load_survey(ccns), on=["ccn_str", "year"], how="left")
    return panel.sort_values(["state", "facility_name_source", "year"]).reset_index(drop=True)


def build_coverage(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, frame in panel.groupby("year", sort=True):
        rows.append(
            {
                "year": int(year),
                "facilities_in_panel": int(frame["ccn_str"].nunique()),
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
    roster = build_roster()
    panel = build_panel(roster)
    coverage = build_coverage(panel)
    unmatched = roster[roster["ccn_str"].isna()].copy()

    roster.to_csv(ROSTER_PATH, index=False)
    unmatched.to_csv(UNMATCHED_PATH, index=False)
    panel.to_csv(PANEL_PATH, index=False)
    coverage.to_csv(COVERAGE_PATH, index=False)

    summary = {
        "deal_year": DEAL_YEAR,
        "source_facilities_listed_in_bankruptcy_filing": int(len(roster)),
        "matched_facilities_with_ccns": int(roster["ccn_str"].notna().sum()),
        "unmatched_facilities": int(roster["ccn_str"].isna().sum()),
        "years": YEARS,
        "event_window": {"t_minus_2": 2017, "t0": 2019, "t_plus_2": 2021},
        "source_documents": {
            "lavie_bankruptcy_facility_list_pdf": "https://documents.elevenflo.com/uuid_database_8_14_23/b3244505-3f86-4db2-a068-7de32236d986.pdf",
            "stretto_creditor_matrix_pdf": "https://cases.stretto.com/public/X122/11358/PLEADINGS/1135804152180000000161.pdf",
            "houlihan_lokey_fc_encore_transaction": "https://hl.com/about-us/transactions/houlihan-lokey-advises-fc-encore/",
        },
        "repo_sources": {
            "ltcfocus": str(LTCFOCUS_PATH),
            "pbj": str(PBJ_PATH),
            "care_compare_provider": str(PROVIDER_PATH),
            "care_compare_health": str(HEALTH_PATH),
            "care_compare_survey": str(SURVEY_PATH),
        },
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {ROSTER_PATH}")
    print(f"Wrote {UNMATCHED_PATH}")
    print(f"Wrote {PANEL_PATH}")
    print(f"Wrote {COVERAGE_PATH}")
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
