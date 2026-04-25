# Welltower / Aurora Reverse-Engineered Subset

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

- Reverse-engineered facilities: 18
- LTCFocus rows in 2009-2013 panel: 85
