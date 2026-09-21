# Analysis-ready data

These six files are the direct inputs to the Stata replication workflow. CSV
is used as the published interchange format; `stata/0_prepare_analysis_data.do`
creates local `.dta` copies without modifying the tracked files.

| File | Design | Rows | Columns | Size (bytes) |
|---|---|---:|---:|---:|
| `pe_national.csv` | PE, national controls | 102,953 | 96 | 58,690,602 |
| `pe_same_state.csv` | PE, same-state controls | 33,095 | 96 | 19,678,332 |
| `pe_matched.csv` | PE, matched controls | 1,730 | 100 | 1,103,541 |
| `reit_national.csv` | REIT, national controls | 143,146 | 36 | 37,264,454 |
| `reit_same_state.csv` | REIT, same-state controls | 45,125 | 36 | 11,872,020 |
| `reit_matched.csv` | REIT, matched controls | 3,476 | 39 | 1,142,311 |

The same-state and matched samples are not interchangeable copies of the
national panels. The matched panels contain matching-specific fields and some
design-specific treatment/baseline values, so each file is retained explicitly.

## Core variables

- `ccn_str`, `year`: facility-year identifier
- `sample_role`: treated or control observation
- `analysis_spec`: control-design identifier
- `treat_year`, `post_treat`, `event_time`: treatment timing
- `sample_main_staffing`: primary staffing-analysis inclusion flag
- `baseline_medicaid_share`: pre-treatment Medicaid share
- `pbj_mean_nurse_hprd`, `pbj_mean_rn_hprd`: PE staffing outcomes
- `ltcfocus_directcare_hprd`, `ltcfocus_rn_hprd`: REIT staffing outcomes
- `provider_*_rating`: Care Compare rating outcomes in the PE panels

The PE panels contain 96 common columns; the matched PE panel adds
`chain_affiliated`, `for_profit`, `matched_sample`, and `treated_ever`. The REIT
panels contain 36 common columns; the matched REIT panel adds
`analysis_sample_label`, `matched_sample`, and `treated_ever`.

## Integrity checksums

SHA-256 values for the tracked CSV files:

```text
pe_matched.csv      7a339764cd664ad0ac33fe89081b37485c8d6f964e9a382a0c1913eecb66dd38
pe_national.csv     15d30d560b3fdce279951a17fa7f6346a2e7901f33f760a015237e7ec9c3637f
pe_same_state.csv   8920666ebb27d5c2042f6094df068b2076620b61393624d112b5cd3d85ad1291
reit_matched.csv    f33702286fb9f56748d1cf2189af4e83c55696828bc4d8ac5f639dd7a5a707f3
reit_national.csv   fd2b11117f8c6007117041d6a07b82d4151bd4bb26bb66bed1f2a12066f03ce2
reit_same_state.csv 014f0479aca1fb2a72982988fba87300603c7eacd160692aa4a0a0c304c4d7d5
```

## Required LTCFocus reference

> LTCFocus Public Use Data sponsored by the National Institute on Aging
> (P01 AG027296) through a cooperative agreement with the Brown University
> School of Public Health. Available at [www.ltcfocus.org](https://www.ltcfocus.org/).
> [https://doi.org/10.26300/h9a2-2c26](https://doi.org/10.26300/h9a2-2c26)
