#!/usr/bin/env python3
"""Refresh the historical CMS deficiency intermediates and downstream files."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import build_control_candidate_pools as control_builder
import build_treated_sample_panels as treated_builder
from build_cms_foundation_panel import (
    INTERMEDIATE_ROOT,
    ROOT,
    parse_care_compare_archived_history,
    parse_care_compare_latest,
)


from utils import get_intermediate_dir, get_output_dir

CMS_DIR = get_intermediate_dir(ROOT) / "cms"


def combine_deficiency_history() -> tuple[pd.DataFrame, pd.DataFrame]:
    _, survey_latest, health_latest = parse_care_compare_latest()
    archived_survey, archived_health = parse_care_compare_archived_history()

    archived_survey_years = set(pd.to_numeric(archived_survey["year"], errors="coerce").dropna().astype(int).unique()) if not archived_survey.empty else set()
    archived_health_years = set(pd.to_numeric(archived_health["year"], errors="coerce").dropna().astype(int).unique()) if not archived_health.empty else set()
    survey_pre_archive = (
        survey_latest.loc[~pd.to_numeric(survey_latest["year"], errors="coerce").isin(archived_survey_years)].copy()
        if not survey_latest.empty
        else pd.DataFrame()
    )
    health_pre_archive = (
        health_latest.loc[~pd.to_numeric(health_latest["year"], errors="coerce").isin(archived_health_years)].copy()
        if not health_latest.empty
        else pd.DataFrame()
    )

    survey_year = (
        pd.concat([survey_pre_archive, archived_survey], ignore_index=True)
        if not survey_pre_archive.empty or not archived_survey.empty
        else pd.DataFrame()
    )
    health_year = (
        pd.concat([health_pre_archive, archived_health], ignore_index=True)
        if not health_pre_archive.empty or not archived_health.empty
        else pd.DataFrame()
    )

    if not survey_year.empty:
        if survey_year.duplicated(["ccn_str", "year"]).sum() != 0:
            raise ValueError("Combined survey summary panel is not unique on ccn_str x year")
        survey_year.to_csv(CMS_DIR / "care_compare_survey_summary_year.csv", index=False)
    if not health_year.empty:
        if health_year.duplicated(["ccn_str", "year"]).sum() != 0:
            raise ValueError("Combined health deficiency panel is not unique on ccn_str x year")
        health_year.to_csv(CMS_DIR / "care_compare_health_deficiencies_year.csv", index=False)

    return survey_year, health_year


def refresh_master(survey_year: pd.DataFrame, health_year: pd.DataFrame) -> pd.DataFrame:
    master_path = CMS_DIR / "cms_facility_year_foundation.csv"
    master = pd.read_csv(master_path, dtype={"ccn_str": str}, low_memory=False)

    key_frames = [master[["ccn_str", "year"]]]
    if not survey_year.empty:
        key_frames.append(survey_year[["ccn_str", "year"]])
    if not health_year.empty:
        key_frames.append(health_year[["ccn_str", "year"]])
    keys = (
        pd.concat(key_frames, ignore_index=True)
        .dropna(subset=["ccn_str", "year"])
        .drop_duplicates()
        .sort_values(["ccn_str", "year"])
        .reset_index(drop=True)
    )

    drop_cols = [
        "has_health_deficiency",
        "has_survey_summary",
        "deficiency_citations",
        "deficiency_standard_citations",
        "deficiency_complaint_citations",
        "deficiency_infection_control_citations",
        "deficiency_actual_harm_or_ij_citations",
        "deficiency_unique_survey_dates",
        "survey_summary_rows",
        "survey_summary_total_health_deficiencies",
        "survey_summary_total_fire_safety_deficiencies",
        "survey_summary_infection_control_deficiencies",
    ]
    existing_cols = [c for c in drop_cols if c in master.columns]
    base = master.drop(columns=existing_cols)
    if master.duplicated(["ccn_str", "year"]).sum() != 0:
        raise ValueError("Existing CMS foundation is not unique on ccn_str x year")
    refreshed = keys.merge(base, on=["ccn_str", "year"], how="left")

    if not health_year.empty:
        if health_year.duplicated(["ccn_str", "year"]).sum() != 0:
            raise ValueError("Health deficiency panel is not unique on ccn_str x year")
        refreshed = refreshed.merge(health_year, on=["ccn_str", "year"], how="left")
        refreshed["has_health_deficiency"] = refreshed["deficiency_citations"].notna().astype(int)
    else:
        refreshed["has_health_deficiency"] = 0

    if not survey_year.empty:
        if survey_year.duplicated(["ccn_str", "year"]).sum() != 0:
            raise ValueError("Survey summary panel is not unique on ccn_str x year")
        refreshed = refreshed.merge(survey_year, on=["ccn_str", "year"], how="left")
        refreshed["has_survey_summary"] = refreshed["survey_summary_rows"].notna().astype(int)
    else:
        refreshed["has_survey_summary"] = 0

    if refreshed.duplicated(["ccn_str", "year"]).sum() != 0:
        raise ValueError("Refreshed CMS foundation is not unique on ccn_str x year")
    refreshed.to_csv(master_path, index=False)
    return refreshed


def refresh_summary(master: pd.DataFrame, health_year: pd.DataFrame) -> None:
    summary_path = CMS_DIR / "cms_foundation_qa_summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text())
    else:
        summary = {}
    summary.update(
        {
            "health_year_rows": int(len(health_year)),
            "master_rows": int(len(master)),
            "master_unique_facilities": int(master["ccn_str"].nunique()),
            "master_year_min": int(master["year"].min()) if not master.empty else None,
            "master_year_max": int(master["year"].max()) if not master.empty else None,
            "master_duplicate_ccn_year_rows": int(master.duplicated(["ccn_str", "year"]).sum()),
        }
    )
    summary_path.write_text(json.dumps(summary, indent=2))


def main() -> None:
    survey_year, health_year = combine_deficiency_history()
    master = refresh_master(survey_year, health_year)
    refresh_summary(master, health_year)
    control_builder.main()
    treated_builder.main()
    print("Refreshed archived Care Compare deficiency history and downstream files in", INTERMEDIATE_ROOT)


if __name__ == "__main__":
    main()
