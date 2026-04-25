#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from pandas.api.types import is_object_dtype, is_string_dtype


ROOT = Path(__file__).resolve().parents[2]
RESEARCH_DIR = ROOT / "research"
TREATMENT_INPUTS_DIR = RESEARCH_DIR / "treatment_inputs"
DEAL_WORKFILES_DIR   = RESEARCH_DIR / "deal_workfiles"
INTERMEDIATE_ANALYSIS_DIR = ROOT / "data" / "intermediate" / "analysis"
PANELS_DIR = INTERMEDIATE_ANALYSIS_DIR / "panels"
CMS_DIR = ROOT / "data" / "intermediate" / "cms"
LTCFOCUS_DIR = ROOT / "data" / "intermediate" / "ltcfocus"

TRILOGY_PANEL = DEAL_WORKFILES_DIR / "trilogy_2015_event_window" / "trilogy_2015_event_window_panel.csv"
OMEGA_ROSTER = DEAL_WORKFILES_DIR / "omega_consulate_2019_event_window" / "omega_consulate_2019_verified_roster.csv"
FC_ENCORE_PANEL = DEAL_WORKFILES_DIR / "fc_encore_2019_event_window" / "fc_encore_2019_event_window_panel.csv"
GENESIS_SUMMARY = DEAL_WORKFILES_DIR / "welltower_aurora_reverse_engineered" / "welltower_aurora_reverse_engineered_summary.csv"
PE_TREATMENT = TREATMENT_INPUTS_DIR / "pe_facility_verification.csv"

LTCFOCUS_FULL = LTCFOCUS_DIR / "ltcfocus_facility_year_full.csv"
CMS_FOUNDATION = CMS_DIR / "cms_facility_year_foundation.csv"

REIT_TREATMENT_CSV = TREATMENT_INPUTS_DIR / "reit_facility_verification.csv"
CONTROL_POOL_CSV = CMS_DIR / "reit_extended_control_pool.csv"
PANEL_CSV = PANELS_DIR / "reit_staffing_panel_extended.csv"
PANEL_DTA = PANELS_DIR / "reit_staffing_panel_extended.dta"
PANEL_STATE_CSV = PANELS_DIR / "reit_staffing_panel_extended_same_state.csv"
PANEL_STATE_DTA = PANELS_DIR / "reit_staffing_panel_extended_same_state.dta"
SUMMARY_JSON = PANELS_DIR / "reit_staffing_panel_extended_summary.json"
README_PATH = INTERMEDIATE_ANALYSIS_DIR / "README_reit_extended.md"


def canonical_ccn(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return None
    core = digits.zfill(6)
    if len(core) > 6:
        return core[-6:]
    return core


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


def load_reit_treatment() -> pd.DataFrame:
    trilogy = pd.read_csv(TRILOGY_PANEL, dtype=str)
    trilogy = trilogy[["ccn_str", "facility_name_reit_file", "state"]].drop_duplicates()
    trilogy["deal_id"] = "REIT001"
    trilogy["reit_name"] = "American Healthcare REIT"
    trilogy["platform_name"] = "Trilogy"
    trilogy["ownership_effective_date"] = "2015"
    trilogy["treat_year"] = 2015
    trilogy["source_group"] = "trilogy_2015_verified"
    trilogy["verification_tier"] = "verified"
    trilogy = trilogy.rename(columns={"facility_name_reit_file": "facility_name", "ccn_str": "ccn"})

    omega = pd.read_csv(OMEGA_ROSTER, dtype=str)
    omega = omega[omega["ccn_str"].notna()].copy()
    omega["facility_name"] = omega["provider_name_latest"].fillna(omega["facility_name_source"])
    omega = omega[["ccn_str", "facility_name", "state"]].drop_duplicates()
    omega["deal_id"] = "REIT002"
    omega["reit_name"] = "Omega Healthcare Investors"
    omega["platform_name"] = "Consulate / LaVie subset"
    omega["ownership_effective_date"] = "2019"
    omega["treat_year"] = 2019
    omega["source_group"] = "omega_consulate_2019_verified_subset"
    omega["verification_tier"] = "verified"
    omega = omega.rename(columns={"ccn_str": "ccn"})

    fc_encore = pd.read_csv(FC_ENCORE_PANEL, dtype=str)
    fc_encore = fc_encore[["ccn_str", "facility_name_reit_file", "state"]].drop_duplicates()
    fc_encore["deal_id"] = "REIT002"
    fc_encore["reit_name"] = "Omega Healthcare Investors"
    fc_encore["platform_name"] = "FC Encore / Consulate"
    fc_encore["ownership_effective_date"] = "2019"
    fc_encore["treat_year"] = 2019
    fc_encore["source_group"] = "fc_encore_2019_direct"
    fc_encore["verification_tier"] = "verified"
    fc_encore = fc_encore.rename(columns={"facility_name_reit_file": "facility_name", "ccn_str": "ccn"})

    genesis = pd.read_csv(GENESIS_SUMMARY, dtype=str)
    genesis = genesis[["ccn", "provider_name_2026", "state"]].drop_duplicates()
    genesis["deal_id"] = "REIT003"
    genesis["reit_name"] = "Welltower"
    genesis["platform_name"] = "Aurora / Complete Care former Genesis subset"
    genesis["ownership_effective_date"] = "2021"
    genesis["treat_year"] = 2021
    genesis["source_group"] = "welltower_aurora_2021_reverse_engineered"
    genesis["verification_tier"] = "reverse_engineered"
    genesis = genesis.rename(columns={"provider_name_2026": "facility_name"})

    treatment = pd.concat([trilogy, omega, fc_encore, genesis], ignore_index=True)
    treatment["ccn"] = treatment["ccn"].map(canonical_ccn)
    treatment = treatment[treatment["ccn"].notna()].copy()
    treatment["analysis_sample"] = "reit_main"
    treatment["sample_role"] = "treated"
    treatment["transition_type"] = "non_reit_to_reit_or_reit_jv"
    treatment = treatment.sort_values(["deal_id", "ccn", "source_group"])
    treatment = treatment.drop_duplicates(subset=["ccn"], keep="first").reset_index(drop=True)
    return treatment


def load_ltcfocus() -> pd.DataFrame:
    df = pd.read_csv(LTCFOCUS_FULL, low_memory=False)
    df["ccn_str"] = df["ccn_str"].map(canonical_ccn)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

    # LTCFocus staffing shifts from legacy hrppd fields to PBJ-based hprd fields
    # in later years. Coalesce them so post-2018 staffing remains available.
    staffing_fallbacks = {
        "dchrppd": "dchprd_pbj",
        "rnhrppd": "rnhprd_pbj",
        "lpnhrppd": "lpnhprd_pbj",
        "cnahrppd": "cnahprd_pbj",
    }
    for legacy_col, pbj_col in staffing_fallbacks.items():
        if legacy_col not in df.columns:
            df[legacy_col] = pd.NA
        if pbj_col not in df.columns:
            df[pbj_col] = pd.NA
        df[legacy_col] = pd.to_numeric(df[legacy_col], errors="coerce")
        df[pbj_col] = pd.to_numeric(df[pbj_col], errors="coerce")
        df[legacy_col] = df[legacy_col].combine_first(df[pbj_col])

    keep = [
        "ccn_str",
        "year",
        "facility_name_ltcfocus",
        "state",
        "county",
        "totbeds",
        "occpct",
        "nhcpain",
        "paymcaid",
        "paymcare",
        "dchrppd",
        "rnhrppd",
        "lpnhrppd",
        "cnahrppd",
    ]
    out = df[keep].copy()
    out = out.rename(
        columns={
            "state": "ltcfocus_state",
            "county": "ltcfocus_county",
            "totbeds": "ltcfocus_total_beds",
            "occpct": "ltcfocus_occupancy_pct",
            "nhcpain": "ltcfocus_residents",
            "paymcaid": "ltcfocus_medicaid_share",
            "paymcare": "ltcfocus_medicare_share",
            "dchrppd": "ltcfocus_directcare_hprd",
            "rnhrppd": "ltcfocus_rn_hprd",
            "lpnhrppd": "ltcfocus_lpn_hprd",
            "cnahrppd": "ltcfocus_cna_hprd",
        }
    )
    return out[out["ccn_str"].notna() & out["year"].notna()].copy()


def build_control_pool(ltcfocus: pd.DataFrame, treatment: pd.DataFrame) -> pd.DataFrame:
    pe = pd.read_csv(PE_TREATMENT, dtype=str)
    pe["ccn_str"] = pe["ccn"].map(canonical_ccn)
    pe_treated = set(pe["ccn_str"].dropna())

    foundation = pd.read_csv(CMS_FOUNDATION, low_memory=False, dtype={"ccn_str": str})
    foundation["ccn_str"] = foundation["ccn_str"].map(canonical_ccn)
    foundation["year"] = pd.to_numeric(foundation["year"], errors="coerce")
    for col in ["has_chow_event", "any_reit_owner", "verified_treated"]:
        if col in foundation.columns:
            foundation[col] = pd.to_numeric(foundation[col], errors="coerce").fillna(0).astype(int)

    facility_flags = (
        foundation[foundation["ccn_str"].notna()]
        .sort_values(["ccn_str", "year"])
        .groupby("ccn_str", as_index=False)
        .agg(
            state_latest=("State", "last"),
            provider_name_latest=("Provider Name", "last"),
            any_chow_event_ever=("has_chow_event", "max"),
            any_reit_owner_ever=("any_reit_owner", "max"),
            any_verified_pe_treated_ever=("verified_treated", "max"),
        )
    )

    ltc_facility = (
        ltcfocus.sort_values(["ccn_str", "year"])
        .groupby("ccn_str", as_index=False)
        .agg(
            facility_name_latest=("facility_name_ltcfocus", "last"),
            state_latest_ltcfocus=("ltcfocus_state", "last"),
            first_year=("year", "min"),
            last_year=("year", "max"),
            panel_years=("year", "nunique"),
            years_with_rn=("ltcfocus_rn_hprd", lambda s: int(s.notna().sum())),
            years_with_directcare=("ltcfocus_directcare_hprd", lambda s: int(s.notna().sum())),
            years_with_any_staffing=(
                "ltcfocus_directcare_hprd",
                lambda s: int(s.notna().sum()),
            ),
        )
    )

    pool = ltc_facility.merge(facility_flags, on="ccn_str", how="left")
    pool["state_latest"] = pool["state_latest"].fillna(pool["state_latest_ltcfocus"])
    pool["provider_name_latest"] = pool["provider_name_latest"].fillna(pool["facility_name_latest"])
    pool["any_chow_event_ever"] = pd.to_numeric(pool["any_chow_event_ever"], errors="coerce").fillna(0).astype(int)
    pool["any_reit_owner_ever"] = pd.to_numeric(pool["any_reit_owner_ever"], errors="coerce").fillna(0).astype(int)
    pool["any_verified_pe_treated_ever"] = (
        pd.to_numeric(pool["any_verified_pe_treated_ever"], errors="coerce").fillna(0).astype(int)
    )
    pool["in_reit_treatment"] = pool["ccn_str"].isin(set(treatment["ccn"])).astype(int)
    pool["in_pe_treatment_file"] = pool["ccn_str"].isin(pe_treated).astype(int)
    pool["control_reit_extended_eligible"] = (
        (pool["in_reit_treatment"] == 0)
        & (pool["in_pe_treatment_file"] == 0)
        & (pool["any_verified_pe_treated_ever"] == 0)
        & (pool["any_reit_owner_ever"] == 0)
        & (pool["any_chow_event_ever"] == 0)
        & (pool["panel_years"] >= 5)
        & (pool["years_with_rn"] >= 5)
        & (pool["years_with_directcare"] >= 5)
    ).astype(int)
    pool = pool.sort_values(["state_latest", "provider_name_latest", "ccn_str"]).reset_index(drop=True)
    return pool


def build_baseline_inputs(ltcfocus: pd.DataFrame, treatment: pd.DataFrame, controls: pd.DataFrame) -> pd.DataFrame:
    treated_units = treatment[["ccn", "facility_name", "state", "treat_year"]].drop_duplicates().rename(
        columns={"ccn": "ccn_str"}
    )
    treated_merged = ltcfocus.merge(treated_units, on="ccn_str", how="inner", suffixes=("", "_treat"))
    treated_pre = treated_merged[treated_merged["year"] < treated_merged["treat_year"]].copy()

    treated_base = (
        treated_pre.groupby(["ccn_str", "facility_name", "state", "treat_year"], as_index=False)
        .agg(
            baseline_medicaid_share=("ltcfocus_medicaid_share", "mean"),
            baseline_medicaid_n_years=("ltcfocus_medicaid_share", "count"),
            baseline_window_start=("year", "min"),
            baseline_window_end=("year", "max"),
        )
    )
    treated_base = treated_base[treated_base["baseline_medicaid_n_years"] >= 2].copy()
    treated_base["sample_role"] = "treated"
    treated_base["baseline_method"] = "treated_all_preyears"
    treated_base["valid_pseudocohorts"] = pd.NA

    treated_year_weights = (
        treatment.groupby("treat_year", as_index=False)
        .size()
        .rename(columns={"size": "treated_count"})
    )
    treated_year_weights["cohort_weight"] = (
        treated_year_weights["treated_count"] / treated_year_weights["treated_count"].sum()
    )

    eligible_controls = controls[controls["control_reit_extended_eligible"].eq(1)].copy()
    control_units = eligible_controls[["ccn_str", "provider_name_latest", "state_latest"]].drop_duplicates()
    control_units["key"] = 1
    cohort_weights = treated_year_weights.rename(columns={"treat_year": "cohort_year"}).copy()
    cohort_weights["key"] = 1

    control_base = ltcfocus[["ccn_str", "year", "ltcfocus_medicaid_share"]].merge(control_units, on="ccn_str", how="inner")
    control_base = control_base.merge(cohort_weights, on="key", how="inner")
    control_base = control_base[control_base["year"] < control_base["cohort_year"]].copy()

    control_by_cohort = (
        control_base.groupby(
            ["ccn_str", "provider_name_latest", "state_latest", "cohort_year", "cohort_weight"],
            as_index=False,
        )
        .agg(
            cohort_baseline_share=("ltcfocus_medicaid_share", "mean"),
            cohort_n_years=("ltcfocus_medicaid_share", "count"),
            cohort_window_start=("year", "min"),
            cohort_window_end=("year", "max"),
        )
    )
    control_by_cohort = control_by_cohort[control_by_cohort["cohort_n_years"] >= 2].copy()
    valid_weight_total = control_by_cohort.groupby("ccn_str")["cohort_weight"].transform("sum")
    control_by_cohort["normalized_weight"] = control_by_cohort["cohort_weight"] / valid_weight_total
    control_by_cohort["weighted_baseline_share"] = (
        control_by_cohort["normalized_weight"] * control_by_cohort["cohort_baseline_share"]
    )

    control_out = (
        control_by_cohort.groupby(["ccn_str", "provider_name_latest", "state_latest"], as_index=False)
        .agg(
            baseline_medicaid_share=("weighted_baseline_share", "sum"),
            baseline_medicaid_n_years=("cohort_n_years", "min"),
            baseline_window_start=("cohort_window_start", "min"),
            baseline_window_end=("cohort_window_end", "max"),
            valid_pseudocohorts=("cohort_year", "nunique"),
        )
    )
    control_out = control_out.rename(
        columns={
            "provider_name_latest": "facility_name",
            "state_latest": "state",
        }
    )
    control_out["treat_year"] = pd.NA
    control_out["sample_role"] = "control"
    control_out["baseline_method"] = "control_weighted_pseudocohort_reit"

    baseline = pd.concat(
        [
            treated_base[
                [
                    "ccn_str",
                    "facility_name",
                    "state",
                    "treat_year",
                    "baseline_medicaid_share",
                    "baseline_medicaid_n_years",
                    "baseline_window_start",
                    "baseline_window_end",
                    "sample_role",
                    "baseline_method",
                    "valid_pseudocohorts",
                ]
            ],
            control_out[
                [
                    "ccn_str",
                    "facility_name",
                    "state",
                    "treat_year",
                    "baseline_medicaid_share",
                    "baseline_medicaid_n_years",
                    "baseline_window_start",
                    "baseline_window_end",
                    "sample_role",
                    "baseline_method",
                    "valid_pseudocohorts",
                ]
            ],
        ],
        ignore_index=True,
    )
    return baseline


def build_panel(
    ltcfocus: pd.DataFrame,
    treatment: pd.DataFrame,
    controls: pd.DataFrame,
    baseline_inputs: pd.DataFrame,
    same_state_only: bool,
) -> pd.DataFrame:
    treated_states = sorted(treatment["state"].dropna().unique().tolist())
    control_subset = controls[controls["control_reit_extended_eligible"].eq(1)].copy()
    if same_state_only:
        control_subset = control_subset[control_subset["state_latest"].isin(treated_states)].copy()

    treated_units = treatment[["ccn", "facility_name", "state", "deal_id", "reit_name", "platform_name", "ownership_effective_date", "treat_year", "source_group", "verification_tier"]].drop_duplicates().copy()
    treated_units["sample_role"] = "treated"
    treated_units = treated_units.rename(columns={"ccn": "ccn_str", "facility_name": "facility_name_treatment", "state": "analysis_state"})

    control_units = control_subset[["ccn_str", "provider_name_latest", "state_latest"]].drop_duplicates().copy()
    control_units["facility_name_treatment"] = control_units["provider_name_latest"]
    control_units["analysis_state"] = control_units["state_latest"]
    control_units["deal_id"] = pd.NA
    control_units["reit_name"] = pd.NA
    control_units["platform_name"] = pd.NA
    control_units["ownership_effective_date"] = pd.NA
    control_units["treat_year"] = pd.NA
    control_units["source_group"] = pd.NA
    control_units["verification_tier"] = pd.NA
    control_units["sample_role"] = "control"
    control_units = control_units.drop(columns=["provider_name_latest", "state_latest"])

    universe = pd.concat([treated_units, control_units], ignore_index=True)
    panel = ltcfocus[ltcfocus["ccn_str"].isin(universe["ccn_str"])].copy()
    panel = panel.merge(universe, on="ccn_str", how="inner")
    panel = panel.merge(
        baseline_inputs[
            [
                "ccn_str",
                "baseline_medicaid_share",
                "baseline_medicaid_n_years",
                "baseline_window_start",
                "baseline_window_end",
                "baseline_method",
                "valid_pseudocohorts",
            ]
        ],
        on="ccn_str",
        how="left",
    )
    panel["analysis_spec"] = "reit_extended_same_state" if same_state_only else "reit_extended_national"
    panel["ever_treated"] = panel["sample_role"].eq("treated").astype(int)
    panel["post_treat"] = 0
    mask = panel["ever_treated"].eq(1) & panel["treat_year"].notna()
    panel.loc[mask, "post_treat"] = (
        pd.to_numeric(panel.loc[mask, "year"], errors="coerce")
        >= pd.to_numeric(panel.loc[mask, "treat_year"], errors="coerce")
    ).astype(int)
    panel.loc[~mask, "post_treat"] = 0
    panel["event_time"] = pd.NA
    panel.loc[mask, "event_time"] = (
        pd.to_numeric(panel.loc[mask, "year"], errors="coerce")
        - pd.to_numeric(panel.loc[mask, "treat_year"], errors="coerce")
    ).astype("Int64")
    panel["did_treat"] = (panel["ever_treated"].eq(1) & panel["post_treat"].eq(1)).astype(int)
    panel["sample_main_staffing"] = panel[["ltcfocus_rn_hprd", "ltcfocus_directcare_hprd"]].notna().all(axis=1).astype(int)
    panel = panel.sort_values(["ccn_str", "year"]).reset_index(drop=True)

    cols = [
        "analysis_spec",
        "sample_role",
        "ccn_str",
        "facility_name_treatment",
        "analysis_state",
        "year",
        "ever_treated",
        "treat_year",
        "post_treat",
        "event_time",
        "did_treat",
        "deal_id",
        "reit_name",
        "platform_name",
        "ownership_effective_date",
        "source_group",
        "verification_tier",
        "ltcfocus_state",
        "ltcfocus_county",
        "facility_name_ltcfocus",
        "ltcfocus_total_beds",
        "ltcfocus_occupancy_pct",
        "ltcfocus_residents",
        "baseline_medicaid_share",
        "baseline_medicaid_n_years",
        "baseline_window_start",
        "baseline_window_end",
        "baseline_method",
        "valid_pseudocohorts",
        "ltcfocus_medicaid_share",
        "ltcfocus_medicare_share",
        "ltcfocus_directcare_hprd",
        "ltcfocus_rn_hprd",
        "ltcfocus_lpn_hprd",
        "ltcfocus_cna_hprd",
        "sample_main_staffing",
    ]
    return panel[cols]


def main() -> None:
    PANELS_DIR.mkdir(parents=True, exist_ok=True)

    treatment = load_reit_treatment()
    treatment.to_csv(REIT_TREATMENT_CSV, index=False)

    ltcfocus = load_ltcfocus()
    controls = build_control_pool(ltcfocus, treatment)
    controls.to_csv(CONTROL_POOL_CSV, index=False)
    baseline_inputs = build_baseline_inputs(ltcfocus, treatment, controls)

    panel_nat = build_panel(ltcfocus, treatment, controls, baseline_inputs, same_state_only=False)
    panel_state = build_panel(ltcfocus, treatment, controls, baseline_inputs, same_state_only=True)

    export_csv_and_dta(panel_nat, PANEL_CSV, PANEL_DTA)
    export_csv_and_dta(panel_state, PANEL_STATE_CSV, PANEL_STATE_DTA)

    summary = {
        "treatment_facilities": int(treatment["ccn"].nunique()),
        "treatment_by_deal": treatment.groupby("deal_id")["ccn"].nunique().to_dict(),
        "eligible_controls": int(controls["control_reit_extended_eligible"].sum()),
        "national_panel_rows": int(len(panel_nat)),
        "national_panel_facilities": int(panel_nat["ccn_str"].nunique()),
        "same_state_panel_rows": int(len(panel_state)),
        "same_state_panel_facilities": int(panel_state["ccn_str"].nunique()),
        "sample_main_staffing_rows_national": int(panel_nat["sample_main_staffing"].sum()),
        "sample_main_staffing_rows_same_state": int(panel_state["sample_main_staffing"].sum()),
        "treated_facilities_with_baseline_medicaid": int(
            panel_nat.loc[
                panel_nat["sample_role"].eq("treated") & panel_nat["baseline_medicaid_share"].notna(),
                "ccn_str",
            ].nunique()
        ),
        "control_facilities_with_baseline_medicaid": int(
            panel_nat.loc[
                panel_nat["sample_role"].eq("control") & panel_nat["baseline_medicaid_share"].notna(),
                "ccn_str",
            ].nunique()
        ),
        "states_treated": sorted(treatment["state"].dropna().unique().tolist()),
        "years": [int(panel_nat["year"].min()), int(panel_nat["year"].max())],
        "note": "REIT003 is the 2021 Welltower/Aurora reverse-engineered former Genesis subset, not the full 2011 Genesis/Welltower acquisition roster.",
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    README_PATH.write_text(
        """# Extended REIT Staffing Panels

This folder contains a separate REIT-focused staffing panel that extends the analysis window back to 2009 using LTCFocus staffing variables.

Files:
- `panels/reit_staffing_panel_extended.csv`
- `panels/reit_staffing_panel_extended.dta`
- `panels/reit_staffing_panel_extended_same_state.csv`
- `panels/reit_staffing_panel_extended_same_state.dta`
- `panels/reit_staffing_panel_extended_summary.json`

Treatment cohorts:
- `REIT001`: American Healthcare REIT / Trilogy (2015)
- `REIT002`: Omega / Consulate / FC Encore subset (2019)
- `REIT003`: Welltower / Aurora reverse-engineered former Genesis subset (2021)

Outcome focus:
- LTCFocus direct-care HPRD
- LTCFocus RN HPRD
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
