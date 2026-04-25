#!/usr/bin/env python3
"""Shared utilities for the nursing home PE research project."""

from __future__ import annotations
import re
from pathlib import Path
import pandas as pd
from pandas.api.types import is_object_dtype, is_string_dtype

import os

def get_intermediate_dir(root: Path) -> Path:
    subdir = os.environ.get("REPRO_INTERMEDIATE", "intermediate")
    return root / "data" / subdir

def get_output_dir(root: Path) -> Path:
    return root / os.environ.get("REPRO_OUTPUT", "outputs")

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

def extract_treat_year(value: object) -> int | None:
    if pd.isna(value):
        return None
    match = re.search(r"(20\d{2})", str(value))
    return int(match.group(1)) if match else None

def first_nonmissing(series: pd.Series):
    nonmissing = series.dropna()
    if len(nonmissing) == 0:
        return pd.NA
    return nonmissing.iloc[0]

def collapse_facility_year(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    # Identifies binary columns to use 'max' instead of 'first'
    binary_cols = [c for c in df.columns if c.startswith('has_') or c.startswith('any_') or 'flag' in c]
    agg_map = {}
    for col in df.columns:
        if col in ["ccn_str", "year"]: continue
        agg_map[col] = "max" if col in binary_cols else first_nonmissing
    
    return (
        df.sort_values(["ccn_str", "year"])
        .groupby(["ccn_str", "year"], as_index=False, dropna=False)
        .agg(agg_map)
    )

def export_csv_and_dta(df: pd.DataFrame, csv_path: Path, dta_path: Path) -> None:
    df.to_csv(csv_path, index=False)
    safe = df.copy()
    for col in safe.columns:
        if is_string_dtype(safe[col]):
            safe[col] = safe[col].astype("string").fillna("")
        elif is_object_dtype(safe[col]):
            numeric_candidate = pd.to_numeric(safe[col], errors="coerce")
            if numeric_candidate.notna().any() and numeric_candidate.notna().sum() == safe[col].notna().sum():
                safe[col] = numeric_candidate
            else:
                safe[col] = safe[col].astype("string").fillna("")
    safe.to_stata(dta_path, write_index=False, version=118)
