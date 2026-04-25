#!/usr/bin/env python3
"""Refresh the historical CMS provider panel and downstream files."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import build_control_candidate_pools as control_builder
import build_treated_sample_panels as treated_builder
from build_cms_foundation_panel import ROOT, parse_care_compare_provider_history


from utils import get_intermediate_dir, get_output_dir

CMS_DIR = get_intermediate_dir(ROOT) / "cms"


def refresh_master(provider_year: pd.DataFrame) -> pd.DataFrame:
    master_path = CMS_DIR / "cms_facility_year_foundation.csv"
    master = pd.read_csv(master_path, dtype={"ccn_str": str}, low_memory=False)
    if master.duplicated(["ccn_str", "year"]).sum() != 0:
        raise ValueError("Existing CMS foundation is not unique on ccn_str x year")
    if provider_year.duplicated(["ccn_str", "year"]).sum() != 0:
        raise ValueError("Provider history is not unique on ccn_str x year")

    provider_cols = [c for c in provider_year.columns if c not in {"ccn_str", "year"}]
    drop_cols = [c for c in provider_cols if c in master.columns]
    drop_cols.extend([c for c in ["has_provider_info", "has_provider_info_latest"] if c in master.columns])
    base = master.drop(columns=drop_cols)

    key_frames = [master[["ccn_str", "year"]], provider_year[["ccn_str", "year"]]]
    keys = (
        pd.concat(key_frames, ignore_index=True)
        .dropna(subset=["ccn_str", "year"])
        .drop_duplicates()
        .sort_values(["ccn_str", "year"])
        .reset_index(drop=True)
    )

    refreshed = keys.merge(base, on=["ccn_str", "year"], how="left")
    refreshed = refreshed.merge(provider_year, on=["ccn_str", "year"], how="left")
    refreshed["has_provider_info"] = refreshed["Provider Name"].notna().astype(int)
    refreshed["has_provider_info_latest"] = refreshed["has_provider_info"]

    if refreshed.duplicated(["ccn_str", "year"]).sum() != 0:
        raise ValueError("Refreshed CMS foundation is not unique on ccn_str x year")

    refreshed.to_csv(master_path, index=False)
    summary_path = CMS_DIR / "cms_foundation_qa_summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    summary.update(
        {
            "provider_year_rows": int(len(provider_year)),
            "master_rows": int(len(refreshed)),
            "master_unique_facilities": int(refreshed["ccn_str"].nunique()),
            "master_year_min": int(pd.to_numeric(refreshed["year"], errors="coerce").min()),
            "master_year_max": int(pd.to_numeric(refreshed["year"], errors="coerce").max()),
            "master_duplicate_ccn_year_rows": int(refreshed.duplicated(["ccn_str", "year"]).sum()),
        }
    )
    summary_path.write_text(json.dumps(summary, indent=2))
    return refreshed


def main() -> None:
    provider_year = parse_care_compare_provider_history()
    if provider_year.empty:
        raise ValueError("No archived provider history found")
    refresh_master(provider_year)
    control_builder.main()
    treated_builder.main()
    print("Refreshed archived provider info history and downstream files in", CMS_DIR)


if __name__ == "__main__":
    main()
