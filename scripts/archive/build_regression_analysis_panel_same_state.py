#!/usr/bin/env python3
"""Build the same-state regression-ready facility-year analysis panel.

This mirrors the main gold_main/v2 analysis panel but restricts controls to the
treated states only using the curated same-state control pool.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from pandas.api.types import is_object_dtype, is_string_dtype


ROOT = Path(__file__).resolve().parents[1]
CMS_DIR = ROOT / "data" / "intermediate" / "cms"
LTCFOCUS_DIR = ROOT / "data" / "intermediate" / "ltcfocus"
ANALYSIS_DIR = ROOT / "data" / "intermediate" / "analysis"
PANELS_DIR = ANALYSIS_DIR / "panels"
RESEARCH_DIR = ROOT / "research"

CMS_FOUNDATION_PATH = CMS_DIR / "cms_facility_year_foundation.csv"
CONTROL_PATH = CMS_DIR / "clean_control_candidates_v2_same_state.csv"
TREATMENT_PATH = RESEARCH_DIR / "pe_facility_verification.csv"
BASELINE_PATH = LTCFOCUS_DIR / "ltcfocus_medicaid_baseline_inputs.csv"

OUTPUT_CSV = PANELS_DIR / "regression_analysis_panel_gold_v2_same_state.csv"
OUTPUT_DTA = PANELS_DIR / "regression_analysis_panel_gold_v2_same_state.dta"
SUMMARY_JSON = PANELS_DIR / "regression_analysis_panel_gold_v2_same_state_summary.json"


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
    return int(match.group(1)) if match else None


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


def first_nonmissing(series: pd.Series):
    nonmissing = series.dropna()
    if len(nonmissing) == 0:
        return pd.NA
    return nonmissing.iloc[0]


def collapse_facility_year(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    return (
        df.sort_values(["ccn_str", "year"])
        .groupby(["ccn_str", "year"], as_index=False, dropna=False)
        .agg(first_nonmissing)
        .sort_values(["ccn_str", "year"])
        .reset_index(drop=True)
    )


def load_treatment_gold() -> pd.DataFrame:
    df = pd.read_csv(TREATMENT_PATH, dtype="string").fillna(pd.NA)
    df["ccn_str"] = df["ccn"].map(canonical_ccn).astype("string")
    df["treat_year"] = df["ownership_effective_date"].map(extract_treat_year).astype("Int64")
    df = df[df["analysis_sample"].eq("gold_main") & df["ccn_str"].notna()].copy()
    keep = [
        "ccn_str",
        "facility_name",
        "deal_id",
        "pe_firm",
        "platform_name",
        "state",
        "city",
        "transition_type",
        "transition_verified",
        "verification_tier",
        "ownership_effective_date",
        "treat_year",
    ]
    df = df[keep].drop_duplicates(subset=["ccn_str"]).copy()
    return df.rename(
        columns={
            "facility_name": "facility_name_treatment",
            "state": "state_treatment",
            "city": "city_treatment",
        }
    )


def load_controls() -> pd.DataFrame:
    df = pd.read_csv(CONTROL_PATH, dtype={"ccn_str": "string"}, low_memory=False)
    df["ccn_str"] = df["ccn_str"].map(canonical_ccn).astype("string")
    df = df[df["control_v2_eligible"].eq(1) & df["ccn_str"].notna()].copy()
    keep = [
        "ccn_str",
        "provider_name_latest",
        "state_latest",
        "ownership_type_latest",
        "chain_name_latest",
        "chain_id_latest",
        "panel_years",
        "years_with_form671",
        "years_with_pbj_nurse",
        "control_v2_eligible",
        "control_v2_staffing_eligible",
        "control_v2_deficiency_eligible",
    ]
    return df[keep].drop_duplicates(subset=["ccn_str"]).copy()


def load_baseline_gold_v2() -> pd.DataFrame:
    df = pd.read_csv(BASELINE_PATH, dtype={"ccn_str": "string"}, low_memory=False)
    df["ccn_str"] = df["ccn_str"].map(canonical_ccn).astype("string")
    df = df[df["baseline_spec"].eq("gold_main_v2") & df["ccn_str"].notna()].copy()
    if df.duplicated(["ccn_str"]).any():
        raise ValueError("Baseline gold_main_v2 slice is not unique on ccn_str")
    keep = [
        "ccn_str",
        "baseline_medicaid_share",
        "baseline_medicaid_n_years",
        "baseline_medicare_share",
        "baseline_medicare_n_years",
        "baseline_window_start",
        "baseline_window_end",
        "baseline_method",
        "valid_pseudocohorts",
    ]
    return df[keep].copy()


def load_master() -> pd.DataFrame:
    df = pd.read_csv(CMS_FOUNDATION_PATH, dtype={"ccn_str": "string"}, low_memory=False)
    df["ccn_str"] = df["ccn_str"].map(canonical_ccn).astype("string")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df = df[df["ccn_str"].notna() & df["year"].notna()].copy()
    if df.duplicated(["ccn_str", "year"]).sum() != 0:
        df = collapse_facility_year(df)

    rename_map = {
        "Provider Name": "provider_name",
        "State": "provider_state",
        "Ownership Type": "provider_ownership_type",
        "Number of Certified Beds": "provider_certified_beds",
        "Average Number of Residents per Day": "provider_avg_residents_per_day",
        "Legal Business Name": "provider_legal_business_name",
        "Chain Name": "provider_chain_name",
        "Chain ID": "provider_chain_id",
        "Overall Rating": "provider_overall_rating",
        "Health Inspection Rating": "provider_health_rating",
        "QM Rating": "provider_qm_rating",
        "Staffing Rating": "provider_staffing_rating",
        "RN Staffing Rating": "provider_rn_staffing_rating",
        "Reported Total Nurse Staffing Hours per Resident per Day": "provider_reported_staffing_hprd",
        "Provider Changed Ownership in Last 12 Months": "provider_changed_ownership_12m",
        "Total Weighted Health Survey Score": "provider_survey_score",
        "Number of Facility Reported Incidents": "provider_reported_incidents",
        "Number of Substantiated Complaints": "provider_subst_complaints",
        "Number of Citations from Infection Control Inspections": "provider_ic_citations",
        "Number of Fines": "provider_number_of_fines",
        "Total Amount of Fines in Dollars": "provider_total_fines_dollars",
        "Number of Payment Denials": "provider_payment_denials",
        "Total Number of Penalties": "provider_total_penalties",
        "Processing Date": "provider_processing_date",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    keep = [
        "ccn_str",
        "year",
        "has_form671",
        "has_pbj_nurse",
        "has_provider_info",
        "has_provider_info_latest",
        "has_owner_snapshot",
        "has_chow_event",
        "has_enrollment_snapshot",
        "any_private_equity_owner",
        "any_reit_owner",
        "any_trust_owner",
        "any_investment_firm_owner",
        "any_holding_company_owner",
        "any_management_company_owner",
        "form671_total_residents_mean",
        "form671_medicaid_census_mean",
        "form671_medicare_census_mean",
        "form671_medicaid_share_mean",
        "pbj_days_observed",
        "pbj_mean_census",
        "pbj_total_rn_hours",
        "pbj_total_nurse_hours",
        "pbj_mean_rn_hprd",
        "pbj_mean_nurse_hprd",
        "provider_name",
        "provider_state",
        "provider_ownership_type",
        "provider_certified_beds",
        "provider_avg_residents_per_day",
        "provider_legal_business_name",
        "provider_chain_name",
        "provider_chain_id",
        "provider_overall_rating",
        "provider_health_rating",
        "provider_qm_rating",
        "provider_staffing_rating",
        "provider_rn_staffing_rating",
        "provider_reported_staffing_hprd",
        "provider_changed_ownership_12m",
        "provider_survey_score",
        "provider_reported_incidents",
        "provider_subst_complaints",
        "provider_ic_citations",
        "provider_number_of_fines",
        "provider_total_fines_dollars",
        "provider_payment_denials",
        "provider_total_penalties",
        "provider_processing_date",
    ]
    keep = [c for c in keep if c in df.columns]
    return df[keep].copy()


def build_panel() -> pd.DataFrame:
    treatment = load_treatment_gold()
    controls = load_controls()
    baseline = load_baseline_gold_v2()
    master = load_master()

    control_universe = controls[["ccn_str"]].drop_duplicates().copy()
    control_universe["sample_role"] = "control"
    control_universe["analysis_sample_label"] = "control_v2_same_state"
    control_universe["ever_treated"] = 0

    treated_universe = treatment[["ccn_str"]].drop_duplicates().copy()
    treated_universe["sample_role"] = "treated"
    treated_universe["analysis_sample_label"] = "gold_main"
    treated_universe["ever_treated"] = 1

    universe = pd.concat([treated_universe, control_universe], ignore_index=True)

    panel = master.merge(universe, on="ccn_str", how="inner")
    panel = panel.merge(treatment, on="ccn_str", how="left")
    panel = panel.merge(controls, on="ccn_str", how="left")
    panel = panel.merge(baseline, on="ccn_str", how="left")

    panel["analysis_spec"] = "gold_main_v2_same_state"
    panel["has_baseline_medicaid"] = panel["baseline_medicaid_share"].notna().astype(int)
    panel["has_baseline_medicare"] = panel["baseline_medicare_share"].notna().astype(int)

    # Medicare-heavy flag: Top quartile of baseline Medicare share
    medicare_baseline = baseline["baseline_medicare_share"].dropna()
    if not medicare_baseline.empty:
        q75_medicare = medicare_baseline.quantile(0.75)
        panel["high_medicare"] = (panel["baseline_medicare_share"] >= q75_medicare).astype(int)
    else:
        panel["high_medicare"] = 0

    panel["post_treat"] = pd.NA
    treated_mask = panel["ever_treated"].eq(1) & panel["treat_year"].notna()
    panel.loc[treated_mask, "post_treat"] = (
        panel.loc[treated_mask, "year"] >= panel.loc[treated_mask, "treat_year"]
    ).astype("Int64")
    panel["event_time"] = pd.NA
    panel.loc[treated_mask, "event_time"] = (
        panel.loc[treated_mask, "year"] - panel.loc[treated_mask, "treat_year"]
    ).astype("Int64")

    panel["analysis_facility_name"] = panel["facility_name_treatment"].combine_first(
        panel["provider_name"]
    )
    panel["analysis_state"] = panel["state_treatment"].combine_first(
        panel["provider_state"]
    ).combine_first(panel["state_latest"])

    panel["outcome_available_pbj_staffing"] = panel["pbj_mean_nurse_hprd"].notna().astype(int)
    panel["has_provider_staffing_outcome"] = (
        panel["provider_reported_staffing_hprd"].notna().astype(int)
    )
    panel["has_star_rating_outcome"] = panel["provider_health_rating"].notna().astype(int)
    panel["has_form671_payer_mix_outcome"] = (
        panel["form671_medicaid_share_mean"].notna().astype(int)
    )

    panel["sample_main_staffing"] = (
        panel["has_baseline_medicaid"].eq(1) & panel["outcome_available_pbj_staffing"].eq(1)
    ).astype(int)
    panel["sample_provider_staffing"] = (
        panel["has_baseline_medicaid"].eq(1)
        & panel["has_provider_staffing_outcome"].eq(1)
    ).astype(int)
    panel["sample_star_ratings"] = (
        panel["has_baseline_medicaid"].eq(1) & panel["has_star_rating_outcome"].eq(1)
    ).astype(int)
    panel["sample_payer_mix_outcome"] = (
        panel["has_baseline_medicaid"].eq(1)
        & panel["has_form671_payer_mix_outcome"].eq(1)
    ).astype(int)

    ordered_cols = [
        "analysis_spec",
        "sample_role",
        "analysis_sample_label",
        "ccn_str",
        "analysis_facility_name",
        "analysis_state",
        "year",
        "ever_treated",
        "treat_year",
        "post_treat",
        "event_time",
        "deal_id",
        "pe_firm",
        "platform_name",
        "transition_type",
        "transition_verified",
        "verification_tier",
        "ownership_effective_date",
        "baseline_medicaid_share",
        "baseline_medicaid_n_years",
        "baseline_medicare_share",
        "baseline_medicare_n_years",
        "high_medicare",
        "any_private_equity_owner",
        "any_reit_owner",
        "any_trust_owner",
        "any_investment_firm_owner",
        "any_holding_company_owner",
        "any_management_company_owner",
        "baseline_window_start",
        "baseline_window_end",
        "baseline_method",
        "valid_pseudocohorts",
        "has_baseline_medicaid",
        "has_form671",
        "has_pbj_nurse",
        "has_provider_info",
        "has_provider_info_latest",
        "has_owner_snapshot",
        "has_chow_event",
        "has_enrollment_snapshot",
        "control_v2_eligible",
        "control_v2_staffing_eligible",
        "panel_years",
        "years_with_form671",
        "years_with_pbj_nurse",
        "pbj_days_observed",
        "pbj_mean_census",
        "pbj_total_rn_hours",
        "pbj_total_nurse_hours",
        "pbj_mean_rn_hprd",
        "pbj_mean_nurse_hprd",
        "provider_reported_staffing_hprd",
        "provider_staffing_rating",
        "provider_rn_staffing_rating",
        "provider_health_rating",
        "provider_overall_rating",
        "provider_qm_rating",
        "provider_survey_score",
        "provider_reported_incidents",
        "provider_subst_complaints",
        "provider_ic_citations",
        "provider_number_of_fines",
        "provider_total_fines_dollars",
        "provider_payment_denials",
        "provider_total_penalties",
        "provider_changed_ownership_12m",
        "form671_total_residents_mean",
        "form671_medicaid_census_mean",
        "form671_medicare_census_mean",
        "form671_medicaid_share_mean",
        "provider_ownership_type",
        "provider_certified_beds",
        "provider_avg_residents_per_day",
        "provider_legal_business_name",
        "provider_chain_name",
        "provider_chain_id",
        "provider_name",
        "provider_state",
        "facility_name_treatment",
        "state_treatment",
        "city_treatment",
        "provider_processing_date",
        "outcome_available_pbj_staffing",
        "has_provider_staffing_outcome",
        "has_star_rating_outcome",
        "has_form671_payer_mix_outcome",
        "sample_main_staffing",
        "sample_provider_staffing",
        "sample_star_ratings",
        "sample_payer_mix_outcome",
    ]
    cols = [c for c in ordered_cols if c in panel.columns]
    panel = panel[cols].sort_values(["sample_role", "ccn_str", "year"]).reset_index(drop=True)

    if panel.duplicated(["ccn_str", "year"]).any():
        raise ValueError("Same-state regression analysis panel is not unique on ccn_str x year")
    return panel


def main() -> None:
    ensure_dir(ANALYSIS_DIR)
    ensure_dir(PANELS_DIR)
    panel = build_panel()
    export_csv_and_dta(panel, OUTPUT_CSV, OUTPUT_DTA)

    summary = {
        "analysis_spec": "gold_main_v2_same_state",
        "rows": int(len(panel)),
        "unique_facilities": int(panel["ccn_str"].nunique()),
        "treated_facilities": int(panel.loc[panel["ever_treated"].eq(1), "ccn_str"].nunique()),
        "control_facilities": int(panel.loc[panel["ever_treated"].eq(0), "ccn_str"].nunique()),
        "year_min": int(panel["year"].min()) if not panel.empty else None,
        "year_max": int(panel["year"].max()) if not panel.empty else None,
        "facilities_with_baseline_medicaid": int(
            panel.loc[panel["has_baseline_medicaid"].eq(1), "ccn_str"].nunique()
        ),
        "rows_with_pbj_staffing": int(panel["outcome_available_pbj_staffing"].sum()),
        "rows_with_provider_staffing": int(panel["has_provider_staffing_outcome"].sum()),
        "rows_with_star_ratings": int(panel["has_star_rating_outcome"].sum()),
        "rows_with_form671_payer_mix": int(panel["has_form671_payer_mix_outcome"].sum()),
        "rows_in_sample_main_staffing": int(panel["sample_main_staffing"].sum()),
        "rows_in_sample_provider_staffing": int(panel["sample_provider_staffing"].sum()),
        "rows_in_sample_star_ratings": int(panel["sample_star_ratings"].sum()),
        "rows_in_sample_payer_mix_outcome": int(panel["sample_payer_mix_outcome"].sum()),
        "duplicate_ccn_year_rows": int(panel.duplicated(["ccn_str", "year"]).sum()),
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
