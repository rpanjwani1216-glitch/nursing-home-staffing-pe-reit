#!/usr/bin/env python3
"""Build a matched control sample from the same-state baseline pool."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.api.types import is_object_dtype, is_string_dtype


from utils import get_intermediate_dir, get_output_dir

ROOT = Path(__file__).resolve().parents[1]
INTERMEDIATE_ROOT = get_intermediate_dir(ROOT)
ANALYSIS_DIR = INTERMEDIATE_ROOT / "analysis"
PANELS_DIR = ANALYSIS_DIR / "panels"
MATCHING_DIR = ANALYSIS_DIR / "matching"
BALANCE_DIR = ANALYSIS_DIR / "balance"

BASELINE_PATH = BALANCE_DIR / "table1_baseline_facility_level_gold_v2_same_state.csv"
PANEL_PATH = PANELS_DIR / "regression_analysis_panel_gold_v2_same_state.csv"

MATCH_PAIRS_CSV = MATCHING_DIR / "matched_control_pairs_gold_v2_same_state.csv"
MATCH_CONTROLS_CSV = MATCHING_DIR / "matched_control_candidates_gold_v2_same_state.csv"
MATCHED_PANEL_CSV = PANELS_DIR / "regression_analysis_panel_gold_v2_same_state_matched.csv"
MATCHED_PANEL_DTA = PANELS_DIR / "regression_analysis_panel_gold_v2_same_state_matched.dta"
SUMMARY_JSON = MATCHING_DIR / "matched_control_sample_gold_v2_same_state_summary.json"

MATCH_RATIO = 3
MATCH_VARS = [
    "provider_certified_beds",
    "provider_avg_residents_per_day",
    "pbj_mean_rn_hprd",
    "pbj_mean_nurse_hprd",
    "provider_health_rating",
    "provider_overall_rating",
    "provider_staffing_rating",
    "chain_affiliated",
    "for_profit",
]


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


def main() -> None:
    MATCHING_DIR.mkdir(parents=True, exist_ok=True)
    PANELS_DIR.mkdir(parents=True, exist_ok=True)
    baseline = pd.read_csv(BASELINE_PATH)
    panel = pd.read_csv(PANEL_PATH, low_memory=False)

    states = panel[["ccn_str", "analysis_state", "sample_role"]].drop_duplicates()
    baseline = baseline.merge(states, on="ccn_str", how="left")

    treated = baseline[baseline["sample_role"].eq("treated")].copy()
    controls = baseline[baseline["sample_role"].eq("control")].copy()

    pairs: list[dict[str, object]] = []

    for state, treated_state in treated.groupby("analysis_state", dropna=False):
        controls_state = controls[controls["analysis_state"].eq(state)].copy()
        if controls_state.empty:
            raise ValueError(f"No same-state controls available for state {state}")

        means = controls_state[MATCH_VARS].mean()
        stds = controls_state[MATCH_VARS].std(ddof=0).replace(0, 1.0).fillna(1.0)

        controls_state = controls_state.copy()
        treated_state = treated_state.copy()
        controls_state.loc[:, MATCH_VARS] = (controls_state[MATCH_VARS] - means) / stds
        treated_state.loc[:, MATCH_VARS] = (treated_state[MATCH_VARS] - means) / stds

        available_controls = controls_state.set_index("ccn_str")

        # Greedy nearest-neighbor matching without replacement within state.
        for _, tr in treated_state.sort_values("ccn_str").iterrows():
            if len(available_controls) < MATCH_RATIO:
                raise ValueError(f"Insufficient controls left in state {state} for ratio {MATCH_RATIO}")

            tr_vec = tr[MATCH_VARS].astype(float).to_numpy()
            distances = []
            for ccn, ctrl in available_controls.iterrows():
                ctrl_vec = ctrl[MATCH_VARS].astype(float).to_numpy()
                dist = float(np.sqrt(np.sum((tr_vec - ctrl_vec) ** 2)))
                distances.append((ccn, dist))
            distances.sort(key=lambda x: (x[1], x[0]))
            chosen = distances[:MATCH_RATIO]

            for rank, (control_ccn, distance) in enumerate(chosen, start=1):
                pairs.append(
                    {
                        "treated_ccn": tr["ccn_str"],
                        "control_ccn": control_ccn,
                        "analysis_state": state,
                        "match_rank": rank,
                        "distance": distance,
                    }
                )
            available_controls = available_controls.drop([ccn for ccn, _ in chosen])

    pairs_df = pd.DataFrame(pairs).sort_values(
        ["analysis_state", "treated_ccn", "match_rank", "control_ccn"]
    )
    pairs_df.to_csv(MATCH_PAIRS_CSV, index=False)

    matched_controls = (
        pairs_df[["control_ccn"]]
        .drop_duplicates()
        .rename(columns={"control_ccn": "ccn_str"})
        .assign(matched_control=1)
    )
    matched_controls.to_csv(MATCH_CONTROLS_CSV, index=False)

    matched_ccns = set(pairs_df["control_ccn"]).union(set(pairs_df["treated_ccn"]))
    matched_panel = panel[panel["ccn_str"].isin(matched_ccns)].copy()
    matched_panel["matched_sample"] = 1
    matched_panel["analysis_spec"] = "gold_main_v2_same_state_matched"
    matched_panel["analysis_sample_label"] = matched_panel["sample_role"].map(
        {"treated": "gold_main", "control": "control_same_state_matched"}
    )
    export_csv_and_dta(matched_panel, MATCHED_PANEL_CSV, MATCHED_PANEL_DTA)

    summary = {
        "analysis_spec": "gold_main_v2_same_state_matched",
        "match_ratio": MATCH_RATIO,
        "match_vars": MATCH_VARS,
        "treated_facilities": int(pairs_df["treated_ccn"].nunique()),
        "matched_control_facilities": int(pairs_df["control_ccn"].nunique()),
        "pair_rows": int(len(pairs_df)),
        "mean_distance": float(pairs_df["distance"].mean()),
        "max_distance": float(pairs_df["distance"].max()),
        "matched_panel_rows": int(len(matched_panel)),
        "matched_panel_unique_facilities": int(matched_panel["ccn_str"].nunique()),
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
