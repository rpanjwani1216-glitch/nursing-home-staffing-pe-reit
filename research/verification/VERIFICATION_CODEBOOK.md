# Verification Codebook
## PE and REIT Treatment Sample Construction

**Project:** Effects of PE and REIT Takeovers on Nursing Home Staffing  
**Author:** Rohan Panjwani, ECON 1430, Brown University

---

## Overview

Treatment facilities were identified through a multi-stage internet-based verification process. No single authoritative database lists private equity or REIT ownership of nursing homes — CMS ownership filings use legal entity names that obscure PE sponsors, and deal disclosures are voluntary and inconsistent. The strategy therefore combines:

1. **Deal identification** — find the PE firm / REIT and their acquisition target from public sources (trade press, regulatory filings, investigative journalism)
2. **Facility mapping** — link the deal to specific licensed facilities using CMS ownership pages and CHOW filings
3. **Pre-period verification** — confirm the pre-acquisition owner was *not* already PE-controlled, which is necessary for a clean DiD treatment

The output is two files:
- `research/treatment_inputs/pe_facility_verification.csv` — 61 rows, one per PE-linked facility
- `research/treatment_inputs/reit_facility_verification.csv` — 81 rows, one per REIT-linked facility

Both files are read directly by the Python pipeline to assign treatment status.

---

## Part I: PE Verification

### 1.1 Deal identification process

PE deals were identified using a combination of:

| Source | What it provides |
|--------|-----------------|
| **Public Citizen "Pillaging the Patient"** (citizen.org) | Compiled list of PE-owned nursing home chains; names sponsors and operating platforms |
| **ProPublica Nursing Home Inspect** (propublica.org/nursing-homes) | Facility-level ownership pages that mirror CMS data; shows current and historical owner/operator structures |
| **CMS Care Compare / Provider of Services** | Official ownership and affiliation fields; CHOW filings record effective date of ownership changes |
| **Trade press** (Skilled Nursing News, Becker's Hospital Review, Senior Housing News) | Announced acquisition transactions with buyer identity, seller identity, and facility names |
| **California Attorney General filings** (oag.ca.gov) | Conditional approval letters for healthcare transactions name buyers, sellers, and specific facilities |
| **Blueprint Healthcare Real Estate Advisors** (seniorshousingbusiness.com) | Transaction advisors whose press releases name buyers, sellers, and bed counts |

The search process was iterative: a deal lead (e.g., "Cascade Capital buys 29 Iowa nursing homes") was found in trade press, then verified by checking that the named facilities appeared in CMS ownership data under the expected PE-linked entities.

### 1.2 Gold vs. silver classification

The key methodological challenge is determining whether a facility's **pre-acquisition owner was genuinely non-PE**. Without this, the DiD comparison is contaminated.

| Tier | Criteria |
|------|----------|
| **gold** | Post-acquisition PE ownership confirmed by ≥2 independent sources (e.g., trade press deal announcement + current CMS/ProPublica ownership page); pre-acquisition owner confirmed non-PE (e.g., nonprofit seller named in press or regulatory filing) |
| **silver** | Post-acquisition PE ownership confirmed by a deal-level source plus a facility-level CMS/platform bridge; pre-acquisition owner status is inferred or partially verified |
| **silver_unclear** | Post-acquisition PE ownership visible in CMS data, but pre-acquisition ownership is ambiguous (e.g., prior owner was itself a financialized chain like SavaSeniorCare) |
| **exclude** | Row retained in master file for reference but excluded from all analysis samples |

For analysis, `gold_main` and `silver_main` rows are included in the main treatment sample (52 facilities: 31 gold + 21 silver). `silver_unclear` and `exclude` rows are dropped.

### 1.3 `pe_facility_verification.csv` column definitions

| Column | Type | Description |
|--------|------|-------------|
| `deal_id` | string | Internal deal identifier (PE001–PE017). Links to `pe_acquisition_deals.csv`. |
| `pe_firm` | string | Name of the private equity sponsor or controlling investment firm |
| `platform_name` | string | Operating platform or brand name used by the PE firm for its nursing home portfolio |
| `facility_name` | string | Facility name as it appears in CMS/ProPublica at time of verification |
| `ccn` | string | CMS Certification Number — the unique 6-digit facility identifier used throughout the pipeline |
| `state` | string | 2-letter state abbreviation |
| `city` | string | City of the facility |
| `address` | string | Street address |
| `source_platform_link` | URL | Primary source establishing the PE deal at the platform level (e.g., Public Citizen article, trade press deal announcement) |
| `source_facility_link` | URL | Primary source establishing PE ownership at the individual facility level (e.g., ProPublica facility page, California AG approval letter) |
| `cms_owner_name` | string | Full legal owner name(s) as listed on the current CMS/ProPublica ownership page |
| `cms_affiliated_entity` | string | CMS affiliation field, if populated — often names the PE principals or managing entity |
| `ownership_effective_date` | string | Date (or approximate date) when the PE-linked ownership structure became effective per CMS records |
| `cms_change_of_ownership_flag` | string | Whether a CMS CHOW filing was found (`yes` / `no` / blank) |
| `pre_owner_name` | string | Name of the pre-acquisition owner as identified from historical CMS data, ProPublica archive pages, or deal press |
| `pre_owner_effective_end` | string | Approximate date when the pre-acquisition owner's period ended |
| `pre_owner_pe_status` | categorical | PE status of the pre-acquisition owner: `non_pe`, `likely_non_pe`, `unknown` |
| `pre_operator_name` | string | Operator or management company in the pre-acquisition period, if distinct from owner |
| `post_operator_name` | string | Operator or management company in the post-acquisition period |
| `post_owner_pe_status` | categorical | Always `pe` for included rows — confirms PE control in the post-period |
| `transition_basis` | string | Narrative description of the ownership change mechanism (e.g., "nonprofit sold to PE buyer via brokered portfolio transaction") |
| `transition_type` | categorical | Classification of the transition: `non_pe_to_pe`, `likely_non_pe_to_pe`, `unclear` |
| `transition_verified` | categorical | Whether the transition is considered verified for treatment coding: `yes`, `no` |
| `match_quality` | categorical | Confidence in the facility-to-deal match: `exact` (CCN or name directly confirmed in source), `probable` (inferred from platform and geography) |
| `verification_tier` | categorical | `gold` or `silver` — see §1.2 |
| `verification_notes` | text | Free-text narrative summarizing the evidence found and any remaining uncertainty |
| `analysis_sample` | categorical | Final sample assignment: `gold_main`, `silver_main`, `silver_unclear`, `exclude` |
| `evidence_pathway` | categorical | How the facility was linked to the deal: `chain_deal_plus_facility_match` (deal source + facility-level CMS match) or `facility_public_current_plus_prehistory` (facility page alone provides full pre/post history) |
| `current_pe_evidence` | categorical | Nature of the post-period PE evidence: `facility_cms_direct` (CMS page names PE entity directly), `facility_cms_managerial` (CMS shows PE as manager, not direct owner), `chain_owner_match` (facility name appears in deal coverage as part of acquired portfolio), `secondary_cms_derived` (PE inferred from related CMS entity network) |
| `pre_period_certainty` | categorical | Confidence that the pre-period was non-PE: `clear_non_pe`, `likely_non_pe`, `likely_pe_or_financialized`, `unknown` |

### 1.4 `pe_acquisition_deals.csv` column definitions

One row per PE deal. Links to `pe_facility_verification.csv` via `deal_id`.

| Column | Description |
|--------|-------------|
| `deal_id` | Internal identifier (PE001–PE017) |
| `pe_firm` | Private equity sponsor name |
| `platform_name` | Operating brand/platform |
| `operator_aliases` | All known operator entity names used by this platform across facilities |
| `reported_deal_year` | Year the deal was publicly reported or closed |
| `reported_current_or_recent_scale` | Number of facilities or portfolio size as reported in primary sources |
| `primary_geography` | States where the deal has identified facilities |
| `source_1`, `source_2` | Primary URLs used to establish the deal |
| `pe_evidence_type` | Type of evidence establishing PE sponsorship |
| `pe_confidence` | Confidence in PE classification: `high`, `medium`, `low` |
| `control_type` | How PE exercises control: `platform_owner_or_majority_control`, `owner_and_affiliated_operator`, `portfolio_buyer_with_affiliated_operators`, etc. |
| `stake_disclosed` | Whether the equity stake percentage was publicly disclosed (`yes` / `not_disclosed`) |
| `stake_value` | Disclosed stake value or deal price, if available |
| `board_control_evidence` | Whether board control evidence exists |
| `managerial_control_evidence` | Whether evidence of day-to-day managerial control exists |
| `control_notes` | Narrative on the nature of PE control |
| `initial_notes` | Summary notes from initial deal verification |
| `next_verification_step` | Outstanding steps needed to expand the verified sample for this deal |

---

## Part II: REIT Verification

### 2.1 Overview

REIT ownership identification used a different strategy than PE because CMS data includes an `any_reit_owner` flag (derived from SEC filings cross-referenced against CMS ownership tables). This flag was used to identify candidate facilities, which were then clustered by ownership chains and verified against public deal sources.

Three deals were ultimately included:

| Deal ID | REIT | Platform | Treat Year | Facilities |
|---------|------|----------|------------|------------|
| REIT001 | American Healthcare REIT | Trilogy | 2015 | 38 |
| REIT002 | Omega Healthcare Investors | Consulate / LaVie subset | 2019 | 25 |
| REIT003 | Welltower | Aurora / Complete Care (former Genesis subset) | 2021 | 18 |

### 2.2 Deal-specific verification methods

**REIT001 — American Healthcare REIT / Trilogy (2015)**  
Trilogy Health Services operated a large Indiana-based SNF chain. American Healthcare REIT (formerly Griffin-American Healthcare REIT) acquired a controlling interest in the Trilogy joint venture in 2015. Facilities were identified by matching the CMS `any_reit_owner` flag against Trilogy-branded facilities in the LTCFocus and CMS Provider of Services data. All 38 facilities in the Trilogy cluster with a clean pre-2015 non-REIT ownership record are included. Source group: `trilogy_2015_verified`.

**REIT002 — Omega Healthcare Investors / Consulate / LaVie (2019)**  
Omega Healthcare Investors is a publicly traded healthcare REIT that owns nursing home properties and leases them back to operators. Consulate Health Care was Omega's largest operator tenant; it rebranded as LaVie Care Centers in 2022. The treated facilities are the subset of Consulate/LaVie facilities whose CMS ownership chain shows Omega as a property owner from 2019 onward. Facilities were cross-referenced against the `omega_consulate_2019_event_window` deal workfile. Source group: `omega_consulate_2019_verified_subset`.

A related cluster (`fc_encore_2019_direct`) covers FC Encore properties that were part of the same Omega-linked lease structure in 2019. These are included in REIT002 under `platform_name = "FC Encore / Consulate"`.

**REIT003 — Welltower / Aurora / former Genesis subset (2021) — reverse engineered**  
This cohort required a non-standard approach. Welltower (formerly Health Care REIT) entered a sale-leaseback arrangement with Genesis HealthCare in 2011 covering a large portfolio of SNFs. However, many of those facilities were subsequently divested by Genesis in the 2015–2021 period as the company faced financial distress. By 2021, a subset of former Genesis/Welltower-linked facilities had been acquired by Aurora Health Network (operating as Complete Care Management), providing a clean post-period entry point.

Because the 2011 Welltower/Genesis deal pre-dates the LTCFocus data coverage used for identification, the cohort was reverse-engineered: starting from Aurora/Complete Care facilities visible in 2021 CMS data with a `any_reit_owner` flag, tracing ownership history back through the Genesis divestiture period, and confirming Welltower as the original REIT counterparty. The `treat_year` is coded as 2021 (the Aurora/Complete Care transition year visible in CMS data) rather than 2011. Source group: `welltower_aurora_2021_reverse_engineered`.

### 2.3 `reit_facility_verification.csv` column definitions

| Column | Type | Description |
|--------|------|-------------|
| `ccn` | string | CMS Certification Number |
| `facility_name` | string | Facility name as in CMS/LTCFocus |
| `state` | string | 2-letter state abbreviation |
| `deal_id` | string | REIT001, REIT002, or REIT003 |
| `reit_name` | string | Name of the REIT (American Healthcare REIT, Omega Healthcare Investors, Welltower) |
| `platform_name` | string | Operating platform or tenant chain associated with this REIT |
| `ownership_effective_date` | string | Date when REIT-linked ownership became visible in CMS data |
| `treat_year` | integer | Treatment year used in the analysis panel |
| `source_group` | categorical | Which verification workfile established this facility: `trilogy_2015_verified`, `omega_consulate_2019_verified_subset`, `fc_encore_2019_direct`, `welltower_aurora_2021_reverse_engineered` |
| `verification_tier` | categorical | `verified` (standard two-source confirmation) or `reverse_engineered` (REIT003 method described in §2.2) |
| `analysis_sample` | categorical | Always `reit_main` for included rows |
| `sample_role` | categorical | Always `treated` — no control facilities are listed in this file |
| `transition_type` | categorical | Always `non_reit_to_reit_or_reit_jv` — confirms pre-period was not REIT-controlled |

---

## Part III: Supporting Workfiles

The `research/verification/reit_ownership_investigation/` folder contains intermediate files from the REIT cluster identification process:

| File | Contents |
|------|----------|
| `reit_owner_clusters.csv` | Raw CMS ownership chains grouped into candidate REIT clusters |
| `reit_owner_cluster_public_verification.csv` | Cluster-level verification notes linking CMS entities to known REIT names |
| `reit_consecutive_homes_investigated.csv` | Facilities investigated for consecutive REIT-linked ownership spells |
| `reit_consecutive_homes_verified_public.csv` | Facilities from the above that passed public-source verification |
| `reit_consecutive_homes_chow_raw.csv` | Raw CHOW filing data for candidate REIT facilities |
| `reit_consecutive_homes_panel_raw.csv` | Raw panel data extracted for the REIT candidate set |

The `research/deal_workfiles/` folder contains event-window workfiles for each REIT deal and the REIT reverse-engineering exercise. Each subfolder documents the specific facilities, ownership timelines, and sources used to build that cohort.

---

## Part IV: Source Archiving Note

All source URLs in `pe_facility_verification.csv` (`source_platform_link`, `source_facility_link`) and `pe_acquisition_deals.csv` were live and accessible during the verification passes conducted in 2024–2025. Web sources are ephemeral; the following sources are especially at risk of link rot:

- **ProPublica Nursing Home Inspect** — facility pages (projects.propublica.org/nursing-homes) reflect current CMS data snapshots and are updated regularly; historical ownership displayed may change
- **CMS Care Compare** — provider pages are updated monthly; ownership history visible at verification time may not persist
- **California AG filings** — oag.ca.gov/node/... permalinks have been stable but are not guaranteed

To preserve the evidence underlying this treatment assignment, it is recommended to archive each source URL at [web.archive.org](https://web.archive.org) and note the archive date. The verification notes in `ownership_transition_verification_notes.md` describe what was found at each URL during the verification pass and serve as the primary documentary record.

---

## Part V: File Inventory

| File | Location | Tracked in git |
|------|----------|---------------|
| `pe_facility_verification.csv` | `research/treatment_inputs/` | ✅ |
| `reit_facility_verification.csv` | `research/treatment_inputs/` | ✅ |
| `pe_acquisition_deals.csv` | `research/treatment_inputs/` | ✅ |
| `pe_analysis_sample_summary.csv` | `research/treatment_inputs/` | ✅ |
| `pe_analysis_sample_qa.json` | `research/treatment_inputs/` | ✅ |
| `ownership_transition_verification_notes.md` | `research/verification/` | ✅ |
| `VERIFICATION_CODEBOOK.md` (this file) | `research/verification/` | ✅ |
| REIT investigation workfiles | `research/verification/reit_ownership_investigation/` | ✅ (except large raw CSVs) |
| Deal event-window workfiles | `research/deal_workfiles/` | ✅ (except cache/ subdirs) |
