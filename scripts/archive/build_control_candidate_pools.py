#!/usr/bin/env python3
"""Build facility-level control candidate pools from the CMS foundation panel.

Rule set for v1:
1. Exclude all verified treated facilities.
2. Exclude any facility with a CHOW event in any observed year.

The output is facility-level, not facility-year, so each CCN appears once with
coverage summaries that support the main and robustness control specifications.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


from utils import get_intermediate_dir, get_output_dir

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CMS_DIR = get_intermediate_dir(PROJECT_ROOT) / "cms"
FOUNDATION_PATH = CMS_DIR / "cms_facility_year_foundation.csv"
PROVIDER_INFO_PATH = CMS_DIR / "care_compare_provider_info_latest.csv"
TREATMENT_PATH = PROJECT_ROOT / "research" / "pe_facility_verification.csv"
OUTPUT_PATH = CMS_DIR / "clean_control_candidates_v1.csv"
SUMMARY_PATH = CMS_DIR / "clean_control_candidates_v1_summary.json"
OUTPUT_V2_PATH = CMS_DIR / "clean_control_candidates_v2.csv"
SUMMARY_V2_PATH = CMS_DIR / "clean_control_candidates_v2_summary.json"
OUTPUT_V2_SAME_STATE_PATH = CMS_DIR / "clean_control_candidates_v2_same_state.csv"
SUMMARY_V2_SAME_STATE_PATH = CMS_DIR / "clean_control_candidates_v2_same_state_summary.json"
OUTPUT_V2_GOLD_SILVER_PATH = CMS_DIR / "clean_control_candidates_v2_gold_plus_silver.csv"
SUMMARY_V2_GOLD_SILVER_PATH = CMS_DIR / "clean_control_candidates_v2_gold_plus_silver_summary.json"
OUTPUT_V2_GOLD_SILVER_SAME_STATE_PATH = CMS_DIR / "clean_control_candidates_v2_gold_plus_silver_same_state.csv"
SUMMARY_V2_GOLD_SILVER_SAME_STATE_PATH = CMS_DIR / "clean_control_candidates_v2_gold_plus_silver_same_state_summary.json"


def canonical_ccn(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if any(ch.isalpha() for ch in text):
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return None
    digits = digits.zfill(6)[-6:]
    if digits == "000000":
        return None
    return digits


def latest_nonmissing(series: pd.Series) -> object:
    nonmissing = series.dropna()
    if nonmissing.empty:
        return pd.NA
    return nonmissing.iloc[-1]


def sum_binary(series: pd.Series) -> int:
    return int(pd.to_numeric(series, errors="coerce").fillna(0).astype(int).sum())


def max_binary(series: pd.Series) -> int:
    return int(pd.to_numeric(series, errors="coerce").fillna(0).astype(int).max())


def collapse_facility_year(df: pd.DataFrame) -> pd.DataFrame:
    binary_cols = [
        "has_form671",
        "has_owner_snapshot",
        "has_chow_event",
        "has_pbj_nurse",
        "has_provider_info_latest",
        "has_health_deficiency",
        "has_enrollment_snapshot",
        "has_survey_summary",
        "post_treatment_year",
        "verified_treated",
        "has_chow_buyer_event",
        "has_chow_seller_event",
    ]
    binary_present = [c for c in binary_cols if c in df.columns]
    for col in binary_present:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    agg: dict[str, object] = {}
    for col in df.columns:
        if col in {"ccn_str", "year"}:
            continue
        if col in binary_present:
            agg[col] = "max"
        else:
            agg[col] = latest_nonmissing
    return (
        df.sort_values(["ccn_str", "year"])
        .groupby(["ccn_str", "year"], as_index=False, dropna=False)
        .agg(agg)
    )


def treated_states_for_samples(*samples: str) -> list[str]:
    df = pd.read_csv(TREATMENT_PATH, dtype="string").fillna("")
    subset = df.loc[df["analysis_sample"].isin(samples), "state"].astype("string").str.strip()
    return sorted([state for state in subset.dropna().unique().tolist() if state])


def main() -> None:
    df = pd.read_csv(FOUNDATION_PATH, dtype={"ccn_str": "string"}, low_memory=False)
    df["ccn_str"] = df["ccn_str"].map(canonical_ccn).astype("string")
    df = df[df["ccn_str"].notna()].copy()
    if df.duplicated(["ccn_str", "year"]).sum() != 0:
        df = collapse_facility_year(df)

    provider_collision_ccns: set[str] = set()
    if PROVIDER_INFO_PATH.exists():
        provider = pd.read_csv(PROVIDER_INFO_PATH, dtype={"ccn_str": "string"}, low_memory=False)
        provider["ccn_str"] = provider["ccn_str"].map(canonical_ccn).astype("string")
        provider = provider[provider["ccn_str"].notna()].copy()
        provider_collision_ccns = set(
            provider.loc[
                provider.duplicated(["ccn_str", "year"], keep=False), "ccn_str"
            ].dropna()
        )

    df["verified_treated"] = pd.to_numeric(
        df["verified_treated"], errors="coerce"
    ).fillna(0).astype(int)

    binary_cols = [
        "has_form671",
        "has_owner_snapshot",
        "has_chow_event",
        "has_pbj_nurse",
        "has_provider_info_latest",
        "has_health_deficiency",
        "has_enrollment_snapshot",
        "has_survey_summary",
        "post_treatment_year",
    ]
    for col in binary_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    facility = (
        df.sort_values(["ccn_str", "year"])
        .groupby("ccn_str", as_index=False)
        .agg(
            first_year=("year", "min"),
            last_year=("year", "max"),
            panel_years=("year", "nunique"),
            provider_name_latest=("Provider Name", latest_nonmissing),
            state_latest=("State", latest_nonmissing),
            ownership_type_latest=("Ownership Type", latest_nonmissing),
            chain_name_latest=("Chain Name", latest_nonmissing),
            chain_id_latest=("Chain ID", latest_nonmissing),
            ever_verified_treated=("verified_treated", "max"),
            treat_year=("treat_year", latest_nonmissing),
            deal_id=("deal_id", latest_nonmissing),
            verification_tier=("verification_tier", latest_nonmissing),
            any_chow_event=("has_chow_event", "max"),
            has_chow_buyer_event_ever=("has_chow_buyer_event", max_binary),
            has_chow_seller_event_ever=("has_chow_seller_event", max_binary),
            years_with_form671=("has_form671", sum_binary),
            years_with_pbj_nurse=("has_pbj_nurse", sum_binary),
            years_with_health_deficiency=("has_health_deficiency", sum_binary),
            years_with_survey_summary=("has_survey_summary", sum_binary),
            years_with_owner_snapshot=("has_owner_snapshot", sum_binary),
            years_with_enrollment_snapshot=("has_enrollment_snapshot", sum_binary),
            latest_form671_medicaid_share=("form671_medicaid_share_mean", latest_nonmissing),
            latest_form671_total_residents=("form671_total_residents_mean", latest_nonmissing),
            latest_pbj_mean_rn_hprd=("pbj_mean_rn_hprd", latest_nonmissing),
            latest_pbj_mean_nurse_hprd=("pbj_mean_nurse_hprd", latest_nonmissing),
            latest_deficiency_citations=("deficiency_citations", latest_nonmissing),
            latest_health_deficiency_total=(
                "survey_summary_total_health_deficiencies",
                latest_nonmissing,
            ),
        )
    )

    facility["control_v1_eligible"] = (
        (facility["ever_verified_treated"] == 0) & (facility["any_chow_event"] == 0)
    ).astype(int)
    if provider_collision_ccns:
        facility.loc[facility["ccn_str"].isin(provider_collision_ccns), "control_v1_eligible"] = 0

    # v2 adds simple data-quality filters so the control pool is more likely to
    # support later DID work without becoming a hand-matched sample.
    facility["has_identifiable_provider"] = (
        facility["provider_name_latest"].notna() & facility["state_latest"].notna()
    ).astype(int)
    facility["has_min_panel_years"] = facility["panel_years"].ge(3).astype(int)
    facility["has_min_form671"] = facility["years_with_form671"].ge(2).astype(int)
    facility["has_any_main_outcome_history"] = (
        facility["years_with_pbj_nurse"].ge(2)
        | facility["years_with_health_deficiency"].ge(2)
        | facility["years_with_survey_summary"].ge(2)
    ).astype(int)
    facility["control_v2_eligible"] = (
        facility["control_v1_eligible"].eq(1)
        & facility["has_identifiable_provider"].eq(1)
        & facility["has_min_panel_years"].eq(1)
        & facility["has_min_form671"].eq(1)
        & facility["has_any_main_outcome_history"].eq(1)
    ).astype(int)
    facility["control_v2_staffing_eligible"] = (
        facility["control_v2_eligible"].eq(1)
        & facility["years_with_pbj_nurse"].ge(2)
    ).astype(int)
    facility["control_v2_deficiency_eligible"] = (
        facility["control_v2_eligible"].eq(1)
        & (
            facility["years_with_health_deficiency"].ge(2)
            | facility["years_with_survey_summary"].ge(2)
        )
    ).astype(int)

    expanded_treated = pd.read_csv(
        PROJECT_ROOT / "research" / "pe_facility_verification.csv", dtype="string"
    ).fillna("")
    expanded_treated["ccn_str"] = expanded_treated["ccn"].map(canonical_ccn).astype("string")
    gold_silver_ccns = set(
        expanded_treated.loc[
            expanded_treated["analysis_sample"].isin(["gold_main", "silver_main"]), "ccn_str"
        ].dropna()
    )
    facility["control_v1_gold_plus_silver_eligible"] = (
        facility["control_v1_eligible"].eq(1) & (~facility["ccn_str"].isin(gold_silver_ccns))
    ).astype(int)
    facility["control_v2_gold_plus_silver_eligible"] = (
        facility["control_v1_gold_plus_silver_eligible"].eq(1)
        & facility["has_identifiable_provider"].eq(1)
        & facility["has_min_panel_years"].eq(1)
        & facility["has_min_form671"].eq(1)
        & facility["has_any_main_outcome_history"].eq(1)
    ).astype(int)
    facility["control_v2_gold_plus_silver_staffing_eligible"] = (
        facility["control_v2_gold_plus_silver_eligible"].eq(1)
        & facility["years_with_pbj_nurse"].ge(2)
    ).astype(int)
    facility["control_v2_gold_plus_silver_deficiency_eligible"] = (
        facility["control_v2_gold_plus_silver_eligible"].eq(1)
        & (
            facility["years_with_health_deficiency"].ge(2)
            | facility["years_with_survey_summary"].ge(2)
        )
    ).astype(int)

    control = facility.loc[facility["control_v1_eligible"] == 1].copy()
    control = control.sort_values(["state_latest", "provider_name_latest", "ccn_str"])
    control.to_csv(OUTPUT_PATH, index=False)

    control_v2 = facility.loc[facility["control_v2_eligible"] == 1].copy()
    control_v2 = control_v2.sort_values(["state_latest", "provider_name_latest", "ccn_str"])
    control_v2.to_csv(OUTPUT_V2_PATH, index=False)

    control_v2_gold_silver = facility.loc[
        facility["control_v2_gold_plus_silver_eligible"] == 1
    ].copy()
    control_v2_gold_silver = control_v2_gold_silver.sort_values(
        ["state_latest", "provider_name_latest", "ccn_str"]
    )
    control_v2_gold_silver.to_csv(OUTPUT_V2_GOLD_SILVER_PATH, index=False)

    gold_states = treated_states_for_samples("gold_main")
    gold_silver_states = treated_states_for_samples("gold_main", "silver_main")

    summary = {
        "source_file": str(FOUNDATION_PATH),
        "output_file": str(OUTPUT_PATH),
        "sample_window_start": int(df["year"].min()),
        "sample_window_end": int(df["year"].max()),
        "unique_facilities_in_foundation": int(df["ccn_str"].nunique()),
        "verified_treated_facilities_excluded": int(
            facility["ever_verified_treated"].eq(1).sum()
        ),
        "facilities_with_any_chow_excluded": int(facility["any_chow_event"].eq(1).sum()),
        "facilities_excluded_for_provider_ccn_collision": int(
            facility["ccn_str"].isin(provider_collision_ccns).sum()
        ),
        "clean_control_candidates_v1": int(control["ccn_str"].nunique()),
        "control_v1_has_form671": int(control["years_with_form671"].gt(0).sum()),
        "control_v1_has_pbj_nurse": int(control["years_with_pbj_nurse"].gt(0).sum()),
        "control_v1_has_health_deficiency": int(
            control["years_with_health_deficiency"].gt(0).sum()
        ),
        "control_v1_has_survey_summary": int(
            control["years_with_survey_summary"].gt(0).sum()
        ),
    }

    with SUMMARY_PATH.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    summary_v2 = {
        "source_file": str(FOUNDATION_PATH),
        "output_file": str(OUTPUT_V2_PATH),
        "based_on": str(OUTPUT_PATH),
        "sample_window_start": int(df["year"].min()),
        "sample_window_end": int(df["year"].max()),
        "unique_facilities_in_foundation": int(df["ccn_str"].nunique()),
        "clean_control_candidates_v1": int(control["ccn_str"].nunique()),
        "control_v2_excludes_missing_identity": int(
            control.loc[control["has_identifiable_provider"].eq(0), "ccn_str"].nunique()
        ),
        "control_v2_excludes_short_panels": int(
            control.loc[control["has_min_panel_years"].eq(0), "ccn_str"].nunique()
        ),
        "control_v2_excludes_low_form671_coverage": int(
            control.loc[control["has_min_form671"].eq(0), "ccn_str"].nunique()
        ),
        "control_v2_excludes_low_outcome_history": int(
            control.loc[control["has_any_main_outcome_history"].eq(0), "ccn_str"].nunique()
        ),
        "clean_control_candidates_v2": int(control_v2["ccn_str"].nunique()),
        "control_v2_staffing_eligible": int(
            control_v2["control_v2_staffing_eligible"].eq(1).sum()
        ),
        "control_v2_deficiency_eligible": int(
            control_v2["control_v2_deficiency_eligible"].eq(1).sum()
        ),
        "control_v2_has_form671": int(control_v2["years_with_form671"].gt(0).sum()),
        "control_v2_has_pbj_nurse": int(control_v2["years_with_pbj_nurse"].gt(0).sum()),
        "control_v2_has_health_deficiency": int(
            control_v2["years_with_health_deficiency"].gt(0).sum()
        ),
        "control_v2_has_survey_summary": int(
            control_v2["years_with_survey_summary"].gt(0).sum()
        ),
    }

    with SUMMARY_V2_PATH.open("w", encoding="utf-8") as f:
        json.dump(summary_v2, f, indent=2)

    summary_v2_gold_silver = {
        "source_file": str(FOUNDATION_PATH),
        "output_file": str(OUTPUT_V2_GOLD_SILVER_PATH),
        "based_on": str(OUTPUT_PATH),
        "sample_window_start": int(df["year"].min()),
        "sample_window_end": int(df["year"].max()),
        "unique_facilities_in_foundation": int(df["ccn_str"].nunique()),
        "gold_plus_silver_treated_facilities_excluded": int(len(gold_silver_ccns)),
        "clean_control_candidates_v2_gold_plus_silver": int(
            control_v2_gold_silver["ccn_str"].nunique()
        ),
        "control_v2_gold_plus_silver_staffing_eligible": int(
            control_v2_gold_silver["control_v2_gold_plus_silver_staffing_eligible"].sum()
        ),
        "control_v2_gold_plus_silver_deficiency_eligible": int(
            control_v2_gold_silver["control_v2_gold_plus_silver_deficiency_eligible"].sum()
        ),
    }
    with SUMMARY_V2_GOLD_SILVER_PATH.open("w", encoding="utf-8") as f:
        json.dump(summary_v2_gold_silver, f, indent=2)

    control_v2_same_state = control_v2.loc[
        control_v2["state_latest"].isin(gold_states)
    ].copy()
    control_v2_same_state = control_v2_same_state.sort_values(
        ["state_latest", "provider_name_latest", "ccn_str"]
    )
    control_v2_same_state.to_csv(OUTPUT_V2_SAME_STATE_PATH, index=False)

    same_state_counts = (
        control_v2_same_state["state_latest"]
        .value_counts()
        .sort_index()
        .to_dict()
    )
    summary_v2_same_state = {
        "source_file": str(FOUNDATION_PATH),
        "output_file": str(OUTPUT_V2_SAME_STATE_PATH),
        "based_on": str(OUTPUT_V2_PATH),
        "treated_states": gold_states,
        "clean_control_candidates_v2": int(control_v2["ccn_str"].nunique()),
        "clean_control_candidates_v2_same_state": int(
            control_v2_same_state["ccn_str"].nunique()
        ),
        "same_state_control_counts": {
            state: int(same_state_counts.get(state, 0)) for state in gold_states
        },
        "same_state_staffing_eligible": int(
            control_v2_same_state["control_v2_staffing_eligible"].eq(1).sum()
        ),
        "same_state_deficiency_eligible": int(
            control_v2_same_state["control_v2_deficiency_eligible"].eq(1).sum()
        ),
    }

    with SUMMARY_V2_SAME_STATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(summary_v2_same_state, f, indent=2)

    control_v2_gold_silver_same_state = control_v2_gold_silver.loc[
        control_v2_gold_silver["state_latest"].isin(gold_silver_states)
    ].copy()
    control_v2_gold_silver_same_state = control_v2_gold_silver_same_state.sort_values(
        ["state_latest", "provider_name_latest", "ccn_str"]
    )
    control_v2_gold_silver_same_state.to_csv(
        OUTPUT_V2_GOLD_SILVER_SAME_STATE_PATH, index=False
    )

    summary_v2_gold_silver_same_state = {
        "source_file": str(FOUNDATION_PATH),
        "output_file": str(OUTPUT_V2_GOLD_SILVER_SAME_STATE_PATH),
        "based_on": str(OUTPUT_V2_GOLD_SILVER_PATH),
        "treated_states": gold_silver_states,
        "clean_control_candidates_v2_gold_plus_silver": int(
            control_v2_gold_silver["ccn_str"].nunique()
        ),
        "clean_control_candidates_v2_gold_plus_silver_same_state": int(
            control_v2_gold_silver_same_state["ccn_str"].nunique()
        ),
        "same_state_control_counts": control_v2_gold_silver_same_state.groupby("state_latest")[
            "ccn_str"
        ]
        .nunique()
        .sort_index()
        .astype(int)
        .to_dict(),
    }
    with SUMMARY_V2_GOLD_SILVER_SAME_STATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(summary_v2_gold_silver_same_state, f, indent=2)

    print("V1 summary:")
    print(json.dumps(summary, indent=2))
    print("\nV2 summary:")
    print(json.dumps(summary_v2, indent=2))
    print("\nV2 same-state summary:")
    print(json.dumps(summary_v2_same_state, indent=2))


if __name__ == "__main__":
    main()
