#!/usr/bin/env python3
"""Evaluate alternative same-state 3:1 matched-control designs."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = ROOT / "data" / "intermediate" / "analysis"
BALANCE_DIR = ANALYSIS_DIR / "balance"
PANELS_DIR = ANALYSIS_DIR / "panels"
OUTPUT_DIR = ROOT / "outputs" / "qa" / "matching" / "variants"

BASELINE_PATH = BALANCE_DIR / "table1_baseline_facility_level_gold_v2_same_state.csv"
PANEL_PATH = PANELS_DIR / "regression_analysis_panel_gold_v2_same_state.csv"
BENCHMARK_PATH = ROOT / "outputs" / "tables" / "balance" / "table1_baseline_balance_gold_v2_same_state_matched.csv"

MATCH_RATIO = 3
BALANCE_VARS = [
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

VARIANT_SPECS: dict[str, dict[str, object]] = {
    "ops_only": {
        "match_vars": [
            "provider_certified_beds",
            "provider_avg_residents_per_day",
            "pbj_mean_rn_hprd",
            "pbj_mean_nurse_hprd",
        ],
        "order_rule": "ccn",
        "method": "nearest_neighbor",
    },
    "ratings_ownership": {
        "match_vars": [
            "provider_health_rating",
            "provider_overall_rating",
            "provider_staffing_rating",
            "chain_affiliated",
            "for_profit",
        ],
        "order_rule": "ccn",
        "method": "nearest_neighbor",
    },
    "size_ratings": {
        "match_vars": [
            "provider_certified_beds",
            "provider_avg_residents_per_day",
            "provider_health_rating",
            "provider_overall_rating",
            "provider_staffing_rating",
        ],
        "order_rule": "ccn",
        "method": "nearest_neighbor",
    },
    "hybrid_ops_ownership": {
        "match_vars": [
            "provider_certified_beds",
            "provider_avg_residents_per_day",
            "pbj_mean_rn_hprd",
            "provider_health_rating",
            "provider_overall_rating",
            "chain_affiliated",
            "for_profit",
        ],
        "order_rule": "ccn",
        "method": "nearest_neighbor",
    },
    "full_linear_score": {
        "match_vars": [
            "provider_certified_beds",
            "provider_avg_residents_per_day",
            "pbj_mean_rn_hprd",
            "pbj_mean_nurse_hprd",
            "provider_health_rating",
            "provider_overall_rating",
            "provider_staffing_rating",
            "chain_affiliated",
            "for_profit",
        ],
        "order_rule": "ccn",
        "method": "linear_score",
    },
    "full_hardest_first": {
        "match_vars": [
            "provider_certified_beds",
            "provider_avg_residents_per_day",
            "pbj_mean_rn_hprd",
            "pbj_mean_nurse_hprd",
            "provider_health_rating",
            "provider_overall_rating",
            "provider_staffing_rating",
            "chain_affiliated",
            "for_profit",
        ],
        "order_rule": "hardest_first",
        "method": "nearest_neighbor",
    },
    "full_linear_exact_fp": {
        "match_vars": [
            "provider_certified_beds",
            "provider_avg_residents_per_day",
            "pbj_mean_rn_hprd",
            "pbj_mean_nurse_hprd",
            "provider_health_rating",
            "provider_overall_rating",
            "provider_staffing_rating",
            "chain_affiliated",
            "for_profit",
        ],
        "order_rule": "ccn",
        "method": "linear_score",
        "exact_cols": ["for_profit_bin"],
    },
}


def pooled_std(treated: pd.Series, control: pd.Series) -> float:
    t = treated.dropna().astype(float)
    c = control.dropna().astype(float)
    if len(t) == 0 or len(c) == 0:
        return float("nan")
    t_var = float(t.var(ddof=0))
    c_var = float(c.var(ddof=0))
    return math.sqrt((t_var + c_var) / 2.0)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    baseline = pd.read_csv(BASELINE_PATH)
    panel = pd.read_csv(PANEL_PATH, low_memory=False)
    benchmark = pd.read_csv(BENCHMARK_PATH)
    states = panel[["ccn_str", "analysis_state", "sample_role"]].drop_duplicates()
    baseline = baseline.merge(states, on="ccn_str", how="left")
    baseline["for_profit_bin"] = (baseline["for_profit"] >= 0.5).astype(int)
    baseline["chain_any_bin"] = (baseline["chain_affiliated"] > 0).astype(int)
    return baseline, panel, benchmark


def standardize_by_state(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for state, idx in out.groupby("analysis_state").groups.items():
        state_df = out.loc[idx, cols]
        means = state_df.mean()
        stds = state_df.std(ddof=0).replace(0, 1.0).fillna(1.0)
        out.loc[idx, cols] = (state_df - means) / stds
    return out


def linear_score_features(df: pd.DataFrame, cols: list[str]) -> np.ndarray:
    x = df[cols].astype(float).to_numpy()
    y = df["treated_ever"].astype(float).to_numpy()
    x_aug = np.column_stack([np.ones(len(df)), x])
    coef, *_ = np.linalg.lstsq(x_aug, y, rcond=None)
    return x_aug @ coef


def build_pairs(baseline: pd.DataFrame, spec: dict[str, object]) -> pd.DataFrame:
    treated = baseline[baseline["sample_role"].eq("treated")].copy()
    controls = baseline[baseline["sample_role"].eq("control")].copy()
    match_vars = list(spec["match_vars"])
    method = str(spec["method"])
    order_rule = str(spec["order_rule"])
    exact_cols = list(spec.get("exact_cols", []))

    pairs: list[dict[str, object]] = []

    for state, treated_state in treated.groupby("analysis_state", dropna=False):
        controls_state = controls[controls["analysis_state"].eq(state)].copy()
        if controls_state.empty:
            raise ValueError(f"No controls available for state {state}")

        state_all = pd.concat([treated_state, controls_state], ignore_index=True)
        state_all = standardize_by_state(state_all, match_vars)
        treated_z = state_all[state_all["sample_role"].eq("treated")].copy()
        controls_z = state_all[state_all["sample_role"].eq("control")].copy()
        available_controls = controls_z.set_index("ccn_str")

        if method == "linear_score":
            state_scored = state_all.copy()
            state_scored["match_score"] = linear_score_features(state_scored, match_vars)
            treated_z = state_scored[state_scored["sample_role"].eq("treated")].copy()
            controls_z = state_scored[state_scored["sample_role"].eq("control")].copy()
            available_controls = controls_z.set_index("ccn_str")

        if order_rule == "hardest_first":
            hardness = []
            for _, tr in treated_z.iterrows():
                tr_vec = tr[match_vars].astype(float).to_numpy()
                dists = []
                for _, ctrl in controls_z.iterrows():
                    ctrl_vec = ctrl[match_vars].astype(float).to_numpy()
                    d = float(np.sqrt(np.sum((tr_vec - ctrl_vec) ** 2)))
                    dists.append(d)
                hardness.append((tr["ccn_str"], min(dists) if dists else float("inf")))
            order = [ccn for ccn, _ in sorted(hardness, key=lambda x: (-x[1], x[0]))]
            treated_iter = treated_z.set_index("ccn_str").loc[order].reset_index()
        else:
            treated_iter = treated_z.sort_values("ccn_str").reset_index(drop=True)

        for _, tr in treated_iter.iterrows():
            if len(available_controls) < MATCH_RATIO:
                raise ValueError(f"Insufficient controls left in state {state}")

            exact_pool = available_controls.reset_index()
            for col in exact_cols:
                exact_pool = exact_pool[exact_pool[col].eq(tr[col])]
            if len(exact_pool) >= MATCH_RATIO:
                candidate_controls = exact_pool.set_index("ccn_str")
            else:
                candidate_controls = available_controls

            distances = []
            if method == "linear_score":
                tr_score = float(tr["match_score"])
                for ccn, ctrl in candidate_controls.iterrows():
                    dist = abs(tr_score - float(ctrl["match_score"]))
                    distances.append((ccn, dist))
            else:
                tr_vec = tr[match_vars].astype(float).to_numpy()
                for ccn, ctrl in candidate_controls.iterrows():
                    ctrl_vec = ctrl[match_vars].astype(float).to_numpy()
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

    return pd.DataFrame(pairs).sort_values(
        ["analysis_state", "treated_ccn", "match_rank", "control_ccn"]
    )


def score_pairs(baseline: pd.DataFrame, pairs: pd.DataFrame) -> pd.DataFrame:
    treated_ccns = pairs["treated_ccn"].drop_duplicates()
    control_ccns = pairs["control_ccn"].drop_duplicates()
    treated = baseline[baseline["ccn_str"].isin(treated_ccns)].copy()
    controls = baseline[baseline["ccn_str"].isin(control_ccns)].copy()

    rows = []
    for i, var in enumerate(BALANCE_VARS, start=1):
        t = treated[var]
        c = controls[var]
        t_mean = float(t.dropna().mean()) if t.notna().any() else float("nan")
        c_mean = float(c.dropna().mean()) if c.notna().any() else float("nan")
        diff = t_mean - c_mean
        ps = pooled_std(t, c)
        std_diff = diff / ps if ps and not math.isnan(ps) and ps != 0 else float("nan")
        rows.append(
            {
                "variable": var,
                "control_mean": c_mean,
                "treated_mean": t_mean,
                "diff_estimate": diff,
                "std_diff": std_diff,
                "n_control": int(c.notna().sum()),
                "n_treated": int(t.notna().sum()),
                "row_order": i,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    baseline, _panel, benchmark = load_inputs()

    benchmark_score = float(benchmark["std_diff"].abs().sum())
    summary_rows = []

    for name, spec in VARIANT_SPECS.items():
        pairs = build_pairs(baseline, spec)
        balance = score_pairs(baseline, pairs)
        score = float(balance["std_diff"].abs().sum())
        result = {
            "variant": name,
            "match_ratio": MATCH_RATIO,
            "match_vars": list(spec["match_vars"]),
            "method": spec["method"],
            "order_rule": spec["order_rule"],
            "treated_facilities": int(pairs["treated_ccn"].nunique()),
            "control_facilities": int(pairs["control_ccn"].nunique()),
            "pair_rows": int(len(pairs)),
            "mean_distance": float(pairs["distance"].mean()),
            "max_distance": float(pairs["distance"].max()),
            "overall_balance_score": score,
            "benchmark_balance_score": benchmark_score,
            "beats_benchmark": bool(score < benchmark_score),
        }

        pairs.to_csv(OUTPUT_DIR / f"{name}_pairs.csv", index=False)
        balance.to_csv(OUTPUT_DIR / f"{name}_balance.csv", index=False)
        (OUTPUT_DIR / f"{name}_summary.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        summary_rows.append(result)

    summary = pd.DataFrame(summary_rows).sort_values(
        ["overall_balance_score", "mean_distance", "variant"]
    )
    summary.to_csv(OUTPUT_DIR / "matching_variant_scoreboard.csv", index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
