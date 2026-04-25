#!/usr/bin/env python3
"""Build a 2013-2017 event-window panel for the Trilogy REIT cohort."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
RESEARCH_DIR = ROOT / "research" / "trilogy_2015_event_window"
CACHE_DIR = RESEARCH_DIR / "cache"
INVESTIGATED_PATH = (
    ROOT
    / "research"
    / "reit_ownership_investigation"
    / "reit_consecutive_homes_investigated.csv"
)
LTCFOCUS_FULL_PATH = ROOT / "data" / "intermediate" / "ltcfocus" / "ltcfocus_facility_year_full.csv"
LOCAL_2017_DIR = ROOT / "data" / "raw" / "outcomes" / "cms" / "care_compare_archived_annual" / "2017"

EVENT_PANEL_PATH = RESEARCH_DIR / "trilogy_2015_event_window_panel.csv"
COVERAGE_PATH = RESEARCH_DIR / "trilogy_2015_event_window_coverage.csv"
SUMMARY_PATH = RESEARCH_DIR / "trilogy_2015_event_window_summary.json"

CMS_ARCHIVE_URLS = {
    2013: "https://www.cms.gov/files/zip/nursing-home-compare-data-2013.zip",
    2014: "https://www.cms.gov/files/zip/nursing-home-compare-data-2014.zip",
    2015: "https://www.cms.gov/files/zip/nursing-home-compare-data-2015.zip",
    2016: "https://www.cms.gov/files/zip/nursing-home-compare-data-2016.zip",
}

YEARS = list(range(2013, 2018))
TRILOGY_ROWS = 38


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


def read_csv_flexible(file_obj, **kwargs) -> pd.DataFrame:
    raw = file_obj.read()
    if hasattr(file_obj, "close"):
        file_obj.close()
    for encoding in ("utf-8", "latin1"):
        try:
            return pd.read_csv(io.BytesIO(raw), encoding=encoding, **kwargs)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(io.BytesIO(raw), encoding="latin1", **kwargs)


def get_series(df: pd.DataFrame, candidates: Iterable[str]) -> pd.Series:
    lookup = {str(col).strip().lower(): col for col in df.columns}
    for candidate in candidates:
        match = lookup.get(candidate.lower())
        if match is not None:
            return df[match]
    return pd.Series(pd.NA, index=df.index, dtype="object")


def get_numeric(df: pd.DataFrame, candidates: Iterable[str]) -> pd.Series:
    return pd.to_numeric(get_series(df, candidates), errors="coerce")


def load_trilogy_facilities() -> pd.DataFrame:
    investigated = pd.read_csv(INVESTIGATED_PATH, dtype="string").fillna(pd.NA)
    trilogy = investigated.iloc[:TRILOGY_ROWS].copy()
    trilogy["ccn_str"] = trilogy["ccn_str"].map(canonical_ccn).astype("string")
    trilogy = trilogy[["ccn_str", "facility_name", "state", "owner_cluster"]].copy()
    trilogy = trilogy.rename(columns={"facility_name": "facility_name_reit_file"})
    return trilogy


def load_ltcfocus(trilogy_ccns: set[str]) -> pd.DataFrame:
    full = pd.read_csv(LTCFOCUS_FULL_PATH, dtype="string").fillna(pd.NA)
    full["ccn_str"] = full["ccn_str"].map(canonical_ccn).astype("string")
    full["year"] = pd.to_numeric(full["year"], errors="coerce").astype("Int64")
    full = full[full["ccn_str"].isin(trilogy_ccns) & full["year"].between(2013, 2017)].copy()

    result = pd.DataFrame(
        {
            "ccn_str": full["ccn_str"],
            "year": full["year"].astype(int),
            "ltcfocus_facility_name": full.get("facility_name_ltcfocus"),
            "ltcfocus_state": full.get("state"),
            "ltcfocus_total_beds": pd.to_numeric(full.get("totbeds"), errors="coerce"),
            "ltcfocus_residents": pd.to_numeric(full.get("nresid"), errors="coerce"),
            "ltcfocus_avg_dailycensus": pd.to_numeric(full.get("avg_dailycensus"), errors="coerce"),
            "ltcfocus_medicaid_share": pd.to_numeric(full.get("paymcaid"), errors="coerce"),
            "ltcfocus_medicare_share": pd.to_numeric(full.get("paymcare"), errors="coerce"),
            "ltcfocus_rn_hprd": pd.to_numeric(full.get("rnhrppd"), errors="coerce"),
            "ltcfocus_lpn_hprd": pd.to_numeric(full.get("lpnhrppd"), errors="coerce"),
            "ltcfocus_cna_hprd": pd.to_numeric(full.get("cnahrppd"), errors="coerce"),
            "ltcfocus_directcare_hprd": pd.to_numeric(full.get("dchrppd"), errors="coerce"),
            "ltcfocus_obs_rehosprate": pd.to_numeric(full.get("obs_rehosprate"), errors="coerce"),
            "ltcfocus_adj_rehosprate": pd.to_numeric(full.get("adj_rehosprate"), errors="coerce"),
            "ltcfocus_source_file": full.get("source_file"),
        }
    )
    return result.drop_duplicates(subset=["ccn_str", "year"]).reset_index(drop=True)


def fetch_archive(year: int) -> zipfile.ZipFile:
    ensure_dir(CACHE_DIR)
    cache_path = CACHE_DIR / f"nursing_home_compare_{year}.zip"
    if not cache_path.exists():
        response = requests.get(CMS_ARCHIVE_URLS[year], timeout=120)
        response.raise_for_status()
        cache_path.write_bytes(response.content)
    return zipfile.ZipFile(cache_path)


def load_provider_frame(file_obj, year: int) -> pd.DataFrame:
    df = read_csv_flexible(file_obj, dtype="string").fillna(pd.NA)
    frame = pd.DataFrame(
        {
            "ccn_str": get_series(df, ["PROVNUM", "provnum"]).map(canonical_ccn).astype("string"),
            "year": year,
            "cms_provider_name": get_series(df, ["PROVNAME", "Provname"]),
            "cms_ownership_type": get_series(df, ["OWNERSHIP", "ownership"]),
            "cms_legal_business_name": get_series(df, ["LBN", "lbn"]),
            "cms_certified_beds": get_numeric(df, ["BEDCERT", "bedcert"]),
            "cms_average_residents": get_numeric(df, ["RESTOT", "restot"]),
            "cms_chow_last_12mos": get_series(df, ["CHOW_LAST_12MOS", "chow_last_12mos"]),
            "cms_overall_rating": get_numeric(df, ["overall_rating"]),
            "cms_survey_rating": get_numeric(df, ["survey_rating"]),
            "cms_quality_rating": get_numeric(df, ["quality_rating"]),
            "cms_staffing_rating": get_numeric(df, ["staffing_rating"]),
            "cms_rn_staffing_rating": get_numeric(df, ["RN_staffing_rating", "rn_staffing_rating"]),
            "cms_provider_aide_hprd": get_numeric(df, ["AIDHRD", "aidhrd"]),
            "cms_provider_lpn_hprd": get_numeric(df, ["VOCHRD", "vochrd"]),
            "cms_provider_rn_hprd": get_numeric(df, ["RNHRD", "rnhrd"]),
            "cms_provider_total_licensed_hprd": get_numeric(df, ["TOTLICHRD", "totlichrd"]),
            "cms_provider_total_nurse_hprd": get_numeric(df, ["TOTHRD", "tothrd"]),
            "cms_provider_pt_hprd": get_numeric(df, ["PTHRD", "pthrd"]),
        }
    )
    frame = frame.dropna(subset=["ccn_str"])
    return frame.drop_duplicates(subset=["ccn_str", "year"]).reset_index(drop=True)


def load_staffing_frame(file_obj, year: int) -> pd.DataFrame:
    df = read_csv_flexible(file_obj, dtype="string").fillna(pd.NA)
    df["ccn_str"] = get_series(df, ["PROVNUM", "provnum"]).map(canonical_ccn).astype("string")
    df["quarter"] = get_series(df, ["Quarter", "quarter"]).astype("string").str.strip()
    numeric_map = {
        "cms_staffing_file_aide_hprd": ["AIDHRD", "aidhrd"],
        "cms_staffing_file_lpn_hprd": ["VOCHRD", "vochrd"],
        "cms_staffing_file_rn_hprd": ["RNHRD", "rnhrd"],
        "cms_staffing_file_total_licensed_hprd": ["TOTLICHRD", "totlichrd"],
        "cms_staffing_file_total_nurse_hprd": ["TOTHRD", "tothrd"],
        "cms_staffing_file_pt_hprd": ["PTHRD", "pthrd"],
        "cms_staffing_file_expected_aide": ["exp_aide"],
        "cms_staffing_file_expected_lpn": ["exp_lpn"],
        "cms_staffing_file_expected_rn": ["exp_rn"],
        "cms_staffing_file_expected_total": ["exp_total"],
        "cms_staffing_file_adjusted_aide": ["adj_aide"],
        "cms_staffing_file_adjusted_lpn": ["adj_lpn"],
        "cms_staffing_file_adjusted_rn": ["adj_rn"],
        "cms_staffing_file_adjusted_total": ["adj_total"],
    }
    for name, candidates in numeric_map.items():
        df[name] = get_numeric(df, candidates)

    subset = df[df["ccn_str"].notna()].copy()
    grouped = (
        subset.groupby("ccn_str", as_index=False)
        .agg(
            cms_staffing_file_quarters=("quarter", lambda s: s.dropna().nunique()),
            **{name: (name, "mean") for name in numeric_map},
        )
        .assign(year=year)
    )
    return grouped


def load_deficiency_frame(file_obj, year: int) -> pd.DataFrame:
    df = read_csv_flexible(file_obj, dtype="string").fillna(pd.NA)
    df["ccn_str"] = get_series(df, ["PROVNUM", "provnum"]).map(canonical_ccn).astype("string")
    df["survey_date"] = pd.to_datetime(
        get_series(df, ["survey_date_output", "H_SURVEY_DATE", "h_survey_date"]),
        errors="coerce",
    )
    complaint = get_series(df, ["complaint", "Complaint"]).astype("string").str.upper()
    standard = get_series(df, ["standard", "Standard"]).astype("string").str.upper()
    subset = df[df["ccn_str"].notna()].copy()
    grouped = (
        subset.groupby("ccn_str", as_index=False)
        .agg(
            cms_deficiency_citations=("ccn_str", "size"),
            cms_deficiency_distinct_tags=(get_series(subset, ["tag", "TAG"]).name or "ccn_str", "size"),
        )
    )
    # Recompute tag counts and flags on the filtered frame.
    tag_series = get_series(subset, ["tag", "TAG"])
    grouped["cms_deficiency_distinct_tags"] = (
        subset.assign(_tag=tag_series)
        .groupby("ccn_str")["_tag"]
        .nunique(dropna=True)
        .reindex(grouped["ccn_str"])
        .to_numpy()
    )
    grouped["cms_deficiency_complaint_citations"] = (
        complaint.loc[subset.index]
        .isin({"Y", "YES", "TRUE", "1"})
        .groupby(subset["ccn_str"])
        .sum()
        .reindex(grouped["ccn_str"])
        .to_numpy()
    )
    grouped["cms_deficiency_standard_citations"] = (
        standard.loc[subset.index]
        .isin({"Y", "YES", "TRUE", "1"})
        .groupby(subset["ccn_str"])
        .sum()
        .reindex(grouped["ccn_str"])
        .to_numpy()
    )
    grouped["cms_deficiency_unique_survey_dates"] = (
        subset.groupby("ccn_str")["survey_date"]
        .nunique(dropna=True)
        .reindex(grouped["ccn_str"])
        .to_numpy()
    )
    grouped["year"] = year
    return grouped


def load_survey_summary_frame(path: Path, year: int) -> pd.DataFrame:
    df = pd.read_csv(path, dtype="string", encoding="latin1").fillna(pd.NA)
    frame = pd.DataFrame(
        {
            "ccn_str": get_series(df, ["PROVNUM", "provnum"]).map(canonical_ccn).astype("string"),
            "year": year,
            "cms_survey_summary_health_deficiencies": get_numeric(df, ["H_TOT_DFCNCY", "h_tot_dfcncy"]),
            "cms_survey_summary_fire_deficiencies": get_numeric(df, ["F_TOT_DFCNCY", "f_tot_dfcncy"]),
            "cms_survey_summary_health_severity_score": get_numeric(df, ["H_SS_MAX", "h_ss_max"]),
            "cms_survey_summary_health_ij_count": get_numeric(df, ["H_IJ_N", "h_ij_n"]),
            "cms_survey_summary_health_severe_count": get_numeric(df, ["H_SEVERE_N", "h_severe_n"]),
        }
    )
    frame = frame.dropna(subset=["ccn_str"])
    return frame.drop_duplicates(subset=["ccn_str", "year"]).reset_index(drop=True)


def load_cms_year(year: int) -> pd.DataFrame:
    if year <= 2016:
        with fetch_archive(year) as zf:
            provider = load_provider_frame(zf.open(f"ProviderInfo_{year}.csv"), year)
            staffing = load_staffing_frame(zf.open(f"Staffing_{year}.csv"), year)
            deficiencies = load_deficiency_frame(zf.open(f"Deficiencies_{year}.csv"), year)
            survey = pd.DataFrame(columns=["ccn_str", "year"])
    else:
        provider = load_provider_frame((LOCAL_2017_DIR / "ProviderInfo_Download.csv").open("rb"), year)
        staffing = pd.DataFrame(columns=["ccn_str", "year"])
        deficiencies = load_deficiency_frame((LOCAL_2017_DIR / "Deficiencies_Download.csv").open("rb"), year)
        survey = load_survey_summary_frame(LOCAL_2017_DIR / "SurveySummary_Download.csv", year)

    merged = provider.merge(staffing, on=["ccn_str", "year"], how="left")
    merged = merged.merge(deficiencies, on=["ccn_str", "year"], how="left")
    merged = merged.merge(survey, on=["ccn_str", "year"], how="left")
    return merged


def build_cms_panel(trilogy_ccns: set[str]) -> pd.DataFrame:
    frames = []
    for year in YEARS:
        frame = load_cms_year(year)
        frames.append(frame[frame["ccn_str"].isin(trilogy_ccns)].copy())
    return pd.concat(frames, ignore_index=True)


def build_base_panel(trilogy: pd.DataFrame) -> pd.DataFrame:
    years = pd.DataFrame({"year": YEARS})
    trilogy = trilogy.copy()
    trilogy["key"] = 1
    years["key"] = 1
    panel = trilogy.merge(years, on="key", how="outer").drop(columns="key")
    panel["event_time"] = panel["year"] - 2015
    return panel.sort_values(["ccn_str", "year"]).reset_index(drop=True)


def build_coverage(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, frame in panel.groupby("year", sort=True):
        rows.append(
            {
                "year": int(year),
                "facilities_in_cohort": int(frame["ccn_str"].nunique()),
                "facilities_with_ltcfocus_staffing": int(frame["ltcfocus_rn_hprd"].notna().sum()),
                "facilities_with_cms_provider_staffing": int(frame["cms_provider_total_nurse_hprd"].notna().sum()),
                "facilities_with_cms_staffing_file": int(frame["cms_staffing_file_total_nurse_hprd"].notna().sum()),
                "facilities_with_cms_deficiencies": int(frame["cms_deficiency_citations"].notna().sum()),
                "facilities_with_cms_survey_rating": int(frame["cms_survey_rating"].notna().sum()),
                "facilities_with_cms_survey_summary": int(frame["cms_survey_summary_health_deficiencies"].notna().sum()),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    ensure_dir(RESEARCH_DIR)
    trilogy = load_trilogy_facilities()
    trilogy_ccns = set(trilogy["ccn_str"].dropna().astype(str))

    base = build_base_panel(trilogy)
    ltcfocus = load_ltcfocus(trilogy_ccns)
    cms = build_cms_panel(trilogy_ccns)

    panel = base.merge(ltcfocus, on=["ccn_str", "year"], how="left")
    panel = panel.merge(cms, on=["ccn_str", "year"], how="left")
    panel = panel.sort_values(["ccn_str", "year"]).reset_index(drop=True)

    coverage = build_coverage(panel)

    panel.to_csv(EVENT_PANEL_PATH, index=False)
    coverage.to_csv(COVERAGE_PATH, index=False)

    summary = {
        "facilities_in_cohort": int(base["ccn_str"].nunique()),
        "years": YEARS,
        "event_window": {"t_minus_2": 2013, "t0": 2015, "t_plus_2": 2017},
        "ltcfocus_years_available": sorted(pd.to_numeric(ltcfocus["year"], errors="coerce").dropna().astype(int).unique().tolist()),
        "cms_provider_years_available": sorted(pd.to_numeric(cms.loc[cms["cms_provider_name"].notna(), "year"], errors="coerce").dropna().astype(int).unique().tolist()),
        "cms_deficiency_years_available": sorted(pd.to_numeric(cms.loc[cms["cms_deficiency_citations"].notna(), "year"], errors="coerce").dropna().astype(int).unique().tolist()),
        "sources": {
            "cms_archive_page": "https://www.cms.gov/medicare/health-safety-standards/quality-safety-oversight-general-information/five-star-quality-rating-system/five-star-quality-rating-system-archives",
            "cms_archives_used": CMS_ARCHIVE_URLS,
            "local_2017_provider_info": str(LOCAL_2017_DIR / "ProviderInfo_Download.csv"),
            "local_2017_deficiencies": str(LOCAL_2017_DIR / "Deficiencies_Download.csv"),
            "local_2017_survey_summary": str(LOCAL_2017_DIR / "SurveySummary_Download.csv"),
            "ltcfocus_intermediate": str(LTCFOCUS_FULL_PATH),
            "cohort_source": str(INVESTIGATED_PATH),
        },
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {EVENT_PANEL_PATH}")
    print(f"Wrote {COVERAGE_PATH}")
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
