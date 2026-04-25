#!/usr/bin/env python3
"""Build the integrated PE treatment research dataset.

This script is the canonical treatment-data builder. It preserves the existing
gold sample, applies the current gold/silver/exclude taxonomy, appends the
curated silver additions, and rewrites the treatment-side research artifacts.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "research"
TREATMENT_INPUTS = RESEARCH / "treatment_inputs"
FACILITY_CSV = TREATMENT_INPUTS / "pe_facility_verification.csv"
DEAL_CSV = TREATMENT_INPUTS / "pe_acquisition_deals.csv"
NOTES_MD = RESEARCH / "verification" / "ownership_transition_verification_notes.md"
SUMMARY_CSV = TREATMENT_INPUTS / "pe_analysis_sample_summary.csv"
QA_JSON = TREATMENT_INPUTS / "pe_analysis_sample_qa.json"


FACILITY_SORT_ORDER = [
    "PE001",
    "PE002",
    "PE007",
    "PE008",
    "PE013",
    "PE014",
    "PE015",
    "PE016",
    "PE017",
]

FACILITY_ORDER_INDEX = {deal_id: idx for idx, deal_id in enumerate(FACILITY_SORT_ORDER)}


def extract_year(value: str) -> int | None:
    if value is None or pd.isna(value):
        return None
    match = re.search(r"(20\d{2})", str(value))
    return int(match.group(1)) if match else None


def first_sentence(text: str) -> str:
    if not text or pd.isna(text):
        return ""
    raw = str(text).strip()
    sentence = re.split(r"(?<=[.!?])\s+", raw, maxsplit=1)[0].strip()
    return sentence if sentence else raw


def normalize_existing_rows(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in [
        "analysis_sample",
        "evidence_pathway",
        "current_pe_evidence",
        "pre_period_certainty",
    ]:
        if col not in df.columns:
            df[col] = ""

    # Default every existing gold/verified row into the gold main sample.
    verified_mask = (
        df["transition_verified"].fillna("").str.lower().eq("yes")
        & df["transition_type"].fillna("").str.lower().eq("non_pe_to_pe")
    )
    df.loc[verified_mask, "analysis_sample"] = "gold_main"
    df.loc[verified_mask, "evidence_pathway"] = "facility_public_current_plus_prehistory"
    df.loc[verified_mask, "pre_period_certainty"] = "clear_non_pe"
    df.loc[verified_mask, "current_pe_evidence"] = "facility_cms_direct"

    # Deal-level refinements for verified rows.
    df.loc[df["deal_id"].eq("PE008") & verified_mask, "current_pe_evidence"] = (
        "facility_cms_managerial"
    )
    df.loc[
        (df["deal_id"].eq("PE015")) & df["facility_name"].eq("Pioneer House"),
        "current_pe_evidence",
    ] = "secondary_cms_derived"

    # Explicit silver/exclude overrides for the current non-gold rows.
    overrides = {
        ("PE001", "345179"): ("silver_unclear", "chain_deal_plus_facility_match", "facility_cms_direct", "likely_pe_or_financialized"),
        ("PE001", "345162"): ("silver_unclear", "chain_deal_plus_facility_match", "facility_cms_direct", "unknown"),
        ("PE001", "345243"): ("silver_unclear", "chain_deal_plus_facility_match", "facility_cms_direct", "likely_pe_or_financialized"),
        ("PE001", "345081"): ("silver_main", "chain_deal_plus_facility_match", "facility_cms_direct", "likely_non_pe"),
        ("PE001", "105332"): ("silver_unclear", "chain_deal_plus_facility_match", "facility_cms_direct", "likely_pe_or_financialized"),
        ("PE002", "676222"): ("silver_main", "chain_deal_plus_facility_match", "facility_cms_managerial", "likely_non_pe"),
        ("PE002", "675799"): ("exclude", "chain_deal_plus_facility_match", "facility_cms_managerial", "likely_non_pe"),
        ("PE002", "455599"): ("silver_main", "chain_deal_plus_facility_match", "facility_cms_managerial", "likely_non_pe"),
        ("PE002", "676258"): ("silver_main", "chain_deal_plus_facility_match", "facility_cms_managerial", "likely_non_pe"),
        ("PE002", "675395"): ("silver_main", "chain_deal_plus_facility_match", "facility_cms_managerial", "likely_non_pe"),
        ("PE008", "165361"): ("silver_main", "chain_deal_plus_facility_match", "facility_cms_managerial", "clear_non_pe"),
        ("PE008", "165347"): ("silver_main", "chain_deal_plus_facility_match", "facility_cms_managerial", "clear_non_pe"),
        ("PE008", "165367"): ("silver_main", "chain_deal_plus_facility_match", "facility_cms_managerial", "clear_non_pe"),
        ("PE013", "106061"): ("silver_unclear", "chain_deal_plus_facility_match", "facility_cms_direct", "likely_pe_or_financialized"),
        ("PE014", "555153"): ("silver_unclear", "chain_deal_plus_facility_match", "facility_cms_direct", "clear_non_pe"),
        ("PE014", "555098"): ("silver_unclear", "chain_deal_plus_facility_match", "facility_cms_direct", "clear_non_pe"),
        ("PE014", "555083"): ("silver_unclear", "chain_deal_plus_facility_match", "facility_cms_direct", "clear_non_pe"),
    }

    for (deal_id, ccn), values in overrides.items():
        mask = df["deal_id"].eq(deal_id) & df["ccn"].eq(ccn)
        if not mask.any():
            raise ValueError(f"Expected existing row missing for {(deal_id, ccn)}")
        df.loc[mask, ["analysis_sample", "evidence_pathway", "current_pe_evidence", "pre_period_certainty"]] = values

    if "verification_tier" in df.columns:
        df.loc[df["analysis_sample"].eq("gold_main"), "verification_tier"] = "gold"
        df.loc[df["analysis_sample"].ne("gold_main"), "verification_tier"] = "silver"

    return df


def new_rows() -> list[dict[str, str]]:
    platform_link = "https://iowacapitaldispatch.com/2024/10/21/private-equity-firm-buys-29-iowa-nursing-homes-in-massive-85-million-deal/"
    rows = [
        {
            "deal_id": "PE008",
            "pe_firm": "Cascade Capital Group",
            "platform_name": "Legacy Healthcare",
            "facility_name": "Bloomfield Care Center",
            "ccn": "165326",
            "state": "IA",
            "city": "Bloomfield",
            "address": "800 North Davis Street, Bloomfield, IA 52537",
            "source_platform_link": platform_link,
            "source_facility_link": "https://projects.propublica.org/nursing-homes/homes/h-165326",
            "cms_owner_name": "Iowa Portfolio Opco Holdings LLC (100%)",
            "cms_affiliated_entity": "Affiliated With Legacy Healthcare",
            "ownership_effective_date": "Aug 2024",
            "cms_change_of_ownership_flag": "yes",
            "pre_owner_name": "ABCM Corporation",
            "pre_owner_effective_end": "before Aug 2024",
            "pre_owner_pe_status": "non_pe",
            "pre_operator_name": "ABCM Corporation",
            "post_operator_name": "Legacy Healthcare Financial Services LLC",
            "post_owner_pe_status": "pe",
            "transition_basis": "owner_and_operator_change",
            "transition_type": "likely_non_pe_to_pe",
            "transition_verified": "no",
            "match_quality": "exact",
            "verification_tier": "silver",
            "verification_notes": (
                "Current ProPublica ownership shows Iowa Portfolio Opco Holdings LLC as the direct owner and Legacy "
                "Healthcare Financial Services LLC in managerial control since Aug 2024. The 2019 HealthcareComps "
                "page identifies Bloomfield Care Center under ABCM Corporation at the same address and CCN. This is "
                "a strong ABCM-to-Cascade/Legacy transition, but it enters the repo through the silver deal-first build "
                "rather than the original gold facility-verification pass."
            ),
            "analysis_sample": "silver_main",
            "evidence_pathway": "chain_deal_plus_facility_match",
            "current_pe_evidence": "facility_cms_direct",
            "pre_period_certainty": "clear_non_pe",
        },
        {
            "deal_id": "PE008",
            "pe_firm": "Cascade Capital Group",
            "platform_name": "Legacy Healthcare",
            "facility_name": "Rehabilitation Center Of Belmond",
            "ccn": "165380",
            "state": "IA",
            "city": "Belmond",
            "address": "1107 Seventh Street Ne, Belmond, IA 50421",
            "source_platform_link": platform_link,
            "source_facility_link": "https://projects.propublica.org/nursing-homes/homes/h-165380",
            "cms_owner_name": "Iowa Portfolio Opco Holdings Llc (100%)",
            "cms_affiliated_entity": "Affiliated With Legacy Healthcare",
            "ownership_effective_date": "Aug 2024",
            "cms_change_of_ownership_flag": "yes",
            "pre_owner_name": "ABCM Corporation",
            "pre_owner_effective_end": "before Aug 2024",
            "pre_owner_pe_status": "non_pe",
            "pre_operator_name": "ABCM Corporation",
            "post_operator_name": "Legacy Healthcare Financial Services Llc",
            "post_owner_pe_status": "pe",
            "transition_basis": "owner_and_operator_change",
            "transition_type": "likely_non_pe_to_pe",
            "transition_verified": "no",
            "match_quality": "exact",
            "verification_tier": "silver",
            "verification_notes": (
                "Current ProPublica ownership shows Iowa Portfolio Opco Holdings Llc as the direct owner and Legacy "
                "Healthcare Financial Services Llc in managerial control since Aug 2024. The 2019 HealthcareComps page "
                "identifies Rehabilitation Center of Belmond under ABCM Corporation at the same address and CCN. This "
                "is a strong ABCM-to-Cascade/Legacy transition, but it is being added through the silver expansion workflow."
            ),
            "analysis_sample": "silver_main",
            "evidence_pathway": "chain_deal_plus_facility_match",
            "current_pe_evidence": "facility_cms_direct",
            "pre_period_certainty": "clear_non_pe",
        },
        {
            "deal_id": "PE008",
            "pe_firm": "Cascade Capital Group",
            "platform_name": "Legacy Healthcare",
            "facility_name": "Emmetsburg Care Center",
            "ccn": "165352",
            "state": "IA",
            "city": "Emmetsburg",
            "address": "2405 21st Street, Emmetsburg, IA 50536",
            "source_platform_link": platform_link,
            "source_facility_link": "https://projects.propublica.org/nursing-homes/homes/h-165352",
            "cms_owner_name": "Iowa Portfolio Opco Holdings Llc (100%)",
            "cms_affiliated_entity": "Affiliated With Legacy Healthcare",
            "ownership_effective_date": "Aug 2024",
            "cms_change_of_ownership_flag": "yes",
            "pre_owner_name": "ABCM Corporation",
            "pre_owner_effective_end": "before Aug 2024",
            "pre_owner_pe_status": "non_pe",
            "pre_operator_name": "ABCM Corporation",
            "post_operator_name": "Legacy Healthcare Financial Services Llc",
            "post_owner_pe_status": "pe",
            "transition_basis": "owner_and_operator_change",
            "transition_type": "likely_non_pe_to_pe",
            "transition_verified": "no",
            "match_quality": "exact",
            "verification_tier": "silver",
            "verification_notes": (
                "Current ProPublica ownership shows Iowa Portfolio Opco Holdings Llc as the direct owner and Legacy "
                "Healthcare Financial Services Llc in managerial control since Aug 2024. The 2019 HealthcareComps page "
                "identifies Emmetsburg Care Center under ABCM Corporation at the same address and CCN. This is a strong "
                "ABCM-to-Cascade/Legacy transition added through the silver expansion workflow."
            ),
            "analysis_sample": "silver_main",
            "evidence_pathway": "chain_deal_plus_facility_match",
            "current_pe_evidence": "facility_cms_direct",
            "pre_period_certainty": "clear_non_pe",
        },
        {
            "deal_id": "PE007",
            "pe_firm": "Tryko Partners",
            "platform_name": "Marquis Health Services",
            "facility_name": "Collingswood Rehabilitation And Healthcare Center",
            "ccn": "215092",
            "state": "MD",
            "city": "Rockville",
            "address": "299 Hurley Avenue, Rockville, MD 20850",
            "source_platform_link": "https://skillednursingnews.com/2019/02/dwight-capitals-13m-bridge-loan-in-ohio-marquis-tryko-expand-in-maryland/",
            "source_facility_link": "https://projects.propublica.org/nursing-homes/homes/h-215092",
            "cms_owner_name": "Quinto Holdings LLC (89%); Ukr Consulting LLC (10%)",
            "cms_affiliated_entity": "Affiliated With Marquis Health Services",
            "ownership_effective_date": "Feb 2019",
            "cms_change_of_ownership_flag": "yes",
            "pre_owner_name": "Collingswood Nursing Facilities Inc.",
            "pre_owner_effective_end": "before Feb 2019",
            "pre_owner_pe_status": "unknown",
            "pre_operator_name": "Collingswood Nsg. & Rehab. Cen.",
            "post_operator_name": "Marquis Limited LLC / Reliant Pro Rehab LLC",
            "post_owner_pe_status": "pe",
            "transition_basis": "owner_and_operator_change",
            "transition_type": "likely_non_pe_to_pe",
            "transition_verified": "no",
            "match_quality": "exact",
            "verification_tier": "silver",
            "verification_notes": (
                "Public deal coverage identifies Tryko Partners as the buyer behind Marquis Health Services' "
                "Rockville expansion, naming Collingswood Rehabilitation & Healthcare Center in February 2019. "
                "The current ProPublica page for the same CCN and address shows Tryko-linked ownership and Marquis "
                "managerial control, while the 2019 HealthcareComps page still lists Collingswood Nursing "
                "Facilities Inc. at the same facility. This is a strong silver_main row even though the historical "
                "pre-period ownership record is a local for-profit corporation rather than a nonprofit seller."
            ),
            "analysis_sample": "silver_main",
            "evidence_pathway": "chain_deal_plus_facility_match",
            "current_pe_evidence": "facility_cms_direct",
            "pre_period_certainty": "likely_non_pe",
        },
        {
            "deal_id": "PE007",
            "pe_firm": "Tryko Partners",
            "platform_name": "Marquis Health Services",
            "facility_name": "Woodbine Rehabilitation & Healthcare Center",
            "ccn": "495019",
            "state": "VA",
            "city": "Alexandria",
            "address": "2729 King Street, Alexandria, VA 22302",
            "source_platform_link": "https://www.roi-nj.com/2020/02/25/healthcare/tryko-partners-grows-in-mid-atlantic-with-acquisition-of-3-skilled-nursing-facilities/",
            "source_facility_link": "https://projects.propublica.org/nursing-homes/homes/h-495019",
            "cms_owner_name": "Quinto Delta LLC (89%); Ukr Consulting LLC (10%); Skilled Venture LLC",
            "cms_affiliated_entity": "Affiliated With Marquis Health Services",
            "ownership_effective_date": "Feb 2020",
            "cms_change_of_ownership_flag": "yes",
            "pre_owner_name": "Cambridge Healthcare Holdings LLC / Woodbine Convalescent & Nursing Care LLC",
            "pre_owner_effective_end": "before Feb 2020",
            "pre_owner_pe_status": "unknown",
            "pre_operator_name": "Cambridge Healthcare portfolio",
            "post_operator_name": "Marquis Limited LLC / Reliant Pro Rehab LLC",
            "post_owner_pe_status": "pe",
            "transition_basis": "owner_and_operator_change",
            "transition_type": "likely_non_pe_to_pe",
            "transition_verified": "no",
            "match_quality": "exact",
            "verification_tier": "silver",
            "verification_notes": (
                "Trade press identifies Tryko Partners as the private equity buyer of three Virginia skilled nursing "
                "facilities from the Cambridge Healthcare portfolio in February 2020, with Marquis Health Services "
                "as operator. The current ProPublica ownership page for the same CCN and address shows Tryko-linked "
                "Quinto Delta / Ukr Consulting ownership and Marquis managerial control, while the 2019 "
                "HealthcareComps page lists Cambridge Healthcare Holdings LLC in the ownership structure. This is a "
                "strong silver_main row, but it stays below gold because the pre-period side is a for-profit chain "
                "rather than a fully verified nonprofit/local seller."
            ),
            "analysis_sample": "silver_main",
            "evidence_pathway": "chain_deal_plus_facility_match",
            "current_pe_evidence": "facility_cms_direct",
            "pre_period_certainty": "likely_non_pe",
        },
        {
            "deal_id": "PE007",
            "pe_firm": "Tryko Partners",
            "platform_name": "Marquis Health Services",
            "facility_name": "Canterbury Rehabilitation And Healthcare Center",
            "ccn": "495272",
            "state": "VA",
            "city": "Richmond",
            "address": "1776 Cambridge Drive, Richmond, VA 23238",
            "source_platform_link": "https://www.roi-nj.com/2020/02/25/healthcare/tryko-partners-grows-in-mid-atlantic-with-acquisition-of-3-skilled-nursing-facilities/",
            "source_facility_link": "https://projects.propublica.org/nursing-homes/homes/h-495272",
            "cms_owner_name": "Quinto Delta LLC (89%); Ukr Consulting LLC (10%)",
            "cms_affiliated_entity": "Affiliated With Marquis Health Services",
            "ownership_effective_date": "Feb 2020",
            "cms_change_of_ownership_flag": "yes",
            "pre_owner_name": "Lexington Rehabilitation & Healthcare Center / Cambridge Healthcare portfolio",
            "pre_owner_effective_end": "before Feb 2020",
            "pre_owner_pe_status": "unknown",
            "pre_operator_name": "Cambridge Healthcare portfolio",
            "post_operator_name": "Marquis Limited LLC / Reliant Pro Rehab LLC",
            "post_owner_pe_status": "pe",
            "transition_basis": "owner_and_operator_change",
            "transition_type": "likely_non_pe_to_pe",
            "transition_verified": "no",
            "match_quality": "exact",
            "verification_tier": "silver",
            "verification_notes": (
                "Trade press identifies Tryko Partners as the private equity buyer of Lexington Rehabilitation & "
                "Healthcare in Richmond as part of its February 2020 Virginia expansion, with Marquis Health Services "
                "as operator. The current ProPublica page for Canterbury Rehabilitation and Healthcare Center at the "
                "same address shows Tryko-linked Quinto Delta / Ukr Consulting ownership and Marquis managerial "
                "control. This is a strong silver_main row even though the pre-period facility-side ownership trail is "
                "coming mainly from the public deal coverage rather than a fully recovered historical CMS owner page."
            ),
            "analysis_sample": "silver_main",
            "evidence_pathway": "chain_deal_plus_facility_match",
            "current_pe_evidence": "facility_cms_direct",
            "pre_period_certainty": "unknown",
        },
        {
            "deal_id": "PE007",
            "pe_firm": "Tryko Partners",
            "platform_name": "Marquis Health Services",
            "facility_name": "Westmoreland Rehabilitation & Healthcare Center",
            "ccn": "495268",
            "state": "VA",
            "city": "Colonial Beach",
            "address": "2400 Mckinney Boulevard, Colonial Beach, VA 22443",
            "source_platform_link": "https://www.roi-nj.com/2020/02/25/healthcare/tryko-partners-grows-in-mid-atlantic-with-acquisition-of-3-skilled-nursing-facilities/",
            "source_facility_link": "https://projects.propublica.org/nursing-homes/homes/h-495268",
            "cms_owner_name": "Quinto Delta LLC (89%); Ukr Consulting LLC (10%)",
            "cms_affiliated_entity": "Affiliated With Marquis Health Services",
            "ownership_effective_date": "Feb 2020",
            "cms_change_of_ownership_flag": "yes",
            "pre_owner_name": "Cambridge Healthcare Holdings LLC / Mary Washington Convalescent & Nursing Care LLC",
            "pre_owner_effective_end": "before Feb 2020",
            "pre_owner_pe_status": "unknown",
            "pre_operator_name": "Cambridge Healthcare portfolio",
            "post_operator_name": "Marquis Limited LLC / Reliant Pro Rehab LLC",
            "post_owner_pe_status": "pe",
            "transition_basis": "owner_and_operator_change",
            "transition_type": "likely_non_pe_to_pe",
            "transition_verified": "no",
            "match_quality": "exact",
            "verification_tier": "silver",
            "verification_notes": (
                "Trade press identifies Tryko Partners as the private equity buyer of Westmoreland "
                "Rehabilitation & Healthcare Center in February 2020, with Marquis Health Services as operator. The "
                "current ProPublica page shows Tryko-linked Quinto Delta / Ukr Consulting ownership and Marquis "
                "managerial control, while the 2019 HealthcareComps page shows Cambridge Healthcare Holdings LLC in "
                "the ownership structure. This is a strong silver_main row, but the pre-period chain side is still "
                "treated as likely non-PE rather than fully verified."
            ),
            "analysis_sample": "silver_main",
            "evidence_pathway": "chain_deal_plus_facility_match",
            "current_pe_evidence": "facility_cms_direct",
            "pre_period_certainty": "likely_non_pe",
        },
        {
            "deal_id": "PE007",
            "pe_firm": "Tryko Partners",
            "platform_name": "Marquis Health Services",
            "facility_name": "Roosevelt Rehabilitation And Healthcare Center",
            "ccn": "395537",
            "state": "PA",
            "city": "Philadelphia",
            "address": "7800 Bustleton Avenue, Philadelphia, PA 19152",
            "source_platform_link": "https://skillednursingnews.com/2020/01/blueprint-pulls-off-seven-snf-sale-in-alabama-tryko-grows-portfolio-in-philadelphia/",
            "source_facility_link": "https://projects.propublica.org/nursing-homes/homes/h-395537",
            "cms_owner_name": "Glendale Opportunity Fund LLC (76%); Rsbrm Holdings LLC (22%)",
            "cms_affiliated_entity": "Affiliated With Marquis Health Services",
            "ownership_effective_date": "Nov 2019",
            "cms_change_of_ownership_flag": "yes",
            "pre_owner_name": "Glendale Uptown Home / GS Operator, L.P.",
            "pre_owner_effective_end": "before Nov 2019",
            "pre_owner_pe_status": "unknown",
            "pre_operator_name": "Glendale Manager, LP / Craig Flashner",
            "post_operator_name": "Marquis Limited LLC / Reliant Pro Rehab LLC",
            "post_owner_pe_status": "pe",
            "transition_basis": "owner_and_operator_change",
            "transition_type": "likely_non_pe_to_pe",
            "transition_verified": "no",
            "match_quality": "exact",
            "verification_tier": "silver",
            "verification_notes": (
                "Public deal coverage identifies Tryko Partners as the buyer behind the Philadelphia acquisition of "
                "Glendale Uptown Home, which was rebranded as Roosevelt Rehabilitation & Healthcare Center in late "
                "2019 under Marquis Health Services. The current ProPublica page for the same CCN and address shows "
                "Tryko-linked indirect ownership and Marquis managerial control since Nov 2019, while the 2019 "
                "HealthcareComps page lists Glendale Uptown Home under GS Operator, L.P. This supports a "
                "silver_main non-PE-to-PE transition, though the pre-period seller is a private for-profit rather "
                "than a fully audited nonprofit."
            ),
            "analysis_sample": "silver_main",
            "evidence_pathway": "chain_deal_plus_facility_match",
            "current_pe_evidence": "facility_cms_direct",
            "pre_period_certainty": "likely_non_pe",
        },
        {
            "deal_id": "PE007",
            "pe_firm": "Tryko Partners",
            "platform_name": "Marquis Health Services",
            "facility_name": "Markley Rehabilitation And Healthcare Center",
            "ccn": "395483",
            "state": "PA",
            "city": "Norristown",
            "address": "550 East Fornance Street, Norristown, PA 19401",
            "source_platform_link": "https://seniorshousingbusiness.com/tryko-partners-acquires-regina-community-nursing-center-in-norristown-pennsylvania/",
            "source_facility_link": "https://projects.propublica.org/nursing-homes/homes/h-395483",
            "cms_owner_name": "Quinto Nexgen LLC (79%); Ukr Nexgen LLC (20%)",
            "cms_affiliated_entity": "Affiliated With Marquis Health Services",
            "ownership_effective_date": "Dec 2020",
            "cms_change_of_ownership_flag": "yes",
            "pre_owner_name": "Regina Community Nursing Center / Regina Nursing Center",
            "pre_owner_effective_end": "before Dec 2020",
            "pre_owner_pe_status": "non_pe",
            "pre_operator_name": "Regina Community Nursing Center",
            "post_operator_name": "Marquis Limited LLC / Reliant Pro Rehab LLC",
            "post_owner_pe_status": "pe",
            "transition_basis": "owner_and_operator_change",
            "transition_type": "likely_non_pe_to_pe",
            "transition_verified": "no",
            "match_quality": "exact",
            "verification_tier": "silver",
            "verification_notes": (
                "Public deal coverage identifies Tryko Partners as the private equity buyer of Regina Community "
                "Nursing Center in December 2020, with the facility rebranded as Markley Rehabilitation & Healthcare "
                "Center under Marquis Health Services. The current ProPublica ownership page shows Tryko-linked "
                "Quinto Nexgen / Ukr Nexgen ownership and Marquis managerial control, while the 2019 HealthcareComps "
                "page identifies Regina Community Nursing Center as a faith-based nonprofit. This is a strong "
                "silver_main row and one of the cleaner new Tryko additions."
            ),
            "analysis_sample": "silver_main",
            "evidence_pathway": "chain_deal_plus_facility_match",
            "current_pe_evidence": "facility_cms_direct",
            "pre_period_certainty": "clear_non_pe",
        },
        {
            "deal_id": "PE016",
            "pe_firm": "Pacifica Companies",
            "platform_name": "California-Nevada Methodist Homes SNFs",
            "facility_name": "Lake Park Healthcare Center",
            "ccn": "555113",
            "state": "CA",
            "city": "Oakland",
            "address": "1850 Alice Street, Oakland, CA 94612",
            "source_platform_link": "https://oag.ca.gov/news/press-releases/attorney-general-bonta-conditionally-approves-sale-california-nevada-methodist",
            "source_facility_link": "https://projects.propublica.org/nursing-homes/homes/h-555113",
            "cms_owner_name": "Aoas, LLC (100%)",
            "cms_affiliated_entity": "Affiliated With Aspen Skilled Healthcare",
            "ownership_effective_date": "Sep 2023",
            "cms_change_of_ownership_flag": "yes",
            "pre_owner_name": "California-Nevada Methodist Homes / Lake Park Retirement Residence",
            "pre_owner_effective_end": "before Sep 2023",
            "pre_owner_pe_status": "non_pe",
            "pre_operator_name": "California-Nevada Methodist Homes",
            "post_operator_name": "Aoas, LLC / Aspen Skilled Healthcare INC / Sequoia Healthcare Group LLC",
            "post_owner_pe_status": "pe",
            "transition_basis": "owner_and_operator_change",
            "transition_type": "likely_non_pe_to_pe",
            "transition_verified": "no",
            "match_quality": "exact",
            "verification_tier": "silver",
            "verification_notes": (
                "California AG materials identify Pacifica Companies LLC as the buyer of California-Nevada Methodist "
                "Homes, a nonprofit operator whose Lake Park campus included a 35-bed skilled nursing facility in "
                "Oakland. The current ProPublica page for Lake Park Healthcare Center shows Aoas, LLC as direct owner "
                "with Aspen Skilled Healthcare and Sequoia Healthcare Group in the ownership chain since Sep 2023. "
                "Because Pacifica is publicly described as a private equity buyer and the current facility ownership "
                "bridges into the known Pacifica/Aspen California network, this is a strong silver_main row."
            ),
            "analysis_sample": "silver_main",
            "evidence_pathway": "chain_deal_plus_facility_match",
            "current_pe_evidence": "chain_owner_match",
            "pre_period_certainty": "clear_non_pe",
        },
        {
            "deal_id": "PE017",
            "pe_firm": "Pacifica Companies",
            "platform_name": "Keiro SNFs",
            "facility_name": "Kei Ai Los Angeles Healthcare Center",
            "ccn": "555438",
            "state": "CA",
            "city": "Los Angeles",
            "address": "2221 Lincoln Park Ave, Los Angeles, CA 90031",
            "source_platform_link": "https://seniorshousingbusiness.com/blueprint-arranges-41m-sale-of-642-unit-keiro-portfolio-in-los-angeles/",
            "source_facility_link": "https://projects.propublica.org/nursing-homes/homes/h-555438",
            "cms_owner_name": "Alal LLC (100%)",
            "cms_affiliated_entity": "Affiliated With Aspen Skilled Healthcare",
            "ownership_effective_date": "Apr 2016",
            "cms_change_of_ownership_flag": "yes",
            "pre_owner_name": "Keiro Nursing Home",
            "pre_owner_effective_end": "before Apr 2016",
            "pre_owner_pe_status": "non_pe",
            "pre_operator_name": "Keiro Senior HealthCare",
            "post_operator_name": "Alal LLC / Aspen Skilled Healthcare Inc",
            "post_owner_pe_status": "pe",
            "transition_basis": "owner_and_operator_change",
            "transition_type": "likely_non_pe_to_pe",
            "transition_verified": "no",
            "match_quality": "exact",
            "verification_tier": "silver",
            "verification_notes": (
                "Blueprint reports that Pacifica Companies, described as a private investment firm, bought Keiro's "
                "four-property Los Angeles portfolio in 2016 and leased the two skilled nursing facilities to Aspen "
                "Healthcare. Keiro's own post-sale communication confirms that the former Keiro Nursing Home was "
                "renamed Kei Ai Los Angeles Healthcare Center and operated by Aspen Skilled Healthcare. The current "
                "ProPublica page for the same CCN shows Alal LLC with Aspen Skilled Healthcare in the ownership chain "
                "since Apr 2016, making this a strong silver_main nonprofit-to-PE entry."
            ),
            "analysis_sample": "silver_main",
            "evidence_pathway": "chain_deal_plus_facility_match",
            "current_pe_evidence": "chain_owner_match",
            "pre_period_certainty": "clear_non_pe",
        },
        {
            "deal_id": "PE017",
            "pe_firm": "Pacifica Companies",
            "platform_name": "Keiro SNFs",
            "facility_name": "Kei Ai South Bay Healthcare Center",
            "ccn": "555306",
            "state": "CA",
            "city": "Gardena",
            "address": "15115 S Vermont Ave, Gardena, CA 90247",
            "source_platform_link": "https://seniorshousingbusiness.com/blueprint-arranges-41m-sale-of-642-unit-keiro-portfolio-in-los-angeles/",
            "source_facility_link": "https://projects.propublica.org/nursing-homes/homes/h-555306",
            "cms_owner_name": "Agva LLC (100%)",
            "cms_affiliated_entity": "Affiliated With Aspen Skilled Healthcare",
            "ownership_effective_date": "May 2016",
            "cms_change_of_ownership_flag": "yes",
            "pre_owner_name": "South Bay Keiro Nursing Home",
            "pre_owner_effective_end": "before May 2016",
            "pre_owner_pe_status": "non_pe",
            "pre_operator_name": "Keiro Senior HealthCare",
            "post_operator_name": "Agva LLC / Aspen Skilled Healthcare Inc",
            "post_owner_pe_status": "pe",
            "transition_basis": "owner_and_operator_change",
            "transition_type": "likely_non_pe_to_pe",
            "transition_verified": "no",
            "match_quality": "exact",
            "verification_tier": "silver",
            "verification_notes": (
                "Blueprint reports that Pacifica Companies bought Keiro's Los Angeles portfolio and leased the two "
                "skilled nursing facilities to Aspen Healthcare, while Keiro's post-sale notice states that South Bay "
                "Keiro Nursing Home became Kei Ai South Bay Healthcare Center under Aspen Skilled Healthcare. The "
                "current ProPublica page for the same CCN shows Agva LLC in direct ownership with Aspen-linked "
                "management beginning in May 2016. This supports a strong silver_main nonprofit-to-PE transition."
            ),
            "analysis_sample": "silver_main",
            "evidence_pathway": "chain_deal_plus_facility_match",
            "current_pe_evidence": "chain_owner_match",
            "pre_period_certainty": "clear_non_pe",
        },
        {
            "deal_id": "PE007",
            "pe_firm": "Tryko Partners",
            "platform_name": "Marquis Health Services",
            "facility_name": "Springfield Rehabilitation And Healthcare Center",
            "ccn": "395690",
            "state": "PA",
            "city": "Springfield",
            "address": "463 West Sproul Road, Springfield, PA 19064",
            "source_platform_link": "https://skillednursingnews.com/2020/06/tryko-expands-again-with-pa-pickup-monticello-provides-41m-for-two-snf-refinance/",
            "source_facility_link": "https://projects.propublica.org/nursing-homes/homes/h-395690",
            "cms_owner_name": "Quinto Delta LLC (89%); Ukr Consulting LLC (10%)",
            "cms_affiliated_entity": "Affiliated With Marquis Health Services",
            "ownership_effective_date": "Jun 2020",
            "cms_change_of_ownership_flag": "yes",
            "pre_owner_name": "Harlee Manor Inc.",
            "pre_owner_effective_end": "before Jun 2020",
            "pre_owner_pe_status": "unknown",
            "pre_operator_name": "Harlee Manor Nursing and Rehabilitation Center",
            "post_operator_name": "Quinto Delta LLC / Marquis Health Services",
            "post_owner_pe_status": "pe",
            "transition_basis": "owner_and_operator_change",
            "transition_type": "likely_non_pe_to_pe",
            "transition_verified": "no",
            "match_quality": "exact",
            "verification_tier": "silver",
            "verification_notes": (
                "Public deal coverage identifies Tryko Partners as the buyer behind the Pennsylvania pickup of "
                "Harlee Manor, which became Springfield Rehabilitation & Healthcare Center in June 2020 under "
                "Marquis Health Services. The current ProPublica page for the same CCN and address shows "
                "Tryko-linked Quinto Delta / Ukr Consulting ownership, while the 2019 HealthcareComps page lists "
                "Harlee Manor Inc. at the same Springfield address. This makes Springfield a strong silver_main row "
                "with a facility-specific bridge from the public deal source into current CMS ownership data."
            ),
            "analysis_sample": "silver_main",
            "evidence_pathway": "chain_deal_plus_facility_match",
            "current_pe_evidence": "facility_cms_direct",
            "pre_period_certainty": "likely_non_pe",
        },
    ]
    return rows


def append_new_deal_rows(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if not df["deal_id"].eq("PE016").any():
        rows.append(
            {
                "deal_id": "PE016",
                "pe_firm": "Pacifica Companies",
                "platform_name": "California-Nevada Methodist Homes SNFs",
                "operator_aliases": "Pacifica Companies; Aspen Skilled Healthcare; Sequoia Healthcare Group; Aoas LLC",
                "reported_deal_year": "2022",
                "reported_current_or_recent_scale": "California AG materials describe Pacifica's acquisition of CNMH's two California continuing care campuses, including a 35-bed SNF at Lake Park and a 26-bed SNF at Forest Hill",
                "primary_geography": "California",
                "source_1": "https://oag.ca.gov/news/press-releases/attorney-general-bonta-conditionally-approves-sale-california-nevada-methodist",
                "source_2": "https://seniorhousingnews.com/2024/04/19/pacifica-adds-15-communities-in-180-5m-deal-as-rhf-shifts-senior-living-strategy/",
                "pe_evidence_type": "California AG materials identify Pacifica as the buyer of CNMH, and Senior Housing News describes Pacifica as a private equity firm",
                "pe_confidence": "high",
                "control_type": "portfolio_buyer_with_affiliated_operators",
                "stake_disclosed": "not_disclosed",
                "stake_value": "",
                "board_control_evidence": "unknown",
                "managerial_control_evidence": "yes",
                "control_notes": "The nonprofit-to-buyer transaction is explicit in California AG materials, while current CMS-linked ownership bridges the SNF into Aspen/Sequoia buyer-side entities associated with Pacifica's California skilled nursing footprint.",
                "initial_notes": "New silver-focused Pacifica cluster. Lake Park is the cleanest current row because the pre-period nonprofit seller is explicit and the current ownership page shows Aspen-linked post-close control.",
                "next_verification_step": "Add Forest Hill only if its current buyer-side ownership chain can be bridged to Pacifica/Aspen with the same clarity as Lake Park.",
            }
        )
    if not df["deal_id"].eq("PE017").any():
        rows.append(
            {
                "deal_id": "PE017",
                "pe_firm": "Pacifica Companies",
                "platform_name": "Keiro SNFs",
                "operator_aliases": "Pacifica Companies; Aspen Skilled Healthcare; Kei-Ai; ALAL LLC; AGVA LLC",
                "reported_deal_year": "2016",
                "reported_current_or_recent_scale": "Blueprint reported Pacifica's acquisition of Keiro's four-property Los Angeles portfolio, including two skilled nursing facilities totaling 398 beds that Pacifica leased to Aspen Healthcare.",
                "primary_geography": "California",
                "source_1": "https://seniorshousingbusiness.com/blueprint-arranges-41m-sale-of-642-unit-keiro-portfolio-in-los-angeles/",
                "source_2": "https://www.nichibei.org/2016/06/escrow-closes-but-criticism-of-keiro-sale-continues/",
                "pe_evidence_type": "Blueprint describes Pacifica as a private investment firm and reports that Pacifica bought the Keiro portfolio and leased the skilled nursing facilities to Aspen Healthcare.",
                "pe_confidence": "high",
                "control_type": "portfolio_buyer_with_affiliated_operators",
                "stake_disclosed": "not_disclosed",
                "stake_value": "$41 million",
                "board_control_evidence": "unknown",
                "managerial_control_evidence": "yes",
                "control_notes": "The nonprofit seller and Pacifica-to-Aspen operator bridge are explicit in public Keiro transaction coverage, and the current ProPublica facility pages show Aspen-linked ownership/control beginning in spring 2016.",
                "initial_notes": "Strong silver-focused California cluster built from the public Keiro sale coverage. Both skilled nursing facilities appear to enter Aspen/Pacifica control in 2016, directly within the sample window.",
                "next_verification_step": "Keep the two skilled nursing facilities in silver_main and only add less directly bridged Keiro assets if they become useful for descriptive appendices.",
            }
        )
    if not rows:
        return df
    out = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
    return out


def append_new_rows(df: pd.DataFrame) -> pd.DataFrame:
    existing_key_to_index = {
        (str(deal_id), str(ccn)): idx
        for idx, (deal_id, ccn) in enumerate(zip(df["deal_id"], df["ccn"]))
    }
    rows = []
    for row in new_rows():
        key = (str(row["deal_id"]), str(row["ccn"]))
        if key in existing_key_to_index:
            idx = existing_key_to_index[key]
            for col, value in row.items():
                df.at[idx, col] = value
            continue
        rows.append(row)

    all_cols = list(df.columns)
    df = df.reindex(columns=all_cols)
    if not rows:
        return df

    new_df = pd.DataFrame(rows)
    for col in new_df.columns:
        if col not in all_cols:
            all_cols.append(col)
    df = df.reindex(columns=all_cols)
    new_df = new_df.reindex(columns=all_cols)
    out = pd.concat([df, new_df], ignore_index=True)
    return out


def update_deal_notes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    updates = {
        "PE001": {
            "initial_notes": "Silver-focused cluster with one gold row (Sunrise Point), one silver-main row (Rose Manor), and the remaining Portopiccolo homes held as silver-unclear because the pre-period often runs through Sava/SSC or Signature-style structures.",
            "next_verification_step": "Only promote additional Portopiccolo rows if a clearly non-PE pre-period owner/operator becomes explicit on a facility-level historical page; otherwise keep them silver_unclear.",
        },
        "PE002": {
            "initial_notes": "Silver-focused Texas cluster. Current CMS-linked pages repeatedly show public or nonprofit direct owners with Regency managerial control, but the immediate pre-Regency operator is often missing so the cleanest cases stay silver_main rather than gold.",
            "next_verification_step": "Use the current four Texas silver-main rows as the working Regency sample and only add more if the facility-level bridge and 2016-2024 entry timing are explicit.",
        },
        "PE007": {
            "initial_notes": "Dual-track Tryko/Marquis cluster. The original New Jersey nonprofit divestitures remain gold_main, and the new Virginia/Pennsylvania additions provide silver_main scale where the PE buyer and facility names are explicit but the pre-period side is less fully verified.",
            "next_verification_step": "Use the current NJ rows as the gold core and the Virginia/Pennsylvania rows as silver_main; only promote additional Tryko facilities when the seller and facility mapping are equally explicit in public deal coverage.",
        },
        "PE008": {
            "initial_notes": "Dual-track cluster with the largest verified gold sample and the strongest silver expansion opportunities. ABCM provides a clean non-PE pre-period seller, while Cascade/Legacy is consistently visible in the 2024 post-period CMS ownership trail.",
            "next_verification_step": "Treat the existing 17 verified Iowa facilities as gold_main and the thinner or newly mapped ABCM-to-Legacy rows as silver_main until they receive a full facility-first re-verification pass.",
        },
        "PE013": {
            "initial_notes": "Primarily a gold-usable Florida cluster. The strongest rows move from local pre-period operators into the Gold FL trust structure, while Greystone-predecessor homes remain silver_unclear.",
            "next_verification_step": "Keep the local-owner Gold FL rows in gold_main and leave Greystone-linked predecessors out of silver_main unless a cleaner non-PE bridge appears.",
        },
        "PE014": {
            "initial_notes": "Silver-unclear only. The Eskaton-to-Cypress turnover is real and the nonprofit pre-period side is clean, but International Equity Partners is still described publicly as an investment-management control buyer rather than explicitly as PE.",
            "next_verification_step": "Preserve the Eskaton rows as silver_unclear until a source explicitly supports treating IEP as a PE sponsor under the project standard.",
        },
        "PE015": {
            "initial_notes": "Gold-focused California cluster. Auburn, Bixby, and Pioneer remain in the main verified treatment sample, with Pioneer retained as gold_main despite a silver verification tier because it was already accepted into the 31-facility core sample.",
            "next_verification_step": "Use the three RHF-to-Pacifica rows as the active California gold sample and only add more if the facility-to-designee bridge is explicit in AG materials and current CMS-linked ownership data.",
        },
        "PE016": {
            "initial_notes": "Silver-focused Pacifica extension from the California-Nevada Methodist Homes transaction. Lake Park is currently the cleanest row because the nonprofit seller, Pacifica buyer, and Aspen-linked post-close ownership bridge are all visible in public sources.",
            "next_verification_step": "Keep Lake Park in silver_main and only add Forest Hill once its current ownership chain can be tied as clearly into Pacifica/Aspen buyer-side entities.",
        },
        "PE017": {
            "initial_notes": "Silver-focused California cluster built from the public Keiro sale. The nonprofit seller, Pacifica buyer, and Aspen operator bridge are explicit, and both skilled nursing facilities show Aspen-linked post-close control beginning in 2016.",
            "next_verification_step": "Keep the two Kei-Ai skilled nursing facilities in silver_main and only broaden the cluster if additional Keiro assets become analytically useful and equally well bridged.",
        },
    }
    for deal_id, cols in updates.items():
        mask = df["deal_id"].eq(deal_id)
        for col, value in cols.items():
            df.loc[mask, col] = value
    return df


def build_summary(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    work = df.copy()
    work["treat_year"] = work["ownership_effective_date"].map(extract_year)
    required_silver_cols = [
        "deal_id",
        "source_platform_link",
        "source_facility_link",
        "ownership_effective_date",
        "evidence_pathway",
        "current_pe_evidence",
        "pre_period_certainty",
    ]
    summary = (
        work.dropna(subset=["analysis_sample", "treat_year"])
        .groupby(["analysis_sample", "treat_year", "state", "deal_id"], dropna=False)
        .size()
        .reset_index(name="facility_count")
        .sort_values(["analysis_sample", "treat_year", "state", "deal_id"])
    )

    qa = {
        "total_rows": int(len(work)),
        "gold_main_rows": int(work["analysis_sample"].eq("gold_main").sum()),
        "silver_main_rows": int(work["analysis_sample"].eq("silver_main").sum()),
        "silver_unclear_rows": int(work["analysis_sample"].eq("silver_unclear").sum()),
        "exclude_rows": int(work["analysis_sample"].eq("exclude").sum()),
        "gold_main_verified_count": int(
            (
                work["analysis_sample"].eq("gold_main")
                & work["transition_verified"].fillna("").str.lower().eq("yes")
            ).sum()
        ),
        "duplicate_deal_ccn": int(work.duplicated(subset=["deal_id", "ccn"]).sum()),
        "silver_main_missing_required_fields": int(
            work.loc[
                work["analysis_sample"].eq("silver_main"), required_silver_cols
            ]
            .replace("", pd.NA)
            .isna()
            .any(axis=1)
            .sum()
        ),
        "silver_main_pre_owner_pe_rows": int(
            (
                work["analysis_sample"].eq("silver_main")
                & work["pre_owner_pe_status"].fillna("").str.lower().eq("pe")
            ).sum()
        ),
        "treat_year_parse_failures_gold_or_silver": int(
            work.loc[
                work["analysis_sample"].isin(["gold_main", "silver_main"]), "treat_year"
            ]
            .isna()
            .sum()
        ),
    }
    return summary, qa


def generate_notes(df: pd.DataFrame, deals: pd.DataFrame) -> str:
    work = df.copy()
    work["treat_year"] = work["ownership_effective_date"].map(extract_year)
    work["summary_note"] = work["verification_notes"].map(first_sentence)
    deal_meta = deals.set_index("deal_id")[["platform_name", "source_1", "source_2"]].to_dict("index")

    sections = [
        "# Ownership Transition Verification Notes",
        "",
        "This note tracks the integrated `gold_main`, `silver_main`, `silver_unclear`, and `exclude` classifications used in the repo after the 2016–2024 silver expansion pass.",
        "",
        "Classification summary:",
        "",
        "- `gold_main`: the original verified treatment sample used for the main paper results.",
        "- `silver_main`: explicit PE deal source plus a facility-level platform bridge, but still below the fully verified gold standard.",
        "- `silver_unclear`: likely PE-linked facilities where the pre-period side is financially complex or the sponsor/bridge is still too ambiguous for the main silver sample.",
        "- `exclude`: rows preserved in the integrated master file but outside the active 2016–2024 gold/silver treatment sets.",
        "",
    ]

    rationale = {
        "PE001": "Post-transition Portopiccolo evidence is visible, but most pre-period structures run through Sava/SSC or Signature-style chains. Rose Manor is the only row currently strong enough for `silver_main`.",
        "PE002": "Regency is explicitly linked to AHP's Texas platform, and several current CMS pages show public/nonprofit direct owners with Regency managerial control. Missing immediate pre-Regency operator detail keeps the cluster in `silver_main` rather than `gold_main`.",
        "PE007": "Tryko / Marquis remains the cleanest fully verified nonprofit-to-PE cluster in the repo.",
        "PE008": "Cascade / Legacy is the strongest expansion cluster: ABCM gives a clean non-PE seller, while current CMS ownership pages repeatedly show Legacy/Cascade post-period control. The silver additions come from the same ABCM portfolio but remain below the original gold verification pass.",
        "PE013": "Gold FL Trust II is gold-usable when the pre-period owner is clearly local. Facilities with Greystone-era predecessor structures remain `silver_unclear`.",
        "PE014": "The Eskaton-to-Cypress transition is real, but the sponsor identity still falls short of the project's PE standard, so the entire cluster remains `silver_unclear`.",
        "PE015": "Pacifica / RHF remains an active California gold cluster. Pioneer stays in `gold_main` because it was already accepted into the verified core sample, even though its post-period evidence is secondary-CMS-derived.",
        "PE016": "California-Nevada Methodist Homes -> Pacifica is the strongest new public-source Pacifica lead. Lake Park enters `silver_main` because the nonprofit seller, Pacifica buyer, and Aspen-linked post-close chain are all visible, while Forest Hill remains out until the same bridge is clearer.",
        "PE017": "Keiro -> Pacifica / Aspen adds a new California silver cluster. The public sale materials name the nonprofit seller and the two skilled nursing facilities, and the current ProPublica pages show Aspen-linked ownership/control beginning in 2016.",
    }

    sample_order = ["gold_main", "silver_main", "silver_unclear", "exclude"]
    sample_titles = {
        "gold_main": "Gold-usable",
        "silver_main": "Silver-main",
        "silver_unclear": "Silver-unclear",
        "exclude": "Excluded for Current Build",
    }

    for deal_id in FACILITY_SORT_ORDER:
        sub = work[work["deal_id"].eq(deal_id)].copy()
        if sub.empty:
            continue
        meta = deal_meta.get(deal_id, {})
        sections.extend(
            [
                f"## {deal_id}: {meta.get('platform_name', deal_id)}",
                "",
                rationale.get(deal_id, ""),
                "",
                f"Sources: [source 1]({meta.get('source_1', '')}), [source 2]({meta.get('source_2', '')})",
                "",
            ]
        )
        for sample in sample_order:
            bucket = sub[sub["analysis_sample"].eq(sample)].copy()
            if bucket.empty:
                continue
            sections.extend([f"### {sample_titles[sample]}", ""])
            bucket = bucket.sort_values(["state", "facility_name"])
            for _, row in bucket.iterrows():
                ccn = row["ccn"]
                year = row["ownership_effective_date"]
                state = row["state"]
                note = row["summary_note"]
                sections.append(
                    f"- `{row['facility_name']}` (`{ccn}`, `{state}`, `{year}`): {note}"
                )
            sections.append("")

    return "\n".join(sections).strip() + "\n"


def main() -> None:
    facility_df = pd.read_csv(FACILITY_CSV, dtype=str).fillna("")
    facility_df = normalize_existing_rows(facility_df)
    facility_df = append_new_rows(facility_df)

    # Preserve the original 31 gold rows as the main sample.
    assert int(facility_df["analysis_sample"].eq("gold_main").sum()) == 31

    facility_df["deal_sort"] = facility_df["deal_id"].map(FACILITY_ORDER_INDEX).fillna(999)
    facility_df["facility_sort"] = facility_df["facility_name"].str.lower()
    facility_df = facility_df.sort_values(["deal_sort", "facility_sort", "ccn"]).drop(
        columns=["deal_sort", "facility_sort"]
    )

    if facility_df.duplicated(subset=["deal_id", "ccn"]).any():
        raise ValueError("Duplicate deal_id + ccn rows detected after silver build.")

    deal_df = pd.read_csv(DEAL_CSV, dtype=str).fillna("")
    deal_df = append_new_deal_rows(deal_df)
    deal_df = update_deal_notes(deal_df)

    summary_df, qa = build_summary(facility_df)
    notes_md = generate_notes(facility_df, deal_df)

    facility_df.to_csv(FACILITY_CSV, index=False)
    deal_df.to_csv(DEAL_CSV, index=False)
    summary_df.to_csv(SUMMARY_CSV, index=False)
    NOTES_MD.write_text(notes_md, encoding="utf-8")
    QA_JSON.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
