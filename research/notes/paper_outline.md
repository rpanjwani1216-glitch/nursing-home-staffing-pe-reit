# Paper Outline: PE & REIT Takeovers and Nursing Home Staffing

**Suggested title:** *"Financialized Ownership and Nursing Home Staffing: Evidence from Private Equity and REIT Acquisitions"*

---

## 1. Introduction (~800–1,000 words)

**Paragraph 1 — Hook / societal stakes.**
Nursing homes serve the most vulnerable elderly population. Staffing levels are the single most important determinant of care quality. CMS quality ratings, health inspection scores, and resident outcomes all correlate strongly with nurse hours per resident day (HPRD). Yet ownership structures in long-term care have shifted dramatically toward financialized forms — private equity (PE) and real estate investment trusts (REITs) — whose incentive structures may systematically differ from traditional non-profit or family operators.

**Paragraph 2 — The phenomenon.**
PE acquisitions of nursing homes grew rapidly through the 2000s and 2010s. REITs — which own the real estate underlying facilities while leasing to operators — are a related but distinct form of financialization that has received far less scrutiny. Both models prioritize financial returns, and both have been linked anecdotally to cost-cutting. But rigorous causal evidence is limited, particularly for REITs.

**Paragraph 3 — "In this paper, I..."**
> In this paper, I estimate the causal effect of PE and REIT ownership transitions on nursing home staffing using facility-level panel data from CMS and LTCFocus spanning 2009–2025. I construct a difference-in-differences (DiD) design comparing facilities that underwent a PE or REIT-linked ownership change to matched, same-state, and national control facilities that did not. My main outcome is total nurse hours per resident day (HPRD), with registered nurse (RN) HPRD as a secondary outcome. I document that PE acquisitions reduce total nurse HPRD by approximately 0.19 hours per resident day — roughly 5 percent from baseline — with effects concentrated among high-Medicaid facilities. REIT-linked transitions are associated with even larger reductions. Both effects grow over time following the ownership change, consistent with a gradual restructuring mechanism rather than an immediate shock.

**Paragraph 4 — Data.**
I use CMS Nursing Home Compare provider files and LTCFocus facility-year data, which together provide annual staffing, quality ratings, and facility characteristics from 2009 onward. Treatment timing comes from CMS change-of-ownership (CHOW) filings and verified deal-level PE and REIT transaction records.

**Paragraph 5 — Identification strategy.**
My identification relies on staggered DiD. I estimate a two-way fixed effects (TWFE) model with facility and year fixed effects, and supplement it with Callaway and Sant'Anna (2021) CSDID to address the Goodman-Bacon heterogeneous-treatment-timing critique. Pre-trend tests across all specifications find no evidence of differential pre-treatment trends, supporting the parallel trends assumption.

**Paragraph 6 — Results preview.**
PE ownership reduces total nurse HPRD by 0.19 hours (−5%) nationally, with consistent results in same-state and matched designs. Effects grow over two post-treatment years. Medicaid heterogeneity is strong: high-Medicaid facilities experience reductions roughly three times larger than low-Medicaid facilities (−0.33 vs. −0.03), consistent with a financial-pressure mechanism. REIT-linked transitions show directionally similar but larger staffing reductions, particularly in the matched design.

**Paragraph 7 — Contribution to literature.**
Cite and position relative to:
- Harrington et al. (2001, 2010) — foundational nursing home staffing and ownership work
- Grabowski et al. (2008) — for-profit vs. non-profit quality differences
- Braun et al. / Eliason et al. (2020, NBER) — PE and nursing home mortality, closest predecessor
- Gupta et al. (2021, JFE) — PE and nursing home quality (key paper to engage with)
- Singh (2016) / Feng et al. — REIT ownership and care quality
- Callaway & Sant'Anna (2021) — methodological anchor

Your contribution: (1) You study staffing directly rather than mortality, which is more proximate. (2) You provide the first systematic REIT comparison alongside PE. (3) You document Medicaid heterogeneity as a mechanism.

---

## 2. Data (~600–800 words)

**2.1 Data sources**
- CMS Nursing Home Compare: annual provider data, staffing ratings, health inspection ratings, quality measure ratings, facility characteristics (beds, chain affiliation, occupancy)
- LTCFocus: facility-year staffing panel — total nurse HPRD, RN HPRD; legacy (`dchrppd`) and PBJ-era (`dchprd_pbj`) columns coalesced
- PE treatment: CMS CHOW filings matched to verified PE deal records; gold + silver identification strategy (explain briefly what gold/silver means)
- REIT treatment: Three verified cohorts — AHR/Trilogy (2015), Omega/Consulate (2019), Welltower/Aurora (2021)

**2.2 Sample construction**
- Full national panel: 82,936 facility-year observations (PE); 141,529 (REIT)
- Same-state subsample: restricts controls to same state as treated facility
- Matched subsample: propensity-score matching on beds, occupancy, baseline direct-care HPRD, Medicaid share (PE: N=1,730; REIT: N=3,476)
- Treatment window: PE 2017–2025; REIT 2009–2023

**2.3 Summary statistics / balance table**
→ **Table 1: Baseline balance** — treated vs. control on beds, occupancy, RN HPRD, total nurse HPRD, Medicaid share, chain affiliation, health/overall ratings. Note that treated PE homes are slightly smaller and slightly higher-rated at baseline; matching addresses this.

**2.4 Outcome variables**
Define HPRD. Note the staffing column transition from legacy to PBJ-era columns and how you handle it.

---

## 3. Empirical Strategy (~700–900 words)

**3.1 Two-way fixed effects DiD**

$$\text{HPRD}_{it} = \alpha_i + \lambda_t + \beta \cdot \text{PostTakeover}_{it} + X_{it}'\gamma + \varepsilon_{it}$$

- $\alpha_i$: facility fixed effects (absorb time-invariant facility characteristics)
- $\lambda_t$: year fixed effects (absorb aggregate time trends)
- $\text{PostTakeover}_{it}$: indicator equal to 1 for treated facilities in post-ownership-change years
- $X_{it}$: time-varying controls (occupancy rate, chain status)
- Standard errors clustered at the facility level

Explain that this is estimated separately for national, same-state, and matched control samples. Explain the matched design briefly — linear propensity score matching, 3:1 ratio.

**3.2 Callaway–Sant'Anna CSDID**

Motivate: staggered treatment timing means TWFE β is a weighted average of heterogeneous group-time ATTs, and with treatment effect heterogeneity across cohorts, the weights can be negative (Goodman-Bacon 2021). CSDID estimates group-time average treatment effects and aggregates them cleanly.

Describe the pre-treatment reference group and the event-study window (Tm2 through Tp2+).

**3.3 Identification assumption**

Parallel trends: in the absence of PE/REIT takeover, treated and control facilities would have followed parallel staffing trends. Support: show pre-trend test results — pre-averages (Tm2, Tm1) insignificant and close to zero in all designs.

Discuss potential threats: selection into PE/REIT targets. Partially addressed by matching. Also note that PE/REIT acquisitions are often driven by portfolio-level financial strategy rather than facility-specific distress, which reduces concern about targeted selection on trends.

**3.4 Medicaid heterogeneity**

Tercile split on pre-treatment Medicaid share. Explain motivation: facilities with higher Medicaid census face lower reimbursement rates and may have more financial pressure to cut costs post-acquisition.

---

## 4. Results (~1,000–1,200 words)

**4.1 PE main staffing results**

Lead with: *Table 2 / Figure 1* — main FE DiD coefficients across national, same-state, matched.
- Total nurse HPRD: −0.194*** (national), −0.191*** (same-state), −0.121** (matched)
- RN HPRD: −0.067** (national), −0.075** (same-state), −0.050 (matched, insignificant)
- Discuss attenuation in matched design — expected given better covariate balance

*Figure 2* — CSDID event study (total nurse, national or same-state).
- Flat pre-period → growing negative post-period
- Tp2 largest effect (−0.296*** nationally)
- Discuss COVID 2020 spike honestly — transitory, doesn't confound the trend

**4.2 PE Medicaid heterogeneity**

*Figure 3 / Table 3* — tercile FE DiD.
- Low Medicaid: insignificant
- Middle: −0.185***
- High: −0.326***
- Frame as: PE cost-cutting is concentrated where facilities have least pricing power (captive Medicaid census, lower reimbursement)

Briefly show the descriptive scatter (*Figure 4* — baseline Medicaid share vs. staffing change) as visual support.

**4.3 Quality outcomes**

Present briefly: health inspection rating falls (−0.43*** nationally), overall rating falls (−0.37**), quality measure rating null. Note the health inspection result is consistent with staffing reductions — fewer nurses → more deficiencies cited.

**4.4 REIT extension**

Frame this subsection clearly as an extension.

*Table 4 / Figure 5* — REIT main FE DiD.
- Direct-care HPRD: −0.496*** (national), −0.381*** (matched)
- Discuss the larger magnitude — 62 treated facilities, heterogeneous deals, interpret cautiously
- Matched result most credible given deal heterogeneity

*Figure 6* — REIT event study (direct-care, matched design is cleanest to show).

**4.5 REIT Medicaid heterogeneity**

Present the tercile pattern (inverted relative to PE — low Medicaid hit hardest). Explain the deal composition confound explicitly: REIT001 (Trilogy) loads into low-Medicaid tercile. Present as exploratory.

---

## 5. Conclusion (~400–500 words)

- Restate: PE takeovers reduce total nurse HPRD by ~5%, concentrated in high-Medicaid facilities, growing over two years post-acquisition
- REIT-linked transitions show directionally consistent but larger effects, warranting further investigation
- Broader implication: financialized ownership imposes real costs on nursing home residents, and those costs fall disproportionately on facilities serving Medicaid-dependent populations — the most vulnerable
- Policy angle: CMS staffing minimum rules (2024 proposed rule), CHOW transparency, REIT disclosure requirements
- Limitations: identification relies on parallel trends which cannot be proven; REIT sample is small; pooled REIT estimates bundle heterogeneous transactions
- Future work: mortality outcomes, within-chain spillovers, operator-level analysis

---

## Tables and Figures Placement

| # | Item | Source file | Section |
|---|---|---|---|
| Table 1 | Baseline balance | balance table in outputs | §2 |
| Table 2 | PE main FE DiD (total nurse + RN) | `staffing_main_total_nurse_gold_plus_silver` | §4.1 |
| Table 3 | PE Medicaid tercile FE DiD | `staffing_medicaid_terciles_total_nurse_gold_plus_silver` | §4.2 |
| Table 4 | REIT main FE DiD | `reit_staffing_main_directcare` | §4.4 |
| Figure 1 | PE main coefficient plot | `paper_main_staffing_coefficients_gold_plus_silver_clean` | §4.1 |
| Figure 2 | PE CSDID event study (total nurse) | `csdid_event_total_nurse_gold_plus_silver_v2_same_state` | §4.1 |
| Figure 3 | PE Medicaid tercile FE DiD | `paper_medicaid_terciles_total_nurse_gold_plus_silver_combined` | §4.2 |
| Figure 4 | Descriptive Medicaid scatter | `paper_baseline_medicaid_vs_staffing_change_gold_plus_silver` | §4.2 |
| Figure 5 | REIT main coefficient plot | `paper_main_staffing_coefficients_reit_clean` | §4.4 |
| Figure 6 | REIT CSDID event study (matched) | `csdid_event_directcare_reit_v2_same_state_matched` | §4.4 |
| Appendix A | PE CSDID national + matched event studies | remaining csdid figures | Appendix |
| Appendix B | REIT Medicaid tercile FE DiD | `paper_medicaid_terciles_directcare_reit_combined` | Appendix |
| Appendix C | Medicaid functional form summary | `paper_medicaid_functional_form_summary_gold_plus_silver` | Appendix |
