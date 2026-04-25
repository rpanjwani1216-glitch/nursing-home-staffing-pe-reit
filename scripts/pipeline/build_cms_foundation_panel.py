#!/usr/bin/env python3
"""Build the CMS facility-year foundation panel and its core intermediates."""

from __future__ import annotations

import csv
import json
import math
import os
import re
from pathlib import Path
from typing import Iterable

import pandas as pd


import sys
sys.path.insert(0, str(Path(__file__).parent))
from utils import get_intermediate_dir, get_output_dir

ROOT = Path(__file__).resolve().parents[2]
CMS_ROOT = ROOT / "data" / "raw" / "outcomes" / "cms"
CARE_COMPARE_ARCHIVE_ROOT = CMS_ROOT / "care_compare_archived_annual"
INTERMEDIATE_ROOT = get_intermediate_dir(ROOT) / "cms"
MANIFEST_ROOT = CMS_ROOT / "manifests"
RESEARCH_ROOT = ROOT / "research"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_csv_flexible(path: Path, **kwargs):
    last_err: Exception | None = None
    wants_chunks = "chunksize" in kwargs
    for encoding in ("utf-8", "latin1"):
        try:
            reader = pd.read_csv(path, encoding=encoding, **kwargs)
            if not wants_chunks:
                return reader
            iterator = iter(reader)
            try:
                first_chunk = next(iterator)
            except StopIteration:
                return iter(())

            def chunk_gen():
                yield first_chunk
                for chunk in iterator:
                    yield chunk

            return chunk_gen()
        except UnicodeDecodeError as err:
            last_err = err
    if last_err is not None:
        raise last_err
    raise RuntimeError(f"Unable to read {path}")


def canonical_ccn(series: pd.Series) -> pd.Series:
    raw = series.astype("string").str.strip()
    has_letters = raw.str.contains(r"[A-Za-z]", na=False)
    cleaned = raw.str.replace(r"[^0-9]", "", regex=True).str.zfill(6)
    valid = cleaned.str.fullmatch(r"\d{6}") & cleaned.ne("000000") & ~has_letters
    return cleaned.where(valid, pd.NA)


def first_nonmissing(series: pd.Series):
    nonmissing = series.dropna()
    if nonmissing.empty:
        return pd.NA
    return nonmissing.iloc[0]


def collapse_unique_facility_year(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    ordered = df.sort_values(["ccn_str", "year"]).copy()
    collapsed = (
        ordered.groupby(["ccn_str", "year"], as_index=False, dropna=False)
        .agg(first_nonmissing)
        .sort_values(["ccn_str", "year"])
        .reset_index(drop=True)
    )
    return collapsed


def parse_date_prefix(name: str) -> pd.Timestamp | None:
    m = re.match(r"(\d{4}-\d{2}-\d{2})__", name)
    if not m:
        return None
    return pd.to_datetime(m.group(1), errors="coerce")


def parse_dotted_date(name: str) -> pd.Timestamp | None:
    m = re.search(r"(\d{4})[._](\d{2})[._](\d{2})", name)
    if not m:
        return None
    return pd.Timestamp(year=int(m.group(1)), month=int(m.group(2)), day=int(m.group(3)))


def read_manifest(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    cols = [c.lower() for c in df.columns]
    if cols[:4] == ["dataset_id", "title", "modified", "download_url"]:
        df["basename"] = df["download_url"].map(lambda x: Path(str(x)).name)
        df["period_start"] = pd.NaT
        df["period_end"] = pd.NaT
        return df
    if len(df.columns) == 5:
        df.columns = ["dataset_title", "resource_title", "temporal", "modified", "download_url"]
        df["basename"] = df["download_url"].map(lambda x: Path(str(x)).name)
        temporal_split = df["temporal"].astype("string").str.split("/", n=1, expand=True)
        df["period_start"] = pd.to_datetime(temporal_split[0], errors="coerce")
        df["period_end"] = pd.to_datetime(temporal_split[1], errors="coerce")
        return df
    raise ValueError(f"Unexpected manifest format: {path}")


def build_inventory() -> pd.DataFrame:
    records: list[dict] = []
    for manifest_path in sorted(MANIFEST_ROOT.glob("*.csv")):
        manifest = read_manifest(manifest_path)
        manifest_name = manifest_path.stem
        for _, row in manifest.iterrows():
            basename = row.get("basename")
            matches = list(CMS_ROOT.rglob(basename)) if pd.notna(basename) else []
            records.append(
                {
                    "manifest": manifest_name,
                    "dataset_title": row.get("dataset_title", row.get("title")),
                    "download_url": row.get("download_url"),
                    "basename": basename,
                    "period_start": row.get("period_start"),
                    "period_end": row.get("period_end"),
                    "match_count": len(matches),
                    "matched_paths": "|".join(str(p.relative_to(ROOT)) for p in matches),
                }
            )
    inventory = pd.DataFrame(records)
    if not inventory.empty:
        inventory.to_csv(INTERMEDIATE_ROOT / "cms_source_inventory.csv", index=False)
    return inventory


def parse_form671() -> pd.DataFrame:
    manifest = read_manifest(MANIFEST_ROOT / "form671_manifest.csv")
    by_name = manifest.set_index("basename")[["period_start", "period_end"]].to_dict("index")
    rows: list[pd.DataFrame] = []
    for path in sorted((CMS_ROOT / "form671").glob("*.csv")):
        meta = by_name.get(path.name, {})
        df = read_csv_flexible(path, dtype=str)
        df["ccn_str"] = canonical_ccn(df["Provider Number"])
        df["period_start"] = meta.get("period_start")
        df["period_end"] = meta.get("period_end")
        df["year"] = pd.to_datetime(df["period_end"]).dt.year
        numeric_cols = ["Medicare Census", "Medicaid Census", "Other Census", "Total Residents"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["form671_medicaid_share"] = df["Medicaid Census"] / df["Total Residents"]
        keep = [
            "ccn_str",
            "Facility Name",
            "City",
            "State",
            "period_start",
            "period_end",
            "year",
            "Medicare Census",
            "Medicaid Census",
            "Other Census",
            "Total Residents",
            "Hospital Based",
            "Ownership Type",
            "Multi-Facility Organization",
            "Multi-Facility Organization Name",
            "form671_medicaid_share",
        ]
        rows.append(df[keep].copy())
    combined = pd.concat(rows, ignore_index=True)
    combined = combined.dropna(subset=["ccn_str", "year"])
    combined.to_csv(INTERMEDIATE_ROOT / "form671_facility_period.csv", index=False)
    year_df = (
        combined.groupby(["ccn_str", "year"], as_index=False)
        .agg(
            form671_records=("ccn_str", "size"),
            form671_total_residents_mean=("Total Residents", "mean"),
            form671_medicaid_census_mean=("Medicaid Census", "mean"),
            form671_medicare_census_mean=("Medicare Census", "mean"),
            form671_medicaid_share_mean=("form671_medicaid_share", "mean"),
            form671_last_period_end=("period_end", "max"),
        )
    )
    year_df.to_csv(INTERMEDIATE_ROOT / "form671_facility_year.csv", index=False)
    return year_df


def parse_snf_enrollments_monthly() -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for path in sorted((CMS_ROOT / "snf_enrollments").glob("*.csv")):
        if path.name == "SNF_Enrollments.csv":
            continue
        snapshot_date = parse_date_prefix(path.name) or parse_dotted_date(path.name)
        if snapshot_date is None:
            continue
        df = read_csv_flexible(path, dtype=str)
        df["snapshot_date"] = snapshot_date
        df["snapshot_year"] = snapshot_date.year
        df["ccn_str"] = canonical_ccn(df["CCN"])
        keep = [
            "snapshot_date",
            "snapshot_year",
            "ENROLLMENT ID",
            "ASSOCIATE ID",
            "ccn_str",
            "ORGANIZATION NAME",
            "DOING BUSINESS AS NAME",
            "NURSING HOME PROVIDER NAME",
            "AFFILIATION ENTITY NAME",
            "PROPRIETARY_NONPROFIT",
            "STATE",
            "CITY",
            "ZIP CODE",
        ]
        rows.append(df[keep].copy())
    combined = pd.concat(rows, ignore_index=True)
    combined = combined.dropna(subset=["snapshot_date", "ccn_str"])
    combined.to_csv(INTERMEDIATE_ROOT / "snf_enrollments_monthly.csv", index=False)
    latest = (
        combined.sort_values(["ccn_str", "snapshot_year", "snapshot_date"])
        .groupby(["ccn_str", "snapshot_year"], as_index=False)
        .tail(1)
        .rename(columns={"snapshot_year": "year"})
    )
    latest.to_csv(INTERMEDIATE_ROOT / "snf_enrollments_year_latest.csv", index=False)
    return combined


def parse_snf_all_owners_monthly(enrollments_monthly: pd.DataFrame) -> pd.DataFrame:
    crosswalk_cols = [
        "snapshot_date",
        "ENROLLMENT ID",
        "ccn_str",
        "NURSING HOME PROVIDER NAME",
        "STATE",
    ]
    crosswalk = enrollments_monthly[crosswalk_cols].drop_duplicates()
    rows: list[pd.DataFrame] = []
    owner_dir = CMS_ROOT / "snf_all_owners"
    for path in sorted(owner_dir.glob("*.csv")):
        if path.name == "SNF_All_Owners.csv":
            continue
        snapshot_date = parse_date_prefix(path.name) or parse_dotted_date(path.name)
        if snapshot_date is None:
            continue
        df = read_csv_flexible(path, dtype=str)
        df["snapshot_date"] = snapshot_date
        df["snapshot_year"] = snapshot_date.year
        for col in [
            "PERCENTAGE OWNERSHIP",
            "PRIVATE EQUITY COMPANY - OWNER",
            "REIT - OWNER",
            "TRUST OR TRUSTEE - OWNER",
            "INVESTMENT FIRM - OWNER",
            "HOLDING COMPANY - OWNER",
            "MANAGEMENT SERVICES COMPANY - OWNER",
        ]:
            if col in df.columns:
                df[col] = df[col].astype("string")
        df = df.merge(crosswalk, on=["snapshot_date", "ENROLLMENT ID"], how="left")
        rows.append(df)
    combined = pd.concat(rows, ignore_index=True)
    flag_cols = {
        "owner_private_equity_flag": "PRIVATE EQUITY COMPANY - OWNER",
        "owner_reit_flag": "REIT - OWNER",
        "owner_trust_flag": "TRUST OR TRUSTEE - OWNER",
        "owner_investment_firm_flag": "INVESTMENT FIRM - OWNER",
        "owner_holding_company_flag": "HOLDING COMPANY - OWNER",
        "owner_management_company_flag": "MANAGEMENT SERVICES COMPANY - OWNER",
    }
    for out_col, source_col in flag_cols.items():
        combined[out_col] = combined[source_col].astype("string").str.upper().isin(["Y", "YES", "TRUE", "1"])
    combined.to_csv(INTERMEDIATE_ROOT / "snf_all_owners_monthly.csv", index=False)
    latest = combined.groupby(["ccn_str", "snapshot_year"])["snapshot_date"].transform("max") == combined["snapshot_date"]
    year_df = (
        combined[latest]
        .dropna(subset=["ccn_str"])
        .groupby(["ccn_str", "snapshot_year"], as_index=False)
        .agg(
            owner_rows=("ENROLLMENT ID", "size"),
            unique_owner_entities=("ASSOCIATE ID - OWNER", pd.Series.nunique),
            any_private_equity_owner=("owner_private_equity_flag", "max"),
            any_reit_owner=("owner_reit_flag", "max"),
            any_trust_owner=("owner_trust_flag", "max"),
            any_investment_firm_owner=("owner_investment_firm_flag", "max"),
            any_holding_company_owner=("owner_holding_company_flag", "max"),
            any_management_company_owner=("owner_management_company_flag", "max"),
        )
        .rename(columns={"snapshot_year": "year"})
    )
    year_df.to_csv(INTERMEDIATE_ROOT / "snf_all_owners_year_latest.csv", index=False)
    return year_df


def parse_snf_chow() -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for path in sorted((CMS_ROOT / "snf_chow").glob("*.csv")):
        df = read_csv_flexible(path, dtype=str)
        df["effective_date"] = pd.to_datetime(df["EFFECTIVE DATE"], errors="coerce")
        df["effective_year"] = df["effective_date"].dt.year
        df["ccn_buyer_str"] = canonical_ccn(df["CCN - BUYER"])
        df["ccn_seller_str"] = canonical_ccn(df["CCN - SELLER"])
        keep = [
            "effective_date",
            "effective_year",
            "ccn_buyer_str",
            "ccn_seller_str",
            "ORGANIZATION NAME - BUYER",
            "DOING BUSINESS AS NAME - BUYER",
            "ORGANIZATION NAME - SELLER",
            "DOING BUSINESS AS NAME - SELLER",
            "CHOW TYPE TEXT",
        ]
        rows.append(df[keep].copy())
    combined = pd.concat(rows, ignore_index=True).dropna(subset=["effective_year"])
    combined.to_csv(INTERMEDIATE_ROOT / "snf_chow_events.csv", index=False)
    buyer_flags = (
        combined.dropna(subset=["ccn_buyer_str"])
        .groupby(["ccn_buyer_str", "effective_year"], as_index=False)
        .agg(has_chow_buyer_event=("ccn_buyer_str", "size"))
        .rename(columns={"ccn_buyer_str": "ccn_str", "effective_year": "year"})
    )
    seller_flags = (
        combined.dropna(subset=["ccn_seller_str"])
        .groupby(["ccn_seller_str", "effective_year"], as_index=False)
        .agg(has_chow_seller_event=("ccn_seller_str", "size"))
        .rename(columns={"ccn_seller_str": "ccn_str", "effective_year": "year"})
    )
    chow_year = buyer_flags.merge(seller_flags, on=["ccn_str", "year"], how="outer").fillna(0)
    chow_year.to_csv(INTERMEDIATE_ROOT / "snf_chow_facility_year.csv", index=False)
    return chow_year


def parse_pbj_nurse() -> pd.DataFrame:
    pbj_files = sorted((CMS_ROOT / "pbj_nurse").glob("*.csv"))
    standardized_hour_cols = [
        "hrs_rndon",
        "hrs_rnadmin",
        "hrs_rn",
        "hrs_lpnadmin",
        "hrs_lpn",
        "hrs_cna",
        "hrs_natrn",
        "hrs_medaide",
    ]
    hour_col_aliases = {
        "hrs_rndon": ["hrs_rndon", "hrs_rn_donadmin"],
        "hrs_rnadmin": ["hrs_rnadmin"],
        "hrs_rn": ["hrs_rn"],
        "hrs_lpnadmin": ["hrs_lpnadmin", "hrs_lpn_admin"],
        "hrs_lpn": ["hrs_lpn"],
        "hrs_cna": ["hrs_cna"],
        "hrs_natrn": ["hrs_natrn", "hrs_na_trn"],
        "hrs_medaide": ["hrs_medaide"],
    }
    aggregates: list[pd.DataFrame] = []
    skipped: list[dict] = []
    for path in pbj_files:
        with open(path, newline="", errors="ignore") as fh:
            header = next(csv.reader(fh))
        lower_map = {col.lower(): col for col in header}
        needed = ["provnum", "workdate", "mdscensus"]
        missing = [col for col in needed if col not in lower_map]
        resolved_hour_cols = {}
        for standard_col, aliases in hour_col_aliases.items():
            matched = next((lower_map[alias] for alias in aliases if alias in lower_map), None)
            resolved_hour_cols[standard_col] = matched
        if missing:
            skipped.append({"source_file": path.name, "reason": f"missing_columns:{'|'.join(missing)}"})
            continue
        pieces: list[pd.DataFrame] = []
        usecols = [lower_map[col] for col in needed]
        usecols.extend(sorted({col for col in resolved_hour_cols.values() if col is not None}))
        try:
            for chunk in read_csv_flexible(
                path,
                usecols=usecols,
                chunksize=250_000,
                low_memory=False,
                on_bad_lines="skip",
            ):
                chunk.columns = [col.lower() for col in chunk.columns]
                chunk["ccn_str"] = canonical_ccn(chunk["provnum"])
                chunk["workdate"] = pd.to_datetime(chunk["workdate"].astype("string"), format="%Y%m%d", errors="coerce")
                chunk["year"] = chunk["workdate"].dt.year
                chunk["mdscensus"] = pd.to_numeric(chunk["mdscensus"], errors="coerce")
                for standard_col, raw_col in resolved_hour_cols.items():
                    if raw_col is None:
                        chunk[standard_col] = 0.0
                    else:
                        chunk[standard_col] = pd.to_numeric(chunk[raw_col.lower()], errors="coerce").fillna(0)
                chunk["total_rn_hours"] = chunk["hrs_rndon"] + chunk["hrs_rnadmin"] + chunk["hrs_rn"]
                chunk["total_lpn_hours"] = chunk["hrs_lpnadmin"] + chunk["hrs_lpn"]
                chunk["total_aide_hours"] = chunk["hrs_cna"] + chunk["hrs_natrn"] + chunk["hrs_medaide"]
                chunk["total_nurse_hours"] = chunk["total_rn_hours"] + chunk["total_lpn_hours"] + chunk["total_aide_hours"]
                positive_census = chunk["mdscensus"].where(chunk["mdscensus"] > 0)
                chunk["rn_hprd"] = chunk["total_rn_hours"] / positive_census
                chunk["nurse_hprd"] = chunk["total_nurse_hours"] / positive_census
                pieces.append(
                    chunk.groupby(["ccn_str", "year"], as_index=False)
                    .agg(
                        pbj_days_observed=("workdate", "count"),
                        pbj_mean_census=("mdscensus", "mean"),
                        pbj_total_rn_hours=("total_rn_hours", "sum"),
                        pbj_total_nurse_hours=("total_nurse_hours", "sum"),
                        pbj_mean_rn_hprd=("rn_hprd", "mean"),
                        pbj_mean_nurse_hprd=("nurse_hprd", "mean"),
                    )
                )
        except pd.errors.ParserError as err:
            skipped.append({"source_file": path.name, "reason": f"parser_error:{err}"})
        if pieces:
            file_df = pd.concat(pieces, ignore_index=True)
            file_df = (
                file_df.groupby(["ccn_str", "year"], as_index=False)
                .agg(
                    pbj_days_observed=("pbj_days_observed", "sum"),
                    pbj_mean_census=("pbj_mean_census", "mean"),
                    pbj_total_rn_hours=("pbj_total_rn_hours", "sum"),
                    pbj_total_nurse_hours=("pbj_total_nurse_hours", "sum"),
                    pbj_mean_rn_hprd=("pbj_mean_rn_hprd", "mean"),
                    pbj_mean_nurse_hprd=("pbj_mean_nurse_hprd", "mean"),
                )
            )
            file_df["source_file"] = path.name
            aggregates.append(file_df)
    if not aggregates:
        return pd.DataFrame(columns=["ccn_str", "year"])
    combined = pd.concat(aggregates, ignore_index=True)
    year_df = (
        combined.groupby(["ccn_str", "year"], as_index=False)
        .agg(
            pbj_source_files=("source_file", "nunique"),
            pbj_days_observed=("pbj_days_observed", "sum"),
            pbj_mean_census=("pbj_mean_census", "mean"),
            pbj_total_rn_hours=("pbj_total_rn_hours", "sum"),
            pbj_total_nurse_hours=("pbj_total_nurse_hours", "sum"),
            pbj_mean_rn_hprd=("pbj_mean_rn_hprd", "mean"),
            pbj_mean_nurse_hprd=("pbj_mean_nurse_hprd", "mean"),
        )
    )
    year_df.to_csv(INTERMEDIATE_ROOT / "pbj_nurse_facility_year.csv", index=False)
    pd.DataFrame(skipped).to_csv(INTERMEDIATE_ROOT / "pbj_nurse_skipped_files.csv", index=False)
    return year_df


def parse_care_compare_latest() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    provider_path = CMS_ROOT / "care_compare_latest" / "NH_ProviderInfo_Mar2026.csv"
    survey_path = CMS_ROOT / "care_compare_latest" / "NH_SurveySummary_Mar2026.csv"
    health_path = CMS_ROOT / "care_compare_latest" / "NH_HealthCitations_Mar2026.csv"

    provider_df = pd.DataFrame()
    if provider_path.exists():
        provider_df = read_csv_flexible(provider_path, dtype=str)
        provider_df["ccn_str"] = canonical_ccn(provider_df["CMS Certification Number (CCN)"])
        provider_df["year"] = 2026
        keep = [
            "ccn_str",
            "year",
            "Provider Name",
            "State",
            "Ownership Type",
            "Chain Name",
            "Chain ID",
            "Overall Rating",
            "Health Inspection Rating",
            "QM Rating",
            "Staffing Rating",
            "Reported Total Nurse Staffing Hours per Resident per Day",
            "Provider Changed Ownership in Last 12 Months",
            "Processing Date",
        ]
        provider_df = provider_df[keep].copy()
        provider_df = collapse_unique_facility_year(provider_df)
        provider_df.to_csv(INTERMEDIATE_ROOT / "care_compare_provider_info_latest.csv", index=False)

    survey_df = pd.DataFrame()
    if survey_path.exists():
        survey_df = read_csv_flexible(survey_path, dtype=str)
        survey_df["ccn_str"] = canonical_ccn(survey_df["CMS Certification Number (CCN)"])
        survey_df["health_survey_date"] = pd.to_datetime(survey_df["Health Survey Date"], errors="coerce")
        survey_df["year"] = survey_df["health_survey_date"].dt.year
        numeric_cols = [
            "Total Number of Health Deficiencies",
            "Total Number of Fire Safety Deficiencies",
            "Count of Infection Control Deficiencies",
        ]
        for col in numeric_cols:
            survey_df[col] = pd.to_numeric(survey_df[col], errors="coerce")
        survey_df = (
            survey_df.dropna(subset=["ccn_str", "year"])
            .groupby(["ccn_str", "year"], as_index=False)
            .agg(
                survey_summary_rows=("Inspection Cycle", "size"),
                survey_summary_total_health_deficiencies=("Total Number of Health Deficiencies", "sum"),
                survey_summary_total_fire_safety_deficiencies=("Total Number of Fire Safety Deficiencies", "sum"),
                survey_summary_infection_control_deficiencies=("Count of Infection Control Deficiencies", "sum"),
            )
        )
        survey_df.to_csv(INTERMEDIATE_ROOT / "care_compare_survey_summary_year.csv", index=False)

    health_df = pd.DataFrame()
    if health_path.exists():
        chunks: list[pd.DataFrame] = []
        for chunk in read_csv_flexible(health_path, dtype=str, chunksize=250_000, on_bad_lines="skip"):
            chunk["ccn_str"] = canonical_ccn(chunk["CMS Certification Number (CCN)"])
            chunk["survey_date"] = pd.to_datetime(chunk["Survey Date"], errors="coerce")
            chunk["year"] = chunk["survey_date"].dt.year
            sev = chunk["Scope Severity Code"].astype("string").str.upper().str[-1]
            chunk["actual_harm_or_ij"] = sev.isin(list("GHIJKL"))
            chunk["standard_flag"] = chunk["Standard Deficiency"].astype("string").str.upper().isin(["Y", "YES", "TRUE", "1"])
            chunk["complaint_flag"] = chunk["Complaint Deficiency"].astype("string").str.upper().isin(["Y", "YES", "TRUE", "1"])
            chunk["infection_flag"] = chunk["Infection Control Inspection Deficiency"].astype("string").str.upper().isin(["Y", "YES", "TRUE", "1"])
            chunks.append(
                chunk.groupby(["ccn_str", "year"], as_index=False)
                .agg(
                    deficiency_citations=("ccn_str", "size"),
                    deficiency_standard_citations=("standard_flag", "sum"),
                    deficiency_complaint_citations=("complaint_flag", "sum"),
                    deficiency_infection_control_citations=("infection_flag", "sum"),
                    deficiency_actual_harm_or_ij_citations=("actual_harm_or_ij", "sum"),
                    deficiency_unique_survey_dates=("survey_date", pd.Series.nunique),
                )
            )
        if chunks:
            health_df = (
                pd.concat(chunks, ignore_index=True)
                .groupby(["ccn_str", "year"], as_index=False)
                .sum()
            )
            health_df.to_csv(INTERMEDIATE_ROOT / "care_compare_health_deficiencies_year.csv", index=False)
    return provider_df, survey_df, health_df


def first_existing_path(root: Path, patterns: list[str]) -> Path | None:
    for pattern in patterns:
        matches = sorted(root.glob(pattern))
        if matches:
            return matches[0]
    return None


def normalize_care_compare_provider_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "provnum": "CMS Certification Number (CCN)",
        "PROVNUM": "CMS Certification Number (CCN)",
        "Provider Number": "CMS Certification Number (CCN)",
        "Federal Provider Number": "CMS Certification Number (CCN)",
        "PROVNAME": "Provider Name",
        "Provname": "Provider Name",
        "CITY": "City/Town",
        "ZIP": "ZIP Code",
        "OWNERSHIP": "Ownership Type",
        "BEDCERT": "Number of Certified Beds",
        "RESTOT": "Average Number of Residents per Day",
        "LBN": "Legal Business Name",
        "AFFILIATED ENTITY NAME": "Chain Name",
        "AFFILIATED ENTITY ID": "Chain ID",
        "Affiliated Entity Name": "Chain Name",
        "Affiliated Entity ID": "Chain ID",
        "overall_rating": "Overall Rating",
        "survey_rating": "Health Inspection Rating",
        "quality_rating": "QM Rating",
        "staffing_rating": "Staffing Rating",
        "RN_staffing_rating": "RN Staffing Rating",
        "RN_STAFFING_RATING": "RN Staffing Rating",
        "TOTHRD": "Reported Total Nurse Staffing Hours per Resident per Day",
        "CHOW_LAST_12MOS": "Provider Changed Ownership in Last 12 Months",
        "WEIGHTED_ALL_CYCLES_SCORE": "Total Weighted Health Survey Score",
        "incident_cnt": "Number of Facility Reported Incidents",
        "INCIDENT_CNT": "Number of Facility Reported Incidents",
        "cmplnt_cnt": "Number of Substantiated Complaints",
        "CMPLNT_CNT": "Number of Substantiated Complaints",
        "FINE_CNT": "Number of Fines",
        "FINE_TOT": "Total Amount of Fines in Dollars",
        "PAYDEN_CNT": "Number of Payment Denials",
        "TOT_PENLTY_CNT": "Total Number of Penalties",
        "FILEDATE": "Processing Date",
        "filedate": "Processing Date",
        "R_TOT_HTH_DFCNCY": "Rating Cycle 1 Total Number of Health Deficiencies",
    }
    out = df.rename(columns=rename_map).copy()
    required = [
        "CMS Certification Number (CCN)",
        "Provider Name",
        "State",
        "Ownership Type",
        "Number of Certified Beds",
        "Average Number of Residents per Day",
        "Legal Business Name",
        "Chain Name",
        "Chain ID",
        "Overall Rating",
        "Health Inspection Rating",
        "QM Rating",
        "Staffing Rating",
        "RN Staffing Rating",
        "Reported Total Nurse Staffing Hours per Resident per Day",
        "Provider Changed Ownership in Last 12 Months",
        "Total Weighted Health Survey Score",
        "Number of Facility Reported Incidents",
        "Number of Substantiated Complaints",
        "Number of Citations from Infection Control Inspections",
        "Number of Fines",
        "Total Amount of Fines in Dollars",
        "Number of Payment Denials",
        "Total Number of Penalties",
        "Processing Date",
    ]
    for col in required:
        if col not in out.columns:
            out[col] = pd.NA
    if "Chain Name" in out.columns and "Affiliated Entity Name" in df.columns:
        out["Chain Name"] = out["Chain Name"].fillna(df["Affiliated Entity Name"])
    if "Chain ID" in out.columns and "Affiliated Entity ID" in df.columns:
        out["Chain ID"] = out["Chain ID"].fillna(df["Affiliated Entity ID"])
    return out


def parse_care_compare_provider_history() -> pd.DataFrame:
    provider_rows: list[pd.DataFrame] = []
    if not CARE_COMPARE_ARCHIVE_ROOT.exists():
        return pd.DataFrame()

    for year_dir in sorted(CARE_COMPARE_ARCHIVE_ROOT.glob("[0-9][0-9][0-9][0-9]")):
        snapshot_year = int(year_dir.name)
        provider_path = first_existing_path(
            year_dir,
            ["NH_ProviderInfo_*.csv", "ProviderInfo_Download.csv", "ProviderInfo_*.csv"],
        )
        if provider_path is None:
            continue
        provider_raw = read_csv_flexible(provider_path, dtype=str)
        provider_raw = normalize_care_compare_provider_columns(provider_raw)
        provider_raw["ccn_str"] = canonical_ccn(provider_raw["CMS Certification Number (CCN)"])
        provider_raw["year"] = snapshot_year
        keep = [
            "ccn_str",
            "year",
            "Provider Name",
            "State",
            "Ownership Type",
            "Number of Certified Beds",
            "Average Number of Residents per Day",
            "Legal Business Name",
            "Chain Name",
            "Chain ID",
            "Overall Rating",
            "Health Inspection Rating",
            "QM Rating",
            "Staffing Rating",
            "RN Staffing Rating",
            "Reported Total Nurse Staffing Hours per Resident per Day",
            "Provider Changed Ownership in Last 12 Months",
            "Total Weighted Health Survey Score",
            "Number of Facility Reported Incidents",
            "Number of Substantiated Complaints",
            "Number of Citations from Infection Control Inspections",
            "Number of Fines",
            "Total Amount of Fines in Dollars",
            "Number of Payment Denials",
            "Total Number of Penalties",
            "Processing Date",
        ]
        provider_year = provider_raw[keep].copy()
        provider_year = provider_year.dropna(subset=["ccn_str"]).copy()
        provider_year = (
            provider_year.sort_values(["ccn_str", "year"])
            .drop_duplicates(subset=["ccn_str", "year"], keep="first")
            .reset_index(drop=True)
        )
        provider_rows.append(provider_year)

    if not provider_rows:
        return pd.DataFrame()
    provider_df = (
        pd.concat(provider_rows, ignore_index=True)
        .sort_values(["ccn_str", "year"])
        .reset_index(drop=True)
    )
    provider_df.to_csv(INTERMEDIATE_ROOT / "care_compare_provider_info_year.csv", index=False)
    latest = provider_df.loc[provider_df["year"] == provider_df["year"].max()].copy()
    latest.to_csv(INTERMEDIATE_ROOT / "care_compare_provider_info_latest.csv", index=False)
    return provider_df


def normalize_care_compare_health_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "PROVNUM": "CMS Certification Number (CCN)",
        "provnum": "CMS Certification Number (CCN)",
        "Federal Provider Number": "CMS Certification Number (CCN)",
        "SURVEY_DATE_OUTPUT": "Survey Date",
        "survey_date_output": "Survey Date",
        "cycle": "Inspection Cycle",
        "TAG": "Deficiency Tag Number",
        "tag": "Deficiency Tag Number",
        "DEFPREF": "Deficiency Prefix",
        "defpref": "Deficiency Prefix",
        "CATEGORY": "Deficiency Category",
        "SCOPE": "Scope Severity Code",
        "scope": "Scope Severity Code",
        "Standard": "Standard Deficiency",
        "standard": "Standard Deficiency",
        "Complaint": "Complaint Deficiency",
        "complaint": "Complaint Deficiency",
    }
    out = df.rename(columns=rename_map).copy()
    required = [
        "CMS Certification Number (CCN)",
        "Survey Date",
        "Inspection Cycle",
        "Deficiency Tag Number",
        "Deficiency Prefix",
        "Deficiency Category",
        "Scope Severity Code",
        "Standard Deficiency",
        "Complaint Deficiency",
        "Infection Control Inspection Deficiency",
    ]
    for col in required:
        if col not in out.columns:
            out[col] = pd.NA
    return out


def normalize_care_compare_survey_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "PROVNUM": "CMS Certification Number (CCN)",
        "Federal Provider Number": "CMS Certification Number (CCN)",
        "cycle": "Inspection Cycle",
        "H_SURVEY_DATE": "Health Survey Date",
        "F_SURVEY_DATE": "Fire Safety Survey Date",
        "H_TOT_DFCNCY": "Total Number of Health Deficiencies",
        "F_TOT_DFCNCY": "Total Number of Fire Safety Deficiencies",
    }
    out = df.rename(columns=rename_map).copy()
    required = [
        "CMS Certification Number (CCN)",
        "Inspection Cycle",
        "Health Survey Date",
        "Fire Safety Survey Date",
        "Total Number of Health Deficiencies",
        "Total Number of Fire Safety Deficiencies",
        "Count of Infection Control Deficiencies",
    ]
    for col in required:
        if col not in out.columns:
            out[col] = pd.NA
    return out


def parse_care_compare_archived_history() -> tuple[pd.DataFrame, pd.DataFrame]:
    survey_rows: list[pd.DataFrame] = []
    health_rows: list[pd.DataFrame] = []
    if not CARE_COMPARE_ARCHIVE_ROOT.exists():
        return pd.DataFrame(), pd.DataFrame()

    for year_dir in sorted(CARE_COMPARE_ARCHIVE_ROOT.glob("[0-9][0-9][0-9][0-9]")):
        snapshot_year = int(year_dir.name)

        survey_path = first_existing_path(
            year_dir,
            ["NH_SurveySummary_*.csv", "SurveySummary_Download.csv"],
        )
        if survey_path is not None:
            survey_raw = read_csv_flexible(survey_path, dtype=str)
            survey_raw = normalize_care_compare_survey_columns(survey_raw)
            survey_raw["ccn_str"] = canonical_ccn(survey_raw["CMS Certification Number (CCN)"])
            survey_raw["health_survey_date"] = pd.to_datetime(survey_raw["Health Survey Date"], errors="coerce")
            survey_raw["fire_safety_survey_date"] = pd.to_datetime(
                survey_raw["Fire Safety Survey Date"], errors="coerce"
            )
            survey_raw["year"] = survey_raw["health_survey_date"].dt.year
            survey_raw = survey_raw.loc[survey_raw["year"] == snapshot_year].copy()
            for col in [
                "Total Number of Health Deficiencies",
                "Total Number of Fire Safety Deficiencies",
                "Count of Infection Control Deficiencies",
            ]:
                survey_raw[col] = pd.to_numeric(survey_raw[col], errors="coerce")
            if not survey_raw.empty:
                survey_rows.append(
                    survey_raw.dropna(subset=["ccn_str", "year"])
                    .groupby(["ccn_str", "year"], as_index=False)
                    .agg(
                        survey_summary_rows=("Inspection Cycle", "size"),
                        survey_summary_total_health_deficiencies=(
                            "Total Number of Health Deficiencies",
                            "sum",
                        ),
                        survey_summary_total_fire_safety_deficiencies=(
                            "Total Number of Fire Safety Deficiencies",
                            "sum",
                        ),
                        survey_summary_infection_control_deficiencies=(
                            "Count of Infection Control Deficiencies",
                            lambda s: s.sum(min_count=1),
                        ),
                    )
                )

        health_path = first_existing_path(
            year_dir,
            [
                "NH_HealthCitations_*.csv",
                "HealthDeficiencies_Download.csv",
                "Deficiencies_Download.csv",
                "Deficiencies_*.csv",
            ],
        )
        if health_path is not None:
            chunk_aggs: list[pd.DataFrame] = []
            for chunk in read_csv_flexible(health_path, dtype=str, chunksize=250_000, on_bad_lines="skip"):
                chunk = normalize_care_compare_health_columns(chunk)
                chunk["ccn_str"] = canonical_ccn(chunk["CMS Certification Number (CCN)"])
                chunk["survey_date"] = pd.to_datetime(chunk["Survey Date"], errors="coerce")
                chunk["year"] = chunk["survey_date"].dt.year
                chunk = chunk.loc[chunk["year"] == snapshot_year].copy()
                if chunk.empty:
                    continue
                sev = chunk["Scope Severity Code"].astype("string").str.upper().str[-1]
                chunk["actual_harm_or_ij"] = sev.isin(list("GHIJKL")).astype(int)
                chunk["standard_flag"] = (
                    chunk["Standard Deficiency"].astype("string").str.upper().isin(["Y", "YES", "TRUE", "1"]).astype(int)
                )
                chunk["complaint_flag"] = (
                    chunk["Complaint Deficiency"].astype("string").str.upper().isin(["Y", "YES", "TRUE", "1"]).astype(int)
                )
                infection_series = chunk["Infection Control Inspection Deficiency"].astype("string")
                has_infection_field = infection_series.notna().any()
                if has_infection_field:
                    chunk["infection_flag"] = infection_series.str.upper().isin(["Y", "YES", "TRUE", "1"]).astype(int)
                else:
                    chunk["infection_flag"] = pd.Series(pd.NA, index=chunk.index, dtype="Float64")
                chunk_aggs.append(
                    chunk.dropna(subset=["ccn_str", "year"])
                    .groupby(["ccn_str", "year"], as_index=False)
                    .agg(
                        deficiency_citations=("ccn_str", "size"),
                        deficiency_standard_citations=("standard_flag", "sum"),
                        deficiency_complaint_citations=("complaint_flag", "sum"),
                        deficiency_infection_control_citations=("infection_flag", lambda s: s.sum(min_count=1)),
                        deficiency_actual_harm_or_ij_citations=("actual_harm_or_ij", "sum"),
                        deficiency_unique_survey_dates=("survey_date", pd.Series.nunique),
                    )
                )
            if chunk_aggs:
                health_rows.append(
                    pd.concat(chunk_aggs, ignore_index=True)
                    .groupby(["ccn_str", "year"], as_index=False)
                    .agg(
                        deficiency_citations=("deficiency_citations", "sum"),
                        deficiency_standard_citations=("deficiency_standard_citations", "sum"),
                        deficiency_complaint_citations=("deficiency_complaint_citations", "sum"),
                        deficiency_infection_control_citations=(
                            "deficiency_infection_control_citations",
                            lambda s: s.sum(min_count=1),
                        ),
                        deficiency_actual_harm_or_ij_citations=(
                            "deficiency_actual_harm_or_ij_citations",
                            "sum",
                        ),
                        deficiency_unique_survey_dates=("deficiency_unique_survey_dates", "sum"),
                    )
                )

    survey_df = (
        pd.concat(survey_rows, ignore_index=True).sort_values(["ccn_str", "year"]).reset_index(drop=True)
        if survey_rows
        else pd.DataFrame()
    )
    health_df = (
        pd.concat(health_rows, ignore_index=True).sort_values(["ccn_str", "year"]).reset_index(drop=True)
        if health_rows
        else pd.DataFrame()
    )
    return survey_df, health_df


def load_treated_sample() -> pd.DataFrame:
    df = pd.read_csv(RESEARCH_ROOT / "pe_facility_verification.csv", dtype=str)
    treated = df[(df["transition_verified"] == "yes") & (df["transition_type"] == "non_pe_to_pe")].copy()
    treated["ccn_str"] = canonical_ccn(treated["ccn"])
    treated["treat_year"] = (
        treated["ownership_effective_date"]
        .astype("string")
        .str.extract(r"(20\d{2})", expand=False)
        .astype("float")
    )
    treated = treated[["ccn_str", "facility_name", "deal_id", "state", "treat_year", "verification_tier"]].drop_duplicates()
    treated["verified_treated"] = 1
    return treated


def build_master(
    form671_year: pd.DataFrame,
    owners_year: pd.DataFrame,
    chow_year: pd.DataFrame,
    pbj_year: pd.DataFrame,
    provider_year: pd.DataFrame,
    health_year: pd.DataFrame,
    enrollments_monthly: pd.DataFrame,
    treated: pd.DataFrame,
) -> pd.DataFrame:
    def valid_ccn_rows(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or "ccn_str" not in df.columns:
            return df
        return df.loc[df["ccn_str"].notna() & ~df["ccn_str"].isin(["000000", "0"])].copy()

    form671_year = valid_ccn_rows(form671_year)
    owners_year = valid_ccn_rows(owners_year)
    chow_year = valid_ccn_rows(chow_year)
    pbj_year = valid_ccn_rows(pbj_year)
    provider_year = valid_ccn_rows(provider_year)
    health_year = valid_ccn_rows(health_year)
    enrollments_monthly = valid_ccn_rows(enrollments_monthly)
    treated = valid_ccn_rows(treated)

    frames: list[pd.DataFrame] = []
    enroll_year = (
        enrollments_monthly.groupby(["ccn_str", "snapshot_year"], as_index=False)
        .agg(enrollment_snapshots=("snapshot_date", "nunique"))
        .rename(columns={"snapshot_year": "year"})
    )
    frames.extend(
        [
            form671_year[["ccn_str", "year"]],
            owners_year[["ccn_str", "year"]],
            chow_year[["ccn_str", "year"]],
            pbj_year[["ccn_str", "year"]],
            provider_year[["ccn_str", "year"]] if not provider_year.empty else pd.DataFrame(columns=["ccn_str", "year"]),
            health_year[["ccn_str", "year"]] if not health_year.empty else pd.DataFrame(columns=["ccn_str", "year"]),
            enroll_year[["ccn_str", "year"]],
            treated[["ccn_str", "treat_year"]].rename(columns={"treat_year": "year"}).dropna(),
        ]
    )
    master = (
        pd.concat(frames, ignore_index=True)
        .dropna()
        .drop_duplicates()
        .sort_values(["ccn_str", "year"])
    )
    master = valid_ccn_rows(master)

    def merge_flag(df: pd.DataFrame, name: str) -> None:
        nonlocal master
        if df.empty:
            master[name] = 0
            return
        merged = df[["ccn_str", "year"]].drop_duplicates().copy()
        merged[name] = 1
        master = master.merge(merged, on=["ccn_str", "year"], how="left")
        master[name] = master[name].fillna(0).astype(int)

    merge_flag(form671_year, "has_form671")
    merge_flag(owners_year, "has_owner_snapshot")
    merge_flag(chow_year, "has_chow_event")
    merge_flag(pbj_year, "has_pbj_nurse")
    merge_flag(provider_year, "has_provider_info")
    master["has_provider_info_latest"] = master["has_provider_info"]
    merge_flag(health_year, "has_health_deficiency")
    merge_flag(enroll_year, "has_enrollment_snapshot")

    for df in [form671_year, owners_year, chow_year, pbj_year, provider_year, health_year, enroll_year]:
        if not df.empty:
            extra_cols = [c for c in df.columns if c not in {"ccn_str", "year"}]
            if extra_cols:
                source_df = collapse_unique_facility_year(df)
                master = master.merge(source_df, on=["ccn_str", "year"], how="left")

    master = master.merge(treated, on="ccn_str", how="left")
    master["verified_treated"] = master["verified_treated"].fillna(0).astype(int)
    master["post_treatment_year"] = (
        (master["verified_treated"] == 1)
        & master["treat_year"].notna()
        & (master["year"] >= master["treat_year"])
    ).astype(int)
    master["year"] = master["year"].astype("Int64")
    master = collapse_unique_facility_year(master)
    master.to_csv(INTERMEDIATE_ROOT / "cms_facility_year_foundation.csv", index=False)
    return master


def build_qa_summary(
    inventory: pd.DataFrame,
    form671_year: pd.DataFrame,
    owners_year: pd.DataFrame,
    chow_year: pd.DataFrame,
    pbj_year: pd.DataFrame,
    provider_year: pd.DataFrame,
    health_year: pd.DataFrame,
    master: pd.DataFrame,
) -> None:
    pbj_manifest = read_manifest(MANIFEST_ROOT / "pbj_nurse_manifest.csv")
    pbj_present = len(list((CMS_ROOT / "pbj_nurse").glob("*.csv")))
    summary = {
        "inventory_rows": int(len(inventory)),
        "form671_year_rows": int(len(form671_year)),
        "owners_year_rows": int(len(owners_year)),
        "chow_year_rows": int(len(chow_year)),
        "pbj_year_rows": int(len(pbj_year)),
        "provider_year_rows": int(len(provider_year)),
        "health_year_rows": int(len(health_year)),
        "master_rows": int(len(master)),
        "master_unique_facilities": int(master["ccn_str"].nunique()),
        "master_year_min": int(master["year"].min()) if not master.empty else None,
        "master_year_max": int(master["year"].max()) if not master.empty else None,
        "pbj_nurse_files_present": int(pbj_present),
        "pbj_nurse_files_expected_from_manifest": int(len(pbj_manifest)),
        "pbj_nurse_partial_download": bool(pbj_present < len(pbj_manifest)),
    }
    with open(INTERMEDIATE_ROOT / "cms_foundation_qa_summary.json", "w") as fh:
        json.dump(summary, fh, indent=2)


def main() -> None:
    ensure_dir(INTERMEDIATE_ROOT)
    inventory = build_inventory()
    form671_year = parse_form671()
    enrollments_monthly = parse_snf_enrollments_monthly()
    owners_year = parse_snf_all_owners_monthly(enrollments_monthly)
    chow_year = parse_snf_chow()
    pbj_year = parse_pbj_nurse()
    _provider_latest, survey_latest, health_latest = parse_care_compare_latest()
    provider_year = parse_care_compare_provider_history()
    archived_survey_year, archived_health_year = parse_care_compare_archived_history()
    survey_pre2019 = survey_latest.loc[survey_latest["year"] < 2019].copy() if not survey_latest.empty else pd.DataFrame()
    health_pre2019 = health_latest.loc[health_latest["year"] < 2019].copy() if not health_latest.empty else pd.DataFrame()
    survey_year = (
        pd.concat([survey_pre2019, archived_survey_year], ignore_index=True)
        .sort_values(["ccn_str", "year"])
        .reset_index(drop=True)
        if not survey_pre2019.empty or not archived_survey_year.empty
        else pd.DataFrame()
    )
    health_year = (
        pd.concat([health_pre2019, archived_health_year], ignore_index=True)
        .sort_values(["ccn_str", "year"])
        .reset_index(drop=True)
        if not health_pre2019.empty or not archived_health_year.empty
        else pd.DataFrame()
    )
    if not survey_year.empty:
        survey_year = collapse_unique_facility_year(survey_year)
        survey_year.to_csv(INTERMEDIATE_ROOT / "care_compare_survey_summary_year.csv", index=False)
    if not health_year.empty:
        health_year = collapse_unique_facility_year(health_year)
        health_year.to_csv(INTERMEDIATE_ROOT / "care_compare_health_deficiencies_year.csv", index=False)
    treated = load_treated_sample()
    master = build_master(
        form671_year=form671_year,
        owners_year=owners_year,
        chow_year=chow_year,
        pbj_year=pbj_year,
        provider_year=provider_year,
        health_year=health_year,
        enrollments_monthly=enrollments_monthly,
        treated=treated,
    )
    if not survey_year.empty:
        master = master.merge(survey_year, on=["ccn_str", "year"], how="left")
        master["has_survey_summary"] = master["survey_summary_rows"].notna().astype(int)
        master = collapse_unique_facility_year(master)
        master.to_csv(INTERMEDIATE_ROOT / "cms_facility_year_foundation.csv", index=False)
    build_qa_summary(
        inventory=inventory,
        form671_year=form671_year,
        owners_year=owners_year,
        chow_year=chow_year,
        pbj_year=pbj_year,
        provider_year=provider_year,
        health_year=health_year,
        master=master,
    )
    print("Wrote CMS facility-year foundation outputs to", INTERMEDIATE_ROOT)


if __name__ == "__main__":
    main()
