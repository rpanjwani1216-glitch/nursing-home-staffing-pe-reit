## Trilogy 2015 event-window extract

This folder contains a facility-year panel for the 38 Trilogy nursing homes
listed in rows 2-39 of
`research/reit_ownership_investigation/reit_consecutive_homes_investigated.csv`.

Files:
- `trilogy_2015_event_window_panel.csv`: one row per CCN-year for 2013-2017
- `trilogy_2015_event_window_coverage.csv`: year-by-year source coverage counts
- `trilogy_2015_event_window_summary.json`: machine-readable source metadata

Construction notes:
- Event time is defined relative to calendar year 2015 (`event_time = year - 2015`).
- LTCFocus now contributes staffing and rehospitalization covariates for
  2013-2017 after expanding the local LTCFocus ingest to include the newly added
  2011-2015 workbooks.
- CMS public archive data contribute annual provider/staffing ratings plus
  archived staffing-file HPRD values for 2013-2016 and provider/deficiency/
  survey-summary history for 2017.
- Official CMS archive source page:
  `https://www.cms.gov/medicare/health-safety-standards/quality-safety-oversight-general-information/five-star-quality-rating-system/five-star-quality-rating-system-archives`

Coverage for the 38-facility Trilogy cohort:
- 2013: LTCFocus staffing 19, CMS provider staffing 16, CMS staffing file 19,
  CMS deficiencies 18
- 2014: LTCFocus staffing 19, CMS provider staffing 19, CMS staffing file 20,
  CMS deficiencies 25
- 2015: LTCFocus staffing 19, CMS provider staffing 25, CMS staffing file 26,
  CMS deficiencies 31
- 2016: LTCFocus staffing 19, CMS provider staffing 25, CMS staffing file 30,
  CMS deficiencies 29
- 2017: LTCFocus staffing 19, CMS provider staffing 33, CMS deficiencies 33,
  CMS survey summary 33

Interpretation:
- A full balanced 38-facility panel is not available in the early pre-period
  because several of the Trilogy homes do not appear in the archived public
  sources until later years.
- Even so, the combined local-plus-archival data are sufficient to study a
  partial `t-2` to `t+2` window around the 2015 transaction with real staffing
  and health-inspection measures.
- Using any staffing source in the panel (LTCFocus, CMS provider snapshot, or
  CMS staffing archive), staffing is observable for 19 Trilogy homes in 2013,
  20 in 2014, 26 in 2015, 30 in 2016, and 33 in 2017.
- Using any health-inspection source in the panel (CMS deficiencies, survey
  ratings, or 2017 survey summary), health is observable for 20 Trilogy homes
  in 2013, 27 in 2014, 32 in 2015, 32 in 2016, and 33 in 2017.
- Nineteen Trilogy homes have a complete 2013-2017 staffing run from at least
  one staffing source, and 20 have a complete 2013-2017 health run.
