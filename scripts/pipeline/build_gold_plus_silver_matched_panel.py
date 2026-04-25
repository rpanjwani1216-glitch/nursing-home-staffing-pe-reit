#!/usr/bin/env python3
"""Build the gold+silver same-state matched panel after a broad variant search."""

from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.api.types import is_object_dtype, is_string_dtype


ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_DIR = ROOT / "data" / "intermediate" / "analysis"
PANELS_DIR = ANALYSIS_DIR / "panels"
BALANCE_DIR = ANALYSIS_DIR / "balance"
MATCHING_DIR = ANALYSIS_DIR / "matching"
QA_DIR = ROOT / "outputs" / "qa" / "matching" / "variants_gold_plus_silver"

PANEL_PATH = PANELS_DIR / "regression_analysis_panel_gold_plus_silver_v2_same_state.csv"
BASELINE_FACILITY_CSV = BALANCE_DIR / "table1_baseline_facility_level_gold_plus_silver_v2_same_state.csv"
BASELINE_FACILITY_DTA = BALANCE_DIR / "table1_baseline_facility_level_gold_plus_silver_v2_same_state.dta"
PAIR_PATH = MATCHING_DIR / "matched_control_pairs_gold_plus_silver_v2_same_state.csv"
CONTROL_PATH = MATCHING_DIR / "matched_control_candidates_gold_plus_silver_v2_same_state.csv"
MATCHED_PANEL_CSV = PANELS_DIR / "regression_analysis_panel_gold_plus_silver_v2_same_state_matched.csv"
MATCHED_PANEL_DTA = PANELS_DIR / "regression_analysis_panel_gold_plus_silver_v2_same_state_matched.dta"
SUMMARY_JSON = MATCHING_DIR / "matched_control_sample_gold_plus_silver_v2_same_state_summary.json"
SCOREBOARD_CSV = QA_DIR / "matching_variant_scoreboard_gold_plus_silver.csv"
SCOREBOARD_JSON = QA_DIR / "matching_variant_scoreboard_gold_plus_silver.json"
BEST_BALANCE_CSV = QA_DIR / "best_match_balance_gold_plus_silver.csv"
BEST_SPEC_JSON = QA_DIR / "best_match_spec_gold_plus_silver.json"

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

NEAREST_VARIANTS: dict[str, dict[str, object]] = {
    "nn_ops_only": {
        "match_vars": [
            "provider_certified_beds",
            "provider_avg_residents_per_day",
            "pbj_mean_rn_hprd",
            "pbj_mean_nurse_hprd",
        ],
        "method": "nearest_neighbor",
        "order_rule": "ccn",
        "exact_cols": [],
    },
    "nn_ratings_ownership": {
        "match_vars": [
            "provider_health_rating",
            "provider_overall_rating",
            "provider_staffing_rating",
            "chain_affiliated",
            "for_profit",
        ],
        "method": "nearest_neighbor",
        "order_rule": "ccn",
        "exact_cols": [],
    },
    "nn_size_ratings": {
        "match_vars": [
            "provider_certified_beds",
            "provider_avg_residents_per_day",
            "provider_health_rating",
            "provider_overall_rating",
            "provider_staffing_rating",
        ],
        "method": "nearest_neighbor",
        "order_rule": "ccn",
        "exact_cols": [],
    },
    "nn_hybrid_ops_ownership": {
        "match_vars": [
            "provider_certified_beds",
            "provider_avg_residents_per_day",
            "pbj_mean_rn_hprd",
            "provider_health_rating",
            "provider_overall_rating",
            "chain_affiliated",
            "for_profit",
        ],
        "method": "nearest_neighbor",
        "order_rule": "ccn",
        "exact_cols": [],
    },
    "nn_full": {
        "match_vars": BALANCE_VARS,
        "method": "nearest_neighbor",
        "order_rule": "ccn",
        "exact_cols": [],
    },
    "nn_full_hardest_first": {
        "match_vars": BALANCE_VARS,
        "method": "nearest_neighbor",
        "order_rule": "hardest_first",
        "exact_cols": [],
    },
    "nn_full_exact_fp": {
        "match_vars": BALANCE_VARS,
        "method": "nearest_neighbor",
        "order_rule": "ccn",
        "exact_cols": ["for_profit_bin"],
    },
    "nn_full_exact_chain": {
        "match_vars": BALANCE_VARS,
        "method": "nearest_neighbor",
        "order_rule": "ccn",
        "exact_cols": ["chain_any_bin"],
    },
    "nn_full_exact_fp_chain": {
        "match_vars": BALANCE_VARS,
        "method": "nearest_neighbor",
        "order_rule": "ccn",
        "exact_cols": ["for_profit_bin", "chain_any_bin"],
    },
    "nn_full_hardest_exact_fp": {
        "match_vars": BALANCE_VARS,
        "method": "nearest_neighbor",
        "order_rule": "hardest_first",
        "exact_cols": ["for_profit_bin"],
    },
    "nn_full_hardest_exact_chain": {
        "match_vars": BALANCE_VARS,
        "method": "nearest_neighbor",
        "order_rule": "hardest_first",
        "exact_cols": ["chain_any_bin"],
    },
    "nn_full_hardest_exact_fp_chain": {
        "match_vars": BALANCE_VARS,
        "method": "nearest_neighbor",
        "order_rule": "hardest_first",
        "exact_cols": ["for_profit_bin", "chain_any_bin"],
    },
}


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


def canonical_ccn(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if digits == "":
        return text.upper()
    return digits.zfill(6)


def pooled_std(treated: pd.Series, control: pd.Series) -> float:
    t = treated.dropna().astype(float)
    c = control.dropna().astype(float)
    if len(t) == 0 or len(c) == 0:
        return float("nan")
    return math.sqrt((float(t.var(ddof=0)) + float(c.var(ddof=0))) / 2.0)


def load_panel() -> pd.DataFrame:
    panel = pd.read_csv(PANEL_PATH, dtype={"ccn_str": "string"}, low_memory=False)
    panel["ccn_str"] = panel["ccn_str"].map(canonical_ccn).astype("string")
    panel["year"] = pd.to_numeric(panel["year"], errors="coerce")
    panel["treat_year"] = pd.to_numeric(panel["treat_year"], errors="coerce")
    panel = panel[panel["sample_main_staffing"].eq(1) & panel["ccn_str"].notna()].copy()
    panel["treated_ever"] = panel["sample_role"].eq("treated").astype(int)
    panel["chain_affiliated"] = np.where(panel["provider_chain_id"].notna(), 1.0, 0.0)
    ownership = panel["provider_ownership_type"].fillna("").astype(str).str.lower()
    panel["for_profit"] = ownership.str.contains("for profit").astype(float)
    return panel


def build_baseline(panel: pd.DataFrame) -> pd.DataFrame:
    table_vars = BALANCE_VARS
    facility_meta = (
        panel[
            [
                "ccn_str",
                "sample_role",
                "analysis_state",
                "treatment_analysis_sample",
                "provider_name",
                "treat_year",
                "year",
            ]
        ]
        .sort_values(["ccn_str", "year"])
        .drop_duplicates(subset=["ccn_str"], keep="first")
        .copy()
    )

    treated_facilities = panel.loc[panel["treated_ever"].eq(1), ["ccn_str", "treat_year"]].drop_duplicates()
    cohort_weights = (
        treated_facilities.groupby("treat_year")
        .size()
        .rename("treated_count")
        .reset_index()
        .rename(columns={"treat_year": "cohort_year"})
    )
    cohort_weights["cohort_weight"] = cohort_weights["treated_count"] / cohort_weights["treated_count"].sum()

    treated_pre = panel[panel["treated_ever"].eq(1) & panel["year"].lt(panel["treat_year"])].copy()
    treated_baseline = (
        treated_pre.groupby("ccn_str", as_index=False)[table_vars]
        .mean()
        .merge(
            treated_pre.groupby("ccn_str").size().rename("baseline_support_years").reset_index(),
            on="ccn_str",
            how="left",
        )
    )

    controls = panel[panel["treated_ever"].eq(0)].copy()
    controls["join_key"] = 1
    cohort_weights = cohort_weights.copy()
    cohort_weights["join_key"] = 1
    control_long = controls.merge(cohort_weights, on="join_key", how="inner")
    control_long = control_long[control_long["year"].lt(control_long["cohort_year"])].copy()

    control_cohort_means = (
        control_long.groupby(["ccn_str", "cohort_year"], as_index=False)[table_vars]
        .mean()
        .merge(cohort_weights[["cohort_year", "cohort_weight"]], on="cohort_year", how="left")
    )
    control_baseline = control_cohort_means[["ccn_str"]].drop_duplicates().copy()
    control_baseline["valid_pseudocohorts"] = (
        control_cohort_means.groupby("ccn_str")["cohort_year"].transform("nunique")
    )

    for var in table_vars:
        tmp = control_cohort_means[["ccn_str", "cohort_weight", var]].copy()
        tmp["weight_component"] = np.where(tmp[var].notna(), tmp["cohort_weight"], 0.0)
        valid_weight_total = tmp.groupby("ccn_str")["weight_component"].transform("sum")
        tmp["weighted_component"] = np.where(
            tmp[var].notna() & valid_weight_total.gt(0),
            (tmp["cohort_weight"] / valid_weight_total) * tmp[var],
            0.0,
        )
        collapsed = tmp.groupby("ccn_str", as_index=False)["weighted_component"].sum().rename(
            columns={"weighted_component": var}
        )
        control_baseline = control_baseline.merge(collapsed, on="ccn_str", how="left")

    baseline = pd.concat(
        [
            treated_baseline.assign(sample_role="treated"),
            control_baseline.assign(sample_role="control"),
        ],
        ignore_index=True,
        sort=False,
    )

    baseline = baseline.merge(
        facility_meta[
            [
                "ccn_str",
                "sample_role",
                "analysis_state",
                "treatment_analysis_sample",
                "provider_name",
                "treat_year",
            ]
        ],
        on=["ccn_str", "sample_role"],
        how="left",
    )
    baseline["treated_ever"] = baseline["sample_role"].eq("treated").astype(int)
    baseline["for_profit_bin"] = (baseline["for_profit"].fillna(0) >= 0.5).astype(int)
    baseline["chain_any_bin"] = (baseline["chain_affiliated"].fillna(0) > 0).astype(int)
    return baseline


def standardize_by_state(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for _, idx in out.groupby("analysis_state").groups.items():
        state_df = out.loc[idx, cols].astype(float)
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


def nearest_distance(tr_vec: np.ndarray, ctrl_matrix: np.ndarray) -> np.ndarray:
    return np.sqrt(np.sum((ctrl_matrix - tr_vec) ** 2, axis=1))


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
        if len(controls_state) < MATCH_RATIO * len(treated_state):
            raise ValueError(f"Insufficient controls in state {state} for ratio {MATCH_RATIO}")

        state_all = pd.concat([treated_state, controls_state], ignore_index=True)
        state_all = standardize_by_state(state_all, match_vars)

        if method == "linear_score":
            state_all = state_all.copy()
            state_all["match_score"] = linear_score_features(state_all, match_vars)

        treated_z = state_all[state_all["sample_role"].eq("treated")].copy().reset_index(drop=True)
        controls_z = state_all[state_all["sample_role"].eq("control")].copy().reset_index(drop=True)

        if order_rule == "hardest_first":
            hardness = []
            full_ctrl = controls_z.copy()
            for _, tr in treated_z.iterrows():
                candidate = full_ctrl
                for col in exact_cols:
                    candidate = candidate[candidate[col].eq(tr[col])]
                if len(candidate) < MATCH_RATIO:
                    candidate = full_ctrl
                if method == "linear_score":
                    dist = np.abs(candidate["match_score"].to_numpy(dtype=float) - float(tr["match_score"]))
                else:
                    dist = nearest_distance(
                        tr[match_vars].astype(float).to_numpy(),
                        candidate[match_vars].astype(float).to_numpy(),
                    )
                hardness.append((tr["ccn_str"], float(np.min(dist))))
            order = [ccn for ccn, _ in sorted(hardness, key=lambda x: (-x[1], x[0]))]
            treated_z = treated_z.set_index("ccn_str").loc[order].reset_index()
        else:
            treated_z = treated_z.sort_values("ccn_str").reset_index(drop=True)

        available_controls = controls_z.copy()

        for _, tr in treated_z.iterrows():
            candidate = available_controls
            for col in exact_cols:
                candidate = candidate[candidate[col].eq(tr[col])]
            if len(candidate) < MATCH_RATIO:
                candidate = available_controls
            if len(candidate) < MATCH_RATIO:
                raise ValueError(f"Insufficient controls left in state {state}")

            if method == "linear_score":
                dists = np.abs(candidate["match_score"].to_numpy(dtype=float) - float(tr["match_score"]))
            else:
                dists = nearest_distance(
                    tr[match_vars].astype(float).to_numpy(),
                    candidate[match_vars].astype(float).to_numpy(),
                )
            candidate = candidate.assign(_distance=dists)
            chosen = candidate.sort_values(["_distance", "ccn_str"]).head(MATCH_RATIO)

            for rank, (_, ctrl) in enumerate(chosen.iterrows(), start=1):
                pairs.append(
                    {
                        "treated_ccn": tr["ccn_str"],
                        "control_ccn": ctrl["ccn_str"],
                        "analysis_state": state,
                        "match_rank": rank,
                        "distance": float(ctrl["_distance"]),
                    }
                )
            available_controls = available_controls[~available_controls["ccn_str"].isin(chosen["ccn_str"])].copy()

    return pd.DataFrame(pairs).sort_values(
        ["analysis_state", "treated_ccn", "match_rank", "control_ccn"]
    ).reset_index(drop=True)


def score_pairs(baseline: pd.DataFrame, pairs: pd.DataFrame) -> pd.DataFrame:
    treated_ccns = pairs["treated_ccn"].drop_duplicates()
    control_ccns = pairs["control_ccn"].drop_duplicates()

    treated = baseline[baseline["ccn_str"].isin(treated_ccns)].copy()
    control = baseline[baseline["ccn_str"].isin(control_ccns)].copy()

    rows = []
    for var in BALANCE_VARS:
        t = treated[var].astype(float)
        c = control[var].astype(float)
        t_mean = float(t.mean())
        c_mean = float(c.mean())
        diff = t_mean - c_mean
        psd = pooled_std(t, c)
        std_diff = diff / psd if psd and not math.isnan(psd) and psd > 0 else float("nan")
        rows.append(
            {
                "variable": var,
                "treated_mean": t_mean,
                "control_mean": c_mean,
                "diff": diff,
                "std_diff": std_diff,
                "abs_std_diff": abs(std_diff) if not math.isnan(std_diff) else float("nan"),
                "n_treated": int(t.notna().sum()),
                "n_control": int(c.notna().sum()),
            }
        )
    return pd.DataFrame(rows)


def exhaustive_linear_variants() -> dict[str, dict[str, object]]:
    variants: dict[str, dict[str, object]] = {}
    exact_options = {
        "none": [],
        "exact_fp": ["for_profit_bin"],
        "exact_chain": ["chain_any_bin"],
        "exact_fp_chain": ["for_profit_bin", "chain_any_bin"],
    }
    for size in range(1, len(BALANCE_VARS) + 1):
        for cols in itertools.combinations(BALANCE_VARS, size):
            slug = "_".join(
                col.replace("provider_", "")
                .replace("pbj_mean_", "")
                .replace("_rating", "")
                .replace("_per_day", "")
                .replace("_hours", "")
                .replace("_resident", "")
                .replace("_", "")
                for col in cols
            )
            for exact_name, exact_cols in exact_options.items():
                name = f"linear_{slug}_{exact_name}"
                variants[name] = {
                    "match_vars": list(cols),
                    "method": "linear_score",
                    "order_rule": "ccn",
                    "exact_cols": exact_cols,
                }
    return variants


def evaluate_variants(baseline: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object], pd.DataFrame, pd.DataFrame]:
    variants = {}
    variants.update(exhaustive_linear_variants())
    variants.update(NEAREST_VARIANTS)

    scoreboard = []
    best_name = None
    best_pairs = None
    best_balance = None
    best_tuple = None

    for idx, (name, spec) in enumerate(variants.items(), start=1):
        try:
            pairs = build_pairs(baseline, spec)
            balance = score_pairs(baseline, pairs)
            overall = float(balance["abs_std_diff"].sum())
            max_abs = float(balance["abs_std_diff"].max())
            mean_abs = float(balance["abs_std_diff"].mean())
            mean_distance = float(pairs["distance"].mean())
            scoreboard.append(
                {
                    "variant": name,
                    "rank_candidate": idx,
                    "method": spec["method"],
                    "order_rule": spec["order_rule"],
                    "exact_cols": ",".join(spec.get("exact_cols", [])),
                    "match_vars": ",".join(spec["match_vars"]),
                    "n_match_vars": len(spec["match_vars"]),
                    "overall_balance_score": overall,
                    "max_abs_std_diff": max_abs,
                    "mean_abs_std_diff": mean_abs,
                    "mean_distance": mean_distance,
                    "matched_control_facilities": int(pairs["control_ccn"].nunique()),
                }
            )
            candidate_tuple = (overall, max_abs, mean_abs, mean_distance, name)
            if best_tuple is None or candidate_tuple < best_tuple:
                best_tuple = candidate_tuple
                best_name = name
                best_pairs = pairs
                best_balance = balance
        except Exception as exc:  # noqa: BLE001
            scoreboard.append(
                {
                    "variant": name,
                    "rank_candidate": idx,
                    "method": spec["method"],
                    "order_rule": spec["order_rule"],
                    "exact_cols": ",".join(spec.get("exact_cols", [])),
                    "match_vars": ",".join(spec["match_vars"]),
                    "n_match_vars": len(spec["match_vars"]),
                    "overall_balance_score": float("inf"),
                    "max_abs_std_diff": float("inf"),
                    "mean_abs_std_diff": float("inf"),
                    "mean_distance": float("inf"),
                    "matched_control_facilities": 0,
                    "error": str(exc),
                }
            )

    assert best_name is not None and best_pairs is not None and best_balance is not None
    scoreboard_df = pd.DataFrame(scoreboard).sort_values(
        ["overall_balance_score", "max_abs_std_diff", "mean_abs_std_diff", "mean_distance", "variant"]
    ).reset_index(drop=True)
    scoreboard_df["rank"] = np.arange(1, len(scoreboard_df) + 1)
    best_spec = variants[best_name] | {"variant": best_name}
    return scoreboard_df, best_spec, best_pairs, best_balance


def main() -> None:
    MATCHING_DIR.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)
    BALANCE_DIR.mkdir(parents=True, exist_ok=True)
    PANELS_DIR.mkdir(parents=True, exist_ok=True)

    panel = load_panel()
    baseline = build_baseline(panel)
    export_csv_and_dta(baseline, BASELINE_FACILITY_CSV, BASELINE_FACILITY_DTA)

    scoreboard, best_spec, best_pairs, best_balance = evaluate_variants(baseline)
    scoreboard.to_csv(SCOREBOARD_CSV, index=False)
    SCOREBOARD_JSON.write_text(scoreboard.to_json(orient="records", indent=2), encoding="utf-8")
    best_balance.to_csv(BEST_BALANCE_CSV, index=False)
    BEST_SPEC_JSON.write_text(json.dumps(best_spec, indent=2), encoding="utf-8")

    best_pairs.to_csv(PAIR_PATH, index=False)
    matched_controls = (
        best_pairs[["control_ccn"]]
        .drop_duplicates()
        .rename(columns={"control_ccn": "ccn_str"})
        .assign(matched_control=1)
    )
    matched_controls.to_csv(CONTROL_PATH, index=False)

    matched_ccns = set(best_pairs["treated_ccn"]).union(set(best_pairs["control_ccn"]))
    matched_panel = panel[panel["ccn_str"].isin(matched_ccns)].copy()
    matched_panel["matched_sample"] = 1
    matched_panel["analysis_spec"] = "gold_plus_silver_v2_same_state_matched"
    matched_panel["analysis_sample_label"] = np.where(
        matched_panel["sample_role"].eq("treated"),
        matched_panel["treatment_analysis_sample"].fillna("gold_plus_silver"),
        "control_same_state_matched",
    )
    export_csv_and_dta(matched_panel, MATCHED_PANEL_CSV, MATCHED_PANEL_DTA)

    summary = {
        "analysis_spec": "gold_plus_silver_v2_same_state_matched",
        "match_ratio": MATCH_RATIO,
        "treated_facilities": int(best_pairs["treated_ccn"].nunique()),
        "matched_control_facilities": int(best_pairs["control_ccn"].nunique()),
        "pair_rows": int(len(best_pairs)),
        "matched_panel_rows": int(len(matched_panel)),
        "matched_panel_unique_facilities": int(matched_panel["ccn_str"].nunique()),
        "best_variant": best_spec["variant"],
        "best_method": best_spec["method"],
        "best_order_rule": best_spec["order_rule"],
        "best_exact_cols": best_spec["exact_cols"],
        "best_match_vars": best_spec["match_vars"],
        "best_overall_balance_score": float(best_balance["abs_std_diff"].sum()),
        "best_max_abs_std_diff": float(best_balance["abs_std_diff"].max()),
        "best_mean_distance": float(best_pairs["distance"].mean()),
        "top5_variants": scoreboard.head(5).to_dict(orient="records"),
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
