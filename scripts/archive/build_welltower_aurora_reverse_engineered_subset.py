from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

OWNERS_PATH = ROOT / "data/raw/outcomes/cms/snf_all_owners/SNF_All_Owners_2026.03.02.csv"
ENROLLMENTS_PATH = ROOT / "data/raw/outcomes/cms/snf_enrollments/SNF_Enrollments_2025.07.01.csv"
LTCFOCUS_PATH = ROOT / "data/intermediate/ltcfocus/ltcfocus_facility_year_full.csv"

PROVIDER_FILES = {
    2019: ROOT / "data/raw/outcomes/cms/care_compare_archived_annual/2019/ProviderInfo_Download.csv",
    2020: ROOT / "data/raw/outcomes/cms/care_compare_archived_annual/2020/NH_ProviderInfo_Nov2020.csv",
    2021: ROOT / "data/raw/outcomes/cms/care_compare_archived_annual/2021/NH_ProviderInfo_Nov2021.csv",
    2022: ROOT / "data/raw/outcomes/cms/care_compare_archived_annual/2022/NH_ProviderInfo_Nov2022.csv",
    2023: ROOT / "data/raw/outcomes/cms/care_compare_archived_annual/2023/NH_ProviderInfo_Nov2023.csv",
    2024: ROOT / "data/raw/outcomes/cms/care_compare_archived_annual/2024/NH_ProviderInfo_Nov2024.csv",
    2025: ROOT / "data/raw/outcomes/cms/care_compare_archived_annual/2025/NH_ProviderInfo_Nov2025.csv",
    2026: ROOT / "data/raw/outcomes/cms/care_compare_archived_annual/2026/NH_ProviderInfo_Mar2026.csv",
}

OUT_DIR = ROOT / "research/deal_workfiles/welltower_aurora_reverse_engineered"
SUMMARY_PATH = OUT_DIR / "welltower_aurora_reverse_engineered_summary.csv"
PANEL_PATH = OUT_DIR / "welltower_aurora_reverse_engineered_ltcfocus_2009_2013.csv"
README_PATH = OUT_DIR / "README.md"
META_PATH = OUT_DIR / "summary.json"


def load_provider_history() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for year, path in PROVIDER_FILES.items():
        df = pd.read_csv(path, dtype=str, encoding="latin1")
        cols = set(df.columns)
        if "PROVNUM" in cols:
            out = df[["PROVNUM", "PROVNAME", "CITY", "STATE"]].copy()
            out.columns = ["ccn", "provider_name", "city", "state"]
        elif "Federal Provider Number" in cols:
            out = df[
                ["Federal Provider Number", "Provider Name", "Provider City", "Provider State"]
            ].copy()
            out.columns = ["ccn", "provider_name", "city", "state"]
        else:
            out = df[
                ["CMS Certification Number (CCN)", "Provider Name", "City/Town", "State"]
            ].copy()
            out.columns = ["ccn", "provider_name", "city", "state"]
        out["year"] = year
        frames.append(out)
    return pd.concat(frames, ignore_index=True)


def build_reverse_engineered_cohort() -> pd.DataFrame:
    owners = pd.read_csv(OWNERS_PATH, dtype=str, encoding="latin1")
    enrollments = pd.read_csv(ENROLLMENTS_PATH, dtype=str, encoding="latin1")

    mask = (
        owners["ORGANIZATION NAME - OWNER"].fillna("").str.contains("WELLTOWER", case=False)
        & owners["ASSOCIATION DATE - OWNER"].fillna("").str.contains("2021")
        & owners["ORGANIZATION NAME"].fillna("").str.contains("COMPLETE CARE", case=False)
    )

    cohort = owners.loc[mask].merge(
        enrollments[["ENROLLMENT ID", "CCN", "NURSING HOME PROVIDER NAME", "CITY", "STATE"]],
        on="ENROLLMENT ID",
        how="left",
    )

    cohort["association_date"] = pd.to_datetime(
        cohort["ASSOCIATION DATE - OWNER"], errors="coerce", format="%m/%d/%Y"
    )
    cohort = cohort.sort_values(["CCN", "association_date", "ROLE TEXT - OWNER"])

    keep_cols = [
        "CCN",
        "NURSING HOME PROVIDER NAME",
        "CITY",
        "STATE",
        "ORGANIZATION NAME",
        "ORGANIZATION NAME - OWNER",
        "ROLE TEXT - OWNER",
        "ASSOCIATION DATE - OWNER",
        "REIT - OWNER",
        "PARENT COMPANY - OWNER",
    ]
    return cohort[keep_cols].drop_duplicates()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    provider_history = load_provider_history()
    cohort_raw = build_reverse_engineered_cohort()

    summary_rows: list[dict[str, object]] = []
    for ccn, group in cohort_raw.groupby("CCN", dropna=True):
        group = group.sort_values(["ASSOCIATION DATE - OWNER", "ROLE TEXT - OWNER"])
        names = (
            provider_history.loc[provider_history["ccn"] == ccn, ["year", "provider_name"]]
            .drop_duplicates()
            .sort_values("year")
        )
        row: dict[str, object] = {
            "ccn": ccn,
            "state": group["STATE"].dropna().iloc[0] if group["STATE"].notna().any() else "",
            "city": group["CITY"].dropna().iloc[0] if group["CITY"].notna().any() else "",
            "provider_name_2026": group["NURSING HOME PROVIDER NAME"].dropna().iloc[0]
            if group["NURSING HOME PROVIDER NAME"].notna().any()
            else "",
            "owner_org_current": group["ORGANIZATION NAME"].dropna().iloc[0]
            if group["ORGANIZATION NAME"].notna().any()
            else "",
            "welltower_owner_entity": "|".join(
                pd.unique(group["ORGANIZATION NAME - OWNER"].dropna())
            ),
            "earliest_welltower_assoc_date_2021_rows": group["ASSOCIATION DATE - OWNER"]
            .dropna()
            .iloc[0]
            if group["ASSOCIATION DATE - OWNER"].notna().any()
            else "",
            "ownership_role_rows": "|".join(pd.unique(group["ROLE TEXT - OWNER"].dropna())),
            "reit_owner_flag_values": "|".join(
                pd.unique(group["REIT - OWNER"].fillna("").replace("", pd.NA).dropna())
            ),
            "provider_name_2019": "",
            "provider_name_2020": "",
            "provider_name_2021": "",
            "provider_name_2022": "",
            "provider_name_2023": "",
            "provider_name_2024": "",
            "provider_name_2025": "",
            "provider_name_2026_hist": "",
            "reverse_engineering_basis": (
                "Current CMS ownership file shows a Welltower owner entity with a 2021 "
                "association date on a Complete Care facility row."
            ),
            "public_transaction_context": (
                "Welltower disclosed in March 2021 that 35 traditional Genesis SNFs would "
                "be sold to a JV with Aurora Health Network and Peace Capital, and later "
                "described seven former Genesis facilities transitioned to Complete Care."
            ),
        }
        for _, hist in names.iterrows():
            col = f"provider_name_{int(hist['year'])}"
            if col in row:
                row[col] = hist["provider_name"]
            elif col == "provider_name_2026":
                row["provider_name_2026_hist"] = hist["provider_name"]
        summary_rows.append(row)

    summary = pd.DataFrame(summary_rows).sort_values(["state", "city", "ccn"]).reset_index(drop=True)

    ltcfocus = pd.read_csv(LTCFOCUS_PATH, dtype={"ccn_str": str})
    staffing_cols = [
        "rnhrppd",
        "lpnhrppd",
        "cnahrppd",
        "dchrppd",
        "totbeds",
        "occpct",
        "facility_name_ltcfocus",
        "state",
        "county",
    ]
    subset = ltcfocus.loc[
        ltcfocus["ccn_str"].isin(summary["ccn"]) & ltcfocus["year"].between(2009, 2013),
        ["ccn_str", "year"] + staffing_cols,
    ].copy()
    subset = subset.rename(columns={"ccn_str": "ccn"})

    coverage = (
        subset.assign(has_any_staffing=subset[["rnhrppd", "lpnhrppd", "cnahrppd", "dchrppd"]].notna().any(axis=1))
        .groupby("ccn", as_index=False)
        .agg(
            ltcfocus_years_2009_2013=("year", lambda s: "|".join(str(v) for v in sorted(s.astype(int)))),
            ltcfocus_staffing_years_2009_2013=(
                "has_any_staffing",
                lambda s: str(int(s.sum())),
            ),
        )
    )
    summary = summary.merge(coverage, on="ccn", how="left")
    summary["ltcfocus_years_2009_2013"] = summary["ltcfocus_years_2009_2013"].fillna("")
    summary["ltcfocus_staffing_years_2009_2013"] = summary[
        "ltcfocus_staffing_years_2009_2013"
    ].fillna("0")

    summary.to_csv(SUMMARY_PATH, index=False)
    subset.sort_values(["ccn", "year"]).to_csv(PANEL_PATH, index=False)

    meta = {
        "cohort_facilities": int(summary["ccn"].nunique()),
        "states": sorted(summary["state"].dropna().unique().tolist()),
        "ltcfocus_panel_years": [2009, 2010, 2011, 2012, 2013],
        "notes": [
            "This is a reverse-engineered subset, not a claimed full roster of the 35 Aurora JV Genesis facilities.",
            "Facilities enter the subset when the latest CMS ownership snapshot shows a Welltower owner entity with a 2021 association date on a Complete Care provider row.",
        ],
        "public_sources": {
            "welltower_pr_2021": "https://www.prnewswire.com/news-releases/welltower-announces-substantial-exit-of-genesis-healthcare-operating-relationship-301239097.html",
            "welltower_2021_10k": "https://welltower.com/wp-content/uploads/2022/02/2021-10-K-FINAL-select-Exhibits.pdf",
            "welltower_2024_annual_report": "https://welltower.com/wp-content/uploads/2025/04/2024-Annual-Report.pdf",
            "inquirer_aurora_complete_care_context": "https://www.inquirer.com/business/health/genesis-health-care-integra-welltower-nursing-homes-20230131.html",
        },
    }
    META_PATH.write_text(json.dumps(meta, indent=2))

    readme = f"""# Welltower / Aurora Reverse-Engineered Subset

Files in this folder:

- `welltower_aurora_reverse_engineered_summary.csv`
- `welltower_aurora_reverse_engineered_ltcfocus_2009_2013.csv`
- `summary.json`

Method:

- Start from the current CMS `SNF_All_Owners` snapshot.
- Keep facilities where a Welltower owner entity appears on a `Complete Care` organization row with a 2021 owner association date.
- Join to CMS enrollments for CCN and provider identity.
- Add provider-name history from archived Care Compare files for 2019-2026.
- Pull LTCFocus facility-year data for the matched CCNs in 2009-2013.

Interpretation:

- This is a reverse-engineered subset of likely former Genesis facilities tied to the 2021 Welltower / Aurora / Peace Capital transactions.
- It should be treated as a high-signal working subset, not as a complete roster of the 35 traditional Genesis SNFs sold into the Aurora JV.

Counts:

- Reverse-engineered facilities: {summary['ccn'].nunique()}
- LTCFocus rows in 2009-2013 panel: {len(subset)}
"""
    README_PATH.write_text(readme)


if __name__ == "__main__":
    main()
