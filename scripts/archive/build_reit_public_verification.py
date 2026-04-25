#!/usr/bin/env python3
"""Add source-backed public verification to the REIT ownership investigation.

This script reads the facility-level CMS-derived summary produced by
`build_reit_ownership_investigation.py` and layers on:

- public/official REIT or operator verification where available
- a more explicit best takeover date and source
- prior-owner candidate fields derived from the immediate pre-REIT snapshot
- ownership-change signal labels that distinguish CHOW-confirmed transitions
  from weaker snapshot-only evidence
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = ROOT / "research" / "reit_ownership_investigation"
BASE_SUMMARY = BASE_DIR / "reit_consecutive_homes_investigated.csv"

OUTPUT_FACILITY = BASE_DIR / "reit_consecutive_homes_verified_public.csv"
OUTPUT_CLUSTER = BASE_DIR / "reit_owner_cluster_public_verification.csv"


@dataclass(frozen=True)
class VerificationRule:
    pattern: re.Pattern[str]
    public_parent_name: str
    public_entity_type: str
    public_reit_status: str
    source_label: str
    source_url: str
    source_note: str
    confidence: str


TITLE_WORDS = {
    "CEO",
    "CFO",
    "COO",
    "PRESIDENT",
    "VICE PRESIDENT",
    "VP",
    "ADMINISTRATOR",
    "DIRECTOR",
    "BOARD MEMBER",
    "BOARD TRUSTEE",
    "CHAIR",
    "CHAIRMAN",
    "CHAIRPERSON",
    "SECRETARY",
    "TREASURER",
    "MEMBER",
    "EXECUTIVE DIRECTOR",
    "CHIEF EXECUTIVE OFFICER",
    "CHIEF FINANCIAL OFFICER",
    "CHIEF OPERATING OFFICER",
}

ORG_HINT = re.compile(
    r"\b("
    r"LLC|L\.L\.C\.|LP|L\.P\.|INC|INC\.|CORP|CORPORATION|HOSPITAL|"
    r"TRUST(?!EE)|REIT|LTD|LIMITED|COMPANY|ASSOCIATES|PROPERTIES|VENTURES|"
    r"PARTNERS|CENTER|CAMPUS|CARE|HEALTH|HEALTHCARE|NURSING|HOLDINGS|"
    r"HOLDCO|PROPERTY|COMMUNITIES|OPERATIONS|OPCO|REALTY|VILLAGE|FACILITY"
    r")\b",
    re.I,
)

RULES: list[VerificationRule] = [
    VerificationRule(
        pattern=re.compile(r"American Healthcare REIT / Trilogy", re.I),
        public_parent_name="American Healthcare REIT, Inc.",
        public_entity_type="public_healthcare_reit",
        public_reit_status="yes",
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
        confidence="high",
    ),
    VerificationRule(
        pattern=re.compile(r"Omega Healthcare Investors", re.I),
        public_parent_name="Omega Healthcare Investors, Inc.",
        public_entity_type="public_healthcare_reit",
        public_reit_status="yes",
        source_label="Omega Healthcare Investors official site",
        source_url="https://www.omegahealthcare.com/about-us",
        source_note=(
            "Omega describes itself as a REIT focused primarily on skilled "
            "nursing and assisted living facilities."
        ),
        confidence="high",
    ),
    VerificationRule(
        pattern=re.compile(r"National Health Investors", re.I),
        public_parent_name="National Health Investors, Inc.",
        public_entity_type="public_healthcare_reit",
        public_reit_status="yes",
        source_label="National Health Investors investor relations",
        source_url="https://investors.nhireit.com/",
        source_note=(
            "NHI says it is a REIT specializing in senior housing, skilled "
            "nursing facilities, and medical investments."
        ),
        confidence="high",
    ),
    VerificationRule(
        pattern=re.compile(r"Welltower", re.I),
        public_parent_name="Welltower Inc.",
        public_entity_type="public_healthcare_reit",
        public_reit_status="yes",
        source_label="Welltower product overview",
        source_url="https://welltower.com/product-overview/",
        source_note=(
            "Welltower describes post-acute care as part of its healthcare real "
            "estate platform."
        ),
        confidence="high",
    ),
    VerificationRule(
        pattern=re.compile(r"Healthpeak Properties", re.I),
        public_parent_name="Healthpeak Properties, Inc.",
        public_entity_type="public_healthcare_reit",
        public_reit_status="yes",
        source_label="Healthpeak official site",
        source_url="https://healthpeak.com/about/",
        source_note=(
            "Healthpeak says it is a healthcare REIT with a senior housing "
            "portfolio."
        ),
        confidence="high",
    ),
    VerificationRule(
        pattern=re.compile(r"Sabra Health Care REIT", re.I),
        public_parent_name="Sabra Health Care REIT, Inc.",
        public_entity_type="public_healthcare_reit",
        public_reit_status="yes",
        source_label="Sabra investor overview",
        source_url="https://ir.sabrahealth.com/investors/overview/",
        source_note=(
            "Sabra says it owns and invests in healthcare real estate, including "
            "skilled nursing facilities."
        ),
        confidence="high",
    ),
    VerificationRule(
        pattern=re.compile(r"CareTrust REIT", re.I),
        public_parent_name="CareTrust REIT, Inc.",
        public_entity_type="public_healthcare_reit",
        public_reit_status="yes",
        source_label="CareTrust official site",
        source_url="https://www.caretrustreit.com/what-we-do",
        source_note=(
            "CareTrust says it acquires and leases skilled nursing and senior "
            "housing properties."
        ),
        confidence="high",
    ),
    VerificationRule(
        pattern=re.compile(r"^NHC-OP LP$", re.I),
        public_parent_name="National HealthCare Corporation",
        public_entity_type="operator_company",
        public_reit_status="no",
        source_label="National HealthCare Corporation annual report",
        source_url="https://nhccare.com/wp-content/uploads/2025/07/Annual-Report-for-Website.pdf",
        source_note=(
            "NHC's annual report describes the company as an operator of "
            "skilled nursing and senior health care facilities."
        ),
        confidence="medium",
    ),
    VerificationRule(
        pattern=re.compile(r"^(FOCUSED POST ACUTE CARE PARTNERS LLC|FPACP )", re.I),
        public_parent_name="Focused Post Acute Care Partners",
        public_entity_type="operator_company",
        public_reit_status="no",
        source_label="Focused Post Acute Care Partners official site",
        source_url=(
            "https://fpacp.com/"
            "focused-post-acute-care-partners-acquisitions-launch-unique-business-"
            "model-bringing-improved-long-term-care-to-outlying-secondary-and-"
            "tertiary-markets/"
        ),
        source_note=(
            "Focused said it acquired operations of skilled nursing facilities in "
            "Texas, which supports an operator rather than REIT role."
        ),
        confidence="medium",
    ),
    VerificationRule(
        pattern=re.compile(r"^ARI OPERATIONS, LLC$", re.I),
        public_parent_name="Avamere",
        public_entity_type="operator_company",
        public_reit_status="no",
        source_label="Avamere official site",
        source_url="https://www.avamere.com/about/",
        source_note=(
            "Avamere describes itself as a post-acute and senior living care "
            "operator; mapping to ARI Operations comes from the local CMS owner "
            "records and Avamere-branded facilities."
        ),
        confidence="medium",
    ),
    VerificationRule(
        pattern=re.compile(r"^(SENIOR LIVING COMMUITIES LLC|WELLMORE LLC)$", re.I),
        public_parent_name="Senior Living Communities, LLC",
        public_entity_type="operator_company",
        public_reit_status="no",
        source_label="Senior Living Communities official FAQs",
        source_url="https://senior-living-communities.com/about/faqs/",
        source_note=(
            "Senior Living Communities describes itself as a company that owns "
            "and operates senior living communities."
        ),
        confidence="medium",
    ),
    VerificationRule(
        pattern=re.compile(r"^JACKSON COUNTY SCHNECK MEMORIAL HOSPITAL$", re.I),
        public_parent_name="Schneck Medical Center",
        public_entity_type="hospital_system",
        public_reit_status="no",
        source_label="Schneck official site",
        source_url="https://www.schneckmed.org/about-us",
        source_note="Schneck is a regional hospital and health system.",
        confidence="high",
    ),
    VerificationRule(
        pattern=re.compile(r"^WACHUSETT VENTURES LLC$", re.I),
        public_parent_name="Wachusett Ventures, LLC",
        public_entity_type="operator_company",
        public_reit_status="no",
        source_label="New England Healthcare Systems leadership page",
        source_url="https://nehs.care/steven-vera/",
        source_note=(
            "The Wachusett Ventures leadership bio describes day-to-day "
            "operational management of skilled nursing facilities."
        ),
        confidence="medium",
    ),
    VerificationRule(
        pattern=re.compile(r"^GTM US SENIOR HOUSING REIT, LP$", re.I),
        public_parent_name="GTM US Sr Housing REIT Inc. / GTM US Senior Housing REIT, LP",
        public_entity_type="private_reit_entity",
        public_reit_status="yes",
        source_label="Florida Division of Corporations",
        source_url=(
            "https://search.sunbiz.org/Inquiry/CorporationSearch/"
            "SearchResultDetail?aggregateId=forlp-b15000000312-e955e064-ae75-"
            "4f66-b2c5-ebeb044fe4b2&directionType=Initial&"
            "inquirytype=OfficerRegisteredAgentName&"
            "listNameOrder=GTMINVESTORSLLC+L170001372771&"
            "searchNameOrder=GTMUSSRHOUSINGREITINC+B150000003122&"
            "searchTerm=Gtm+Investors+Llc"
        ),
        source_note=(
            "Florida's entity record shows GTM US Senior Housing REIT, LP and "
            "its REIT-labeled general partner."
        ),
        confidence="medium",
    ),
    VerificationRule(
        pattern=re.compile(
            r"^(WO HOLDINGS LLC|OMG RE HOLDINGS LLC|HEALTH CARE HOLDINGS, LLC|"
            r"OHIO PENNSYSLVANIA PROPERTY LLC|OHL ASSET \(VA\) MECHANICSVILLE, LLC)$",
            re.I,
        ),
        public_parent_name="Omega Healthcare Investors-affiliated entity",
        public_entity_type="private_reit_affiliate",
        public_reit_status="yes_affiliate",
        source_label="Omega SEC filings / Maryland exemption request",
        source_url=(
            "https://mhcc.maryland.gov/mhcc/pages/hcfs/hcfs_con/documents/"
            "2023_exemption/communicare/con_communicare_ex015_exemption_request_20230414.pdf"
        ),
        source_note=(
            "State and SEC documents tie these entities to Omega or to Omega's "
            "subsidiary/affiliate structure."
        ),
        confidence="medium",
    ),
]


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def split_pipe(value: str) -> list[str]:
    return [clean(part) for part in str(value).split("|") if clean(part)]


def likely_org_entity(value: str) -> bool:
    text = clean(value)
    if not text:
        return False
    if any(title in text.upper() for title in TITLE_WORDS):
        if not ORG_HINT.search(text):
            return False
    return bool(ORG_HINT.search(text))


def org_entities_from_pipe(value: str) -> list[str]:
    return [item for item in split_pipe(value) if likely_org_entity(item)]


def verify_cluster(cluster: str) -> dict[str, str]:
    cluster = clean(cluster)
    for rule in RULES:
        if rule.pattern.search(cluster):
            return {
                "public_parent_name": rule.public_parent_name,
                "public_entity_type": rule.public_entity_type,
                "public_reit_status": rule.public_reit_status,
                "public_source_label": rule.source_label,
                "public_source_url": rule.source_url,
                "public_source_note": rule.source_note,
                "verification_confidence": rule.confidence,
            }

    upper = cluster.upper()
    if "TRUST" in upper or " IRRV TR" in upper or " FAM TR " in upper:
        return {
            "public_parent_name": cluster,
            "public_entity_type": "private_trust_or_individual_vehicle",
            "public_reit_status": "no",
            "public_source_label": "CMS owner entity name",
            "public_source_url": "",
            "public_source_note": "Owner entity is a private trust rather than a REIT.",
            "verification_confidence": "low",
        }
    if "HOSPITAL" in upper:
        return {
            "public_parent_name": cluster,
            "public_entity_type": "hospital_system",
            "public_reit_status": "no",
            "public_source_label": "CMS owner entity name",
            "public_source_url": "",
            "public_source_note": "Owner entity is a hospital or hospital-related organization.",
            "verification_confidence": "low",
        }
    if any(token in upper for token in ["SECRETARY", "TREASURER", "MEMBER", "MANAGING MEMBER", "COO"]):
        return {
            "public_parent_name": cluster,
            "public_entity_type": "individual_or_officer_record",
            "public_reit_status": "no",
            "public_source_label": "CMS owner entity name",
            "public_source_url": "",
            "public_source_note": (
                "CMS appears to record an individual or officer-title row rather "
                "than a clean corporate owner entity."
            ),
            "verification_confidence": "low",
        }
    if "REIT" in upper:
        return {
            "public_parent_name": cluster,
            "public_entity_type": "private_reit_entity",
            "public_reit_status": "yes_name_based",
            "public_source_label": "CMS owner entity name",
            "public_source_url": "",
            "public_source_note": (
                "The entity name itself contains REIT, but I did not attach a "
                "separate public company page in this pass."
            ),
            "verification_confidence": "low",
        }
    if any(token in upper for token in ["LLC", "LP", "L.P.", "INC", "CORPORATION", "ASSOCIATES", "PROPERTIES"]):
        return {
            "public_parent_name": cluster,
            "public_entity_type": "private_real_estate_or_operating_entity",
            "public_reit_status": "unclear",
            "public_source_label": "CMS owner entity name",
            "public_source_url": "",
            "public_source_note": (
                "Private entity visible in CMS ownership data, but I did not find "
                "enough public evidence in this pass to classify it confidently as "
                "REIT or non-REIT."
            ),
            "verification_confidence": "low",
        }
    return {
        "public_parent_name": cluster,
        "public_entity_type": "unclear_entity_type",
        "public_reit_status": "unclear",
        "public_source_label": "CMS owner entity name",
        "public_source_url": "",
        "public_source_note": "No stronger public classification attached in this pass.",
        "verification_confidence": "low",
    }


def build_prior_owner_candidates(row: pd.Series) -> str:
    current = set(org_entities_from_pipe(row.get("owner_aliases_raw", "")))
    current_primary = clean(row.get("owner_name_raw_primary"))
    if likely_org_entity(current_primary):
        current.add(current_primary)
    prior = [item for item in org_entities_from_pipe(row.get("pre_reit_snapshot_owner_entities", "")) if item not in current]
    # Preserve order while deduplicating.
    deduped = list(dict.fromkeys(prior))
    return "|".join(deduped)


def current_owner_visible_pre_reit(row: pd.Series) -> bool:
    current = set(org_entities_from_pipe(row.get("owner_aliases_raw", "")))
    current_primary = clean(row.get("owner_name_raw_primary"))
    if likely_org_entity(current_primary):
        current.add(current_primary)
    prior = set(org_entities_from_pipe(row.get("pre_reit_snapshot_owner_entities", "")))
    return bool(current & prior)


def best_takeover_date(row: pd.Series) -> tuple[str, str]:
    chow_date = clean(row.get("change_in_ownership_date_if_observed"))
    assoc_date = clean(row.get("owner_takeover_date_estimated"))
    if chow_date:
        return chow_date, "CMS CHOW event"
    return assoc_date, "CMS owner association date"


def ownership_signal(row: pd.Series) -> str:
    if clean(row.get("change_in_ownership_date_if_observed")):
        return "chow_confirmed"
    if clean(row.get("prior_owner_candidates_pre_reit_snapshot")):
        if row.get("current_owner_visible_in_pre_reit_snapshot") == "True":
            return "same_owner_already_visible_pre_reit"
        return "different_named_entities_in_pre_reit_snapshot"
    if row.get("current_owner_visible_in_pre_reit_snapshot") == "True":
        return "same_owner_already_visible_pre_reit"
    return "no_prior_snapshot_org_entity_available"


def main() -> None:
    df = pd.read_csv(BASE_SUMMARY, dtype="string").fillna("")
    verification = df["owner_cluster"].map(verify_cluster).apply(pd.Series)
    verified = pd.concat([df, verification], axis=1)

    verified["prior_owner_candidates_pre_reit_snapshot"] = verified.apply(
        build_prior_owner_candidates, axis=1
    )
    verified["current_owner_visible_in_pre_reit_snapshot"] = verified.apply(
        current_owner_visible_pre_reit, axis=1
    ).map({True: "True", False: "False"})
    takeover = verified.apply(best_takeover_date, axis=1)
    verified["takeover_date_best"] = takeover.map(lambda x: x[0])
    verified["takeover_date_best_source"] = takeover.map(lambda x: x[1])
    verified["ownership_change_signal"] = verified.apply(ownership_signal, axis=1)

    cols_front = [
        "ccn_str",
        "facility_name",
        "state",
        "sample_role",
        "provider_chain_name_latest",
        "owner_name_raw_primary",
        "owner_identification_method",
        "owner_cluster",
        "public_parent_name",
        "public_entity_type",
        "public_reit_status",
        "public_source_label",
        "public_source_url",
        "public_source_note",
        "verification_confidence",
        "reit_years_in_panel",
        "takeover_date_best",
        "takeover_date_best_source",
        "owner_takeover_date_estimated",
        "change_in_ownership_date_if_observed",
        "prior_owner_name_if_observed",
        "prior_owner_candidates_pre_reit_snapshot",
        "current_owner_visible_in_pre_reit_snapshot",
        "ownership_change_signal",
    ]
    remaining = [c for c in verified.columns if c not in cols_front]
    verified = verified[cols_front + remaining].sort_values(
        ["public_reit_status", "owner_cluster", "state", "facility_name"]
    )
    verified.to_csv(OUTPUT_FACILITY, index=False)

    cluster_df = (
        verified.groupby("owner_cluster", dropna=False)
        .agg(
            cluster_size=("ccn_str", "size"),
            public_parent_name=("public_parent_name", "first"),
            public_entity_type=("public_entity_type", "first"),
            public_reit_status=("public_reit_status", "first"),
            public_source_label=("public_source_label", "first"),
            public_source_url=("public_source_url", "first"),
            public_source_note=("public_source_note", "first"),
            verification_confidence=("verification_confidence", "first"),
            example_owner_name_raw_primary=("owner_name_raw_primary", "first"),
            example_facility_name=("facility_name", "first"),
            states=("state", lambda s: "|".join(dict.fromkeys([clean(x) for x in s if clean(x)]))),
        )
        .reset_index()
        .sort_values(["cluster_size", "owner_cluster"], ascending=[False, True])
    )
    cluster_df.to_csv(OUTPUT_CLUSTER, index=False)

    print(
        json.dumps(
            {
                "facility_rows": int(len(verified)),
                "cluster_rows": int(len(cluster_df)),
                "public_reit_status_counts": {
                    k: int(v) for k, v in verified["public_reit_status"].value_counts().to_dict().items()
                },
                "outputs": {
                    "facility_verified": str(OUTPUT_FACILITY.relative_to(ROOT)),
                    "cluster_verified": str(OUTPUT_CLUSTER.relative_to(ROOT)),
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
