#!/usr/bin/env python3
"""Build raw extracts and a facility-level REIT ownership investigation summary.

The workflow is intentionally conservative:

1. Identify the 175 facilities in the national panel that have at least one
   consecutive-year run with ``any_reit_owner == True``.
2. Export raw panel, owner-history, and CHOW extracts for those facilities.
3. Build a facility-level summary that keeps the raw CMS owner entity name,
   groups facilities into ownership clusters, and records the earliest observed
   REIT-owner association date plus any nearby CHOW-based prior owner.

Major cluster labels are cross-walked to official company sources. Smaller
one-off entities remain labeled directly from the CMS raw owner name.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PANEL_PATH = ROOT / "data" / "intermediate" / "analysis" / "panels" / "regression_analysis_panel_gold_v2.csv"
OWNER_MONTHLY_PATH = ROOT / "data" / "intermediate" / "cms" / "snf_all_owners_monthly.csv"
CHOW_EVENTS_PATH = ROOT / "data" / "intermediate" / "cms" / "snf_chow_events.csv"
OUTPUT_DIR = ROOT / "research" / "reit_ownership_investigation"

RAW_PANEL_OUTPUT = OUTPUT_DIR / "reit_consecutive_homes_panel_raw.csv"
RAW_OWNER_OUTPUT = OUTPUT_DIR / "reit_consecutive_homes_owner_history_raw.csv"
RAW_CHOW_OUTPUT = OUTPUT_DIR / "reit_consecutive_homes_chow_raw.csv"
SUMMARY_OUTPUT = OUTPUT_DIR / "reit_consecutive_homes_investigated.csv"
CLUSTER_OUTPUT = OUTPUT_DIR / "reit_owner_clusters.csv"
NOTES_OUTPUT = OUTPUT_DIR / "README.md"


@dataclass(frozen=True)
class ClusterRule:
    pattern: re.Pattern[str]
    cluster_label: str
    parent_owner_name: str
    source_type: str
    source_label: str
    source_url: str
    source_note: str


CLUSTER_RULES: list[ClusterRule] = [
    ClusterRule(
        pattern=re.compile(
            r"AMERICAN HEALTHCARE REIT|TRILOGY REAL ESTATE INVESTMENT TRUST|"
            r"TRILOGY REIT HOLDINGS|GRIFFIN-AMERICAN HEALTHCARE REIT",
            re.I,
        ),
        cluster_label="American Healthcare REIT / Trilogy",
        parent_owner_name="American Healthcare REIT, Inc.",
        source_type="official_company_ir",
        source_label="American Healthcare REIT investor relations",
        source_url=(
            "https://ir.americanhealthcarereit.com/news/news-details/2024/"
            "American-Healthcare-REIT-Acquires-Remaining-Minority-Membership-"
            "Interest-in-Trilogy-REIT-Holdings-Becomes-Sole-Owner-of-Trilogy-"
            "REIT-Holdings/default.aspx"
        ),
        source_note=(
            "American Healthcare REIT said in September 2024 that it became the "
            "sole owner of Trilogy REIT Holdings."
        ),
    ),
    ClusterRule(
        pattern=re.compile(
            r"OMEGA HEALTHCARE INVESTORS|OMEGA HEALTH INVESTORS|OHI ASSET|"
            r"\bAVIV\b|BHG AVIV",
            re.I,
        ),
        cluster_label="Omega Healthcare Investors",
        parent_owner_name="Omega Healthcare Investors, Inc.",
        source_type="official_company_site",
        source_label="Omega Healthcare Investors official site",
        source_url="https://www.omegahealthcare.com/about-us",
        source_note=(
            "Omega describes itself as a REIT focused primarily on skilled "
            "nursing and assisted living facilities."
        ),
    ),
    ClusterRule(
        pattern=re.compile(r"NATIONAL HEALTH INVESTORS|NHI-REIT", re.I),
        cluster_label="National Health Investors",
        parent_owner_name="National Health Investors, Inc.",
        source_type="official_company_ir",
        source_label="National Health Investors investor relations",
        source_url="https://investors.nhireit.com/",
        source_note=(
            "NHI says it is a REIT specializing in senior housing, skilled "
            "nursing facilities, and medical investments."
        ),
    ),
    ClusterRule(
        pattern=re.compile(r"HEALTHPEAK", re.I),
        cluster_label="Healthpeak Properties",
        parent_owner_name="Healthpeak Properties, Inc.",
        source_type="official_company_site",
        source_label="Healthpeak official site",
        source_url="https://healthpeak.com/about/",
        source_note=(
            "Healthpeak says it is a healthcare REIT that manages senior "
            "housing communities alongside other healthcare real estate."
        ),
    ),
    ClusterRule(
        pattern=re.compile(r"WELLTOWER", re.I),
        cluster_label="Welltower",
        parent_owner_name="Welltower Inc.",
        source_type="official_company_site",
        source_label="Welltower product overview",
        source_url="https://welltower.com/product-overview/",
        source_note=(
            "Welltower describes post-acute care as part of its healthcare real "
            "estate platform."
        ),
    ),
    ClusterRule(
        pattern=re.compile(r"CARETRUST", re.I),
        cluster_label="CareTrust REIT",
        parent_owner_name="CareTrust REIT, Inc.",
        source_type="official_company_site",
        source_label="CareTrust official site",
        source_url="https://www.caretrustreit.com/what-we-do",
        source_note=(
            "CareTrust says it is a healthcare REIT focused on acquiring and "
            "leasing skilled nursing and seniors housing properties."
        ),
    ),
    ClusterRule(
        pattern=re.compile(r"SABRA", re.I),
        cluster_label="Sabra Health Care REIT",
        parent_owner_name="Sabra Health Care REIT, Inc.",
        source_type="official_company_ir",
        source_label="Sabra investor overview",
        source_url="https://ir.sabrahealth.com/investors/overview/",
        source_note=(
            "Sabra says it owns and invests in healthcare real estate, including "
            "skilled nursing facilities."
        ),
    ),
]

ORG_HINT = re.compile(
    r"\b("
    r"LLC|L\.L\.C\.|LP|L\.P\.|INC|INC\.|CORP|CORPORATION|HOSPITAL|"
    r"TRUST(?!EE)|REIT|LTD|LIMITED|COMPANY|ASSOCIATES|PROPERTIES|VENTURES|"
    r"PARTNERS|CENTER|CAMPUS|CARE|HEALTH|HEALTHCARE|NURSING|HOLDINGS|"
    r"HOLDCO|PROPERTY|COMMUNITIES|OPERATIONS|OPCO|REALTY|VILLAGE|FACILITY"
    r")\b",
    re.I,
)
LEGAL_ENTITY_HINT = re.compile(
    r"\b(LLC|L\.L\.C\.|LP|L\.P\.|INC|INC\.|CORP|CORPORATION|HOSPITAL|"
    r"TRUST(?!EE)|REIT|LTD|LIMITED|ASSOCIATES|PROPERTIES|VENTURES|"
    r"PARTNERS|HOLDINGS|HOLDCO|PROPERTY|COMMUNITIES|OPERATIONS|OPCO|REALTY)\b",
    re.I,
)
TITLE_HINT = re.compile(
    r"\b(CEO|CFO|COO|PRESIDENT|VICE PRESIDENT|SECRETARY|TREASURER|"
    r"ADMINISTRATOR|DIRECTOR|BOARD|CHAIR|MEMBER)\b",
    re.I,
)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "1.0", "true", "t", "yes", "y"}


def clean_name(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def owner_entity_display(row: pd.Series) -> str:
    org = clean_name(row.get("ORGANIZATION NAME - OWNER"))
    if org:
        return org
    dba = clean_name(row.get("DOING BUSINESS AS NAME - OWNER"))
    if dba:
        return dba
    person_bits = [
        clean_name(row.get("FIRST NAME - OWNER")),
        clean_name(row.get("MIDDLE NAME - OWNER")),
        clean_name(row.get("LAST NAME - OWNER")),
        clean_name(row.get("TITLE - OWNER")),
    ]
    person = clean_name(" ".join(bit for bit in person_bits if bit))
    return person


def owner_entity_priority(value: str) -> int:
    text = clean_name(value)
    if not text:
        return 2
    if TITLE_HINT.search(text) and not LEGAL_ENTITY_HINT.search(text):
        return 1
    if ORG_HINT.search(text):
        return 0
    return 1


def parse_mmddyyyy(value: object) -> pd.Timestamp | pd.NaT:
    if pd.isna(value) or str(value).strip() == "":
        return pd.NaT
    return pd.to_datetime(value, format="%m/%d/%Y", errors="coerce")


def classify_owner(owner_name: str) -> dict[str, str]:
    cleaned = clean_name(owner_name)
    for rule in CLUSTER_RULES:
        if rule.pattern.search(cleaned):
            return {
                "owner_cluster": rule.cluster_label,
                "parent_owner_name": rule.parent_owner_name,
                "source_type": rule.source_type,
                "source_label": rule.source_label,
                "source_url": rule.source_url,
                "source_note": rule.source_note,
            }
    return {
        "owner_cluster": cleaned,
        "parent_owner_name": cleaned,
        "source_type": "cms_raw_owner_file_only",
        "source_label": "CMS SNF All Owners raw ownership file",
        "source_url": "",
        "source_note": (
            "No additional official web source attached in this pass; owner "
            "name carried directly from the CMS raw ownership snapshot."
        ),
    }


def format_date(value: pd.Timestamp | pd.NaT) -> str:
    if pd.isna(value):
        return ""
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def format_pipe(values: list[object]) -> str:
    cleaned = [clean_name(v) for v in values if clean_name(v)]
    if not cleaned:
        return ""
    return "|".join(dict.fromkeys(cleaned))


def longest_run(years: list[int]) -> tuple[int | None, int | None, int]:
    if not years:
        return None, None, 0
    ordered = sorted(set(years))
    best_start = ordered[0]
    best_end = ordered[0]
    best_len = 1
    cur_start = ordered[0]
    cur_end = ordered[0]
    for year in ordered[1:]:
        if year == cur_end + 1:
            cur_end = year
        else:
            if (cur_end - cur_start + 1) > best_len:
                best_start, best_end, best_len = cur_start, cur_end, cur_end - cur_start + 1
            cur_start = year
            cur_end = year
    if (cur_end - cur_start + 1) > best_len:
        best_start, best_end, best_len = cur_start, cur_end, cur_end - cur_start + 1
    return best_start, best_end, best_len


def build_cohort(panel: pd.DataFrame) -> tuple[set[str], dict[str, dict[str, object]]]:
    cohort: set[str] = set()
    facility_meta: dict[str, dict[str, object]] = {}
    years_by_ccn: defaultdict[str, list[int]] = defaultdict(list)

    panel = panel.copy()
    panel["reit_flag"] = panel["any_reit_owner"].map(truthy)
    panel["year"] = pd.to_numeric(panel["year"], errors="coerce").astype("Int64")

    for row in panel.itertuples(index=False):
        ccn = clean_name(row.ccn_str)
        if not ccn:
            continue
        if row.reit_flag and pd.notna(row.year):
            years_by_ccn[ccn].append(int(row.year))

    latest_panel = (
        panel.sort_values(["ccn_str", "year"])
        .groupby("ccn_str", as_index=False)
        .tail(1)
        .set_index("ccn_str")
    )

    for ccn, years in years_by_ccn.items():
        start, end, run_len = longest_run(years)
        if run_len < 2:
            continue
        cohort.add(ccn)
        latest = latest_panel.loc[ccn]
        facility_meta[ccn] = {
            "facility_name": clean_name(latest.get("analysis_facility_name") or latest.get("provider_name")),
            "state": clean_name(latest.get("analysis_state") or latest.get("provider_state")),
            "sample_role": clean_name(latest.get("sample_role")),
            "provider_chain_name": clean_name(latest.get("provider_chain_name")),
            "reit_years": sorted(set(int(y) for y in years)),
            "consecutive_run_start": start,
            "consecutive_run_end": end,
            "consecutive_run_length": run_len,
        }
    return cohort, facility_meta


def pick_relevant_chow_event(
    buyer_events: pd.DataFrame,
    owner_takeover_date: pd.Timestamp | pd.NaT,
    first_reit_snapshot: pd.Timestamp | pd.NaT,
) -> pd.Series | None:
    if buyer_events.empty:
        return None
    buyer_events = buyer_events.copy()
    buyer_events["effective_date"] = pd.to_datetime(buyer_events["effective_date"], errors="coerce")
    anchor = owner_takeover_date
    if pd.isna(anchor):
        anchor = first_reit_snapshot
    if pd.isna(anchor):
        return buyer_events.sort_values("effective_date").iloc[-1]

    buyer_events["distance_days"] = (buyer_events["effective_date"] - anchor).abs().dt.days
    nearby = buyer_events[buyer_events["distance_days"].le(730)].sort_values(
        ["distance_days", "effective_date"]
    )
    if not nearby.empty:
        return nearby.iloc[0]

    prior = buyer_events[buyer_events["effective_date"].le(anchor)].sort_values("effective_date")
    if not prior.empty:
        return prior.iloc[-1]
    return buyer_events.sort_values("effective_date").iloc[0]


def main() -> None:
    ensure_dir(OUTPUT_DIR)

    panel = pd.read_csv(PANEL_PATH, dtype="string", low_memory=False)
    cohort, facility_meta = build_cohort(panel)
    cohort_list = sorted(cohort)

    panel_raw = panel[panel["ccn_str"].isin(cohort_list)].copy()
    panel_raw = panel_raw.sort_values(["ccn_str", "year"])
    panel_raw.to_csv(RAW_PANEL_OUTPUT, index=False)

    owner_records: list[dict[str, str]] = []
    with OWNER_MONTHLY_PATH.open(newline="") as fh:
        for row in csv.DictReader(fh):
            if clean_name(row.get("ccn_str")) in cohort:
                owner_records.append(row)
    owner_history = pd.DataFrame(owner_records)

    owner_raw = owner_history.copy()
    owner_raw["owner_reit_flag_bool"] = owner_raw["owner_reit_flag"].map(truthy)
    owner_raw["snapshot_date_ts"] = pd.to_datetime(owner_raw["snapshot_date"], errors="coerce")
    owner_raw["association_date_ts"] = owner_raw["ASSOCIATION DATE - OWNER"].map(parse_mmddyyyy)
    owner_raw["percentage_ownership_num"] = pd.to_numeric(
        owner_raw["PERCENTAGE OWNERSHIP"], errors="coerce"
    )
    owner_raw["owner_name_raw"] = owner_raw.apply(owner_entity_display, axis=1)
    owner_raw["owner_cluster"] = owner_raw["owner_name_raw"].map(
        lambda x: classify_owner(x)["owner_cluster"]
    )
    owner_raw.sort_values(["ccn_str", "snapshot_date_ts", "owner_name_raw"]).to_csv(
        RAW_OWNER_OUTPUT, index=False
    )

    chow_records: list[dict[str, str]] = []
    with CHOW_EVENTS_PATH.open(newline="") as fh:
        for row in csv.DictReader(fh):
            if clean_name(row.get("ccn_buyer_str")) in cohort or clean_name(
                row.get("ccn_seller_str")
            ) in cohort:
                chow_records.append(row)
    chow = pd.DataFrame(chow_records)

    chow_raw = chow.copy()
    chow_raw["effective_date"] = pd.to_datetime(chow_raw["effective_date"], errors="coerce")
    chow_raw.sort_values(["effective_date", "ccn_buyer_str", "ccn_seller_str"]).to_csv(
        RAW_CHOW_OUTPUT, index=False
    )

    summary_rows: list[dict[str, object]] = []
    cluster_counter: Counter[str] = Counter()

    for ccn in cohort_list:
        facility_owner_rows = owner_raw[owner_raw["ccn_str"] == ccn].copy()
        facility_reit_rows = facility_owner_rows[facility_owner_rows["owner_reit_flag_bool"]].copy()
        if facility_reit_rows.empty:
            continue

        first_reit_snapshot = facility_reit_rows["snapshot_date_ts"].dropna().min()
        last_reit_snapshot = facility_reit_rows["snapshot_date_ts"].dropna().max()

        named_reit_rows = facility_reit_rows[facility_reit_rows["owner_name_raw"].ne("")].copy()
        named_reit_org_rows = named_reit_rows[
            named_reit_rows["owner_name_raw"].map(owner_entity_priority).eq(0)
        ].copy()
        if not named_reit_org_rows.empty:
            owner_identification_method = "named_reit_owner_row"
            named_reit_org_rows["entity_priority"] = named_reit_org_rows["owner_name_raw"].map(
                owner_entity_priority
            )
            owner_counts = (
                named_reit_org_rows.groupby(["entity_priority", "owner_name_raw"], dropna=False)
                .size()
                .reset_index(name="n")
                .sort_values(["entity_priority", "n", "owner_name_raw"], ascending=[True, False, True])
            )
            owner_name_raw_primary = clean_name(owner_counts.iloc[0]["owner_name_raw"])
            primary_cluster_meta = classify_owner(owner_name_raw_primary)
            owner_cluster = primary_cluster_meta["owner_cluster"]
            cluster_rows = named_reit_org_rows[
                named_reit_org_rows["owner_cluster"].eq(owner_cluster)
            ].copy()
            if cluster_rows.empty:
                cluster_rows = named_reit_org_rows[
                    named_reit_org_rows["owner_name_raw"].eq(owner_name_raw_primary)
                ].copy()
        else:
            same_snapshot_rows = facility_owner_rows[
                facility_owner_rows["snapshot_date_ts"].eq(first_reit_snapshot)
            ].copy()
            same_snapshot_named = same_snapshot_rows[same_snapshot_rows["owner_name_raw"].ne("")].copy()
            if not same_snapshot_named.empty:
                owner_identification_method = "same_snapshot_owner_fallback"
                same_snapshot_named["entity_priority"] = same_snapshot_named["owner_name_raw"].map(
                    owner_entity_priority
                )
                same_snapshot_named = same_snapshot_named.sort_values(
                    ["entity_priority", "percentage_ownership_num", "owner_name_raw"],
                    ascending=[True, False, True],
                    na_position="last",
                )
                owner_name_raw_primary = clean_name(same_snapshot_named.iloc[0]["owner_name_raw"])
                primary_cluster_meta = classify_owner(owner_name_raw_primary)
                owner_cluster = primary_cluster_meta["owner_cluster"]
                cluster_rows = facility_owner_rows[
                    facility_owner_rows["owner_name_raw"].eq(owner_name_raw_primary)
                ].copy()
            else:
                owner_identification_method = "provider_chain_or_facility_fallback"
                owner_name_raw_primary = clean_name(facility_meta[ccn]["provider_chain_name"]) or clean_name(
                    facility_meta[ccn]["facility_name"]
                )
                primary_cluster_meta = classify_owner(owner_name_raw_primary)
                owner_cluster = primary_cluster_meta["owner_cluster"]
                cluster_rows = facility_owner_rows[
                    facility_owner_rows["owner_name_raw"].eq(owner_name_raw_primary)
                ].copy()

        owner_takeover_date = cluster_rows["association_date_ts"].dropna().min()
        if pd.isna(owner_takeover_date):
            owner_takeover_date = facility_reit_rows["association_date_ts"].dropna().min()

        reit_years = facility_meta[ccn]["reit_years"]
        run_start = facility_meta[ccn]["consecutive_run_start"]
        run_end = facility_meta[ccn]["consecutive_run_end"]
        run_length = facility_meta[ccn]["consecutive_run_length"]

        prior_snapshot_rows = facility_owner_rows[
            facility_owner_rows["snapshot_date_ts"].lt(first_reit_snapshot)
        ].copy()
        if prior_snapshot_rows.empty:
            prior_snapshot_date = pd.NaT
            prior_snapshot_owners = ""
        else:
            prior_snapshot_date = prior_snapshot_rows["snapshot_date_ts"].max()
            prior_snapshot_owners = format_pipe(
                prior_snapshot_rows.loc[
                    prior_snapshot_rows["snapshot_date_ts"].eq(prior_snapshot_date), "owner_name_raw"
                ].tolist()
            )

        buyer_events = chow_raw[chow_raw["ccn_buyer_str"].eq(ccn)].copy()
        matched_chow = pick_relevant_chow_event(buyer_events, owner_takeover_date, first_reit_snapshot)
        if matched_chow is None:
            change_in_ownership_date = ""
            prior_owner_name = ""
            prior_owner_source = ""
            matched_chow_type = ""
        else:
            change_in_ownership_date = format_date(matched_chow["effective_date"])
            prior_owner_name = clean_name(
                matched_chow.get("ORGANIZATION NAME - SELLER")
                or matched_chow.get("DOING BUSINESS AS NAME - SELLER")
            )
            prior_owner_source = "CMS SNF_CHOW seller record"
            matched_chow_type = clean_name(matched_chow.get("CHOW TYPE TEXT"))

        all_buyer_chow_dates = format_pipe(
            [format_date(x) for x in buyer_events["effective_date"].dropna().tolist()]
        )
        all_buyer_chow_sellers = format_pipe(
            (
                buyer_events["ORGANIZATION NAME - SELLER"].fillna("")
                + " / "
                + buyer_events["DOING BUSINESS AS NAME - SELLER"].fillna("")
            ).tolist()
        )

        summary_rows.append(
            {
                "ccn_str": ccn,
                "facility_name": facility_meta[ccn]["facility_name"],
                "state": facility_meta[ccn]["state"],
                "sample_role": facility_meta[ccn]["sample_role"],
                "provider_chain_name_latest": facility_meta[ccn]["provider_chain_name"],
                "owner_name_raw_primary": owner_name_raw_primary,
                "owner_aliases_raw": format_pipe(cluster_rows["owner_name_raw"].tolist()),
                "owner_identification_method": owner_identification_method,
                "owner_cluster": owner_cluster,
                "parent_owner_name": primary_cluster_meta["parent_owner_name"],
                "owner_source_type": primary_cluster_meta["source_type"],
                "owner_source_label": primary_cluster_meta["source_label"],
                "owner_source_url": primary_cluster_meta["source_url"],
                "owner_source_note": primary_cluster_meta["source_note"],
                "reit_years_in_panel": "|".join(str(y) for y in reit_years),
                "first_reit_year_in_panel": min(reit_years),
                "last_reit_year_in_panel": max(reit_years),
                "consecutive_reit_run_start": run_start,
                "consecutive_reit_run_end": run_end,
                "consecutive_reit_run_length": run_length,
                "first_reit_snapshot_date": format_date(first_reit_snapshot),
                "last_reit_snapshot_date": format_date(last_reit_snapshot),
                "owner_takeover_date_estimated": format_date(owner_takeover_date),
                "owner_takeover_date_source": "CMS SNF_All_Owners association date",
                "change_in_ownership_date_if_observed": change_in_ownership_date,
                "change_in_ownership_type": matched_chow_type,
                "prior_owner_name_if_observed": prior_owner_name,
                "prior_owner_source": prior_owner_source,
                "all_buyer_chow_dates": all_buyer_chow_dates,
                "all_buyer_chow_seller_names": all_buyer_chow_sellers,
                "pre_reit_snapshot_date": format_date(prior_snapshot_date),
                "pre_reit_snapshot_owner_entities": prior_snapshot_owners,
            }
        )
        cluster_counter[owner_cluster] += 1

    summary = pd.DataFrame(summary_rows)
    summary["cluster_size"] = summary["owner_cluster"].map(cluster_counter)
    summary = summary.sort_values(
        ["cluster_size", "owner_cluster", "state", "facility_name"],
        ascending=[False, True, True, True],
    ).reset_index(drop=True)
    summary.to_csv(SUMMARY_OUTPUT, index=False)

    cluster_rows: list[dict[str, object]] = []
    for cluster, cluster_df in summary.groupby("owner_cluster", dropna=False):
        first = cluster_df.iloc[0]
        cluster_rows.append(
            {
                "owner_cluster": cluster,
                "parent_owner_name": first["parent_owner_name"],
                "cluster_size": int(len(cluster_df)),
                "owner_source_type": first["owner_source_type"],
                "owner_source_label": first["owner_source_label"],
                "owner_source_url": first["owner_source_url"],
                "owner_source_note": first["owner_source_note"],
                "example_owner_name_raw_primary": first["owner_name_raw_primary"],
                "example_facility_name": first["facility_name"],
                "states": format_pipe(sorted(cluster_df["state"].dropna().unique().tolist())),
            }
        )
    cluster_df = pd.DataFrame(cluster_rows).sort_values(
        ["cluster_size", "owner_cluster"], ascending=[False, True]
    )
    cluster_df.to_csv(CLUSTER_OUTPUT, index=False)

    notes = f"""# REIT ownership investigation outputs

This folder was generated by `scripts/build_reit_ownership_investigation.py`.

Files:

- `reit_consecutive_homes_panel_raw.csv`: all panel rows for the 175 national-panel
  facilities that have at least one consecutive-year REIT run.
- `reit_consecutive_homes_owner_history_raw.csv`: all raw CMS owner-history rows for
  those 175 facilities, with owner-cluster labels added.
- `reit_consecutive_homes_chow_raw.csv`: raw CMS CHOW events where the facility
  appears as buyer or seller.
- `reit_consecutive_homes_investigated.csv`: facility-level summary with owner,
  REIT years, estimated takeover date, any nearby CHOW date, and prior owner if
  observed.
- `reit_owner_clusters.csv`: cluster-level lookup with official source links for
  major REIT parents.

Method notes:

- The cohort is defined from the national panel
  `data/intermediate/analysis/panels/regression_analysis_panel_gold_v2.csv`.
- REIT years use the formal `any_reit_owner` flag from the panel, not name-based
  heuristics.
- `owner_takeover_date_estimated` comes from the earliest observed
  `ASSOCIATION DATE - OWNER` among REIT-tagged owner rows in the CMS raw owner
  file for the facility's dominant REIT cluster.
- `change_in_ownership_date_if_observed` and `prior_owner_name_if_observed` come
  from the nearest buyer-side CMS CHOW event when one can be matched. Blank
  fields mean no nearby CHOW buyer event was observed in the local CMS CHOW data.
- Smaller one-off entities remain labeled directly from the CMS owner name when
  I did not attach an additional official web source in this pass.
"""
    NOTES_OUTPUT.write_text(notes)

    manifest = {
        "cohort_facilities": int(len(cohort_list)),
        "raw_panel_rows": int(len(panel_raw)),
        "raw_owner_rows": int(len(owner_raw)),
        "raw_chow_rows": int(len(chow_raw)),
        "summary_rows": int(len(summary)),
        "cluster_count": int(len(cluster_df)),
        "outputs": {
            "raw_panel": str(RAW_PANEL_OUTPUT.relative_to(ROOT)),
            "raw_owner": str(RAW_OWNER_OUTPUT.relative_to(ROOT)),
            "raw_chow": str(RAW_CHOW_OUTPUT.relative_to(ROOT)),
            "summary": str(SUMMARY_OUTPUT.relative_to(ROOT)),
            "clusters": str(CLUSTER_OUTPUT.relative_to(ROOT)),
        },
    }
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
