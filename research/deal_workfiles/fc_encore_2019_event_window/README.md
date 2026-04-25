## FC Encore 2019 event-window extract

This folder contains a facility-year panel for the FC Encore cohort that appears
in the local REIT investigation file. In the current repo this cohort contains
two CCNs:
- `255260` `HILLTOP MANOR HEALTH AND REHABILITATION CENTER`
- `345258` `Kannapolis Health and Rehabilitation`

Files:
- `fc_encore_2019_event_window_panel.csv`: one row per CCN-year for 2017-2021
- `fc_encore_2019_event_window_coverage.csv`: year-by-year source coverage counts
- `fc_encore_2019_event_window_summary.json`: machine-readable metadata and source links

Construction notes:
- Event time is defined relative to calendar year 2019 (`event_time = year - 2019`).
- The panel combines LTCFocus, PBJ nurse staffing, Care Compare provider history,
  Care Compare health deficiencies, and Care Compare survey summary history.
- Because the deal window is later than the Trilogy case, PBJ is available for
  the full `t-2` to `t+2` period and is the strongest staffing source here.

Coverage for the two-facility FC Encore cohort:
- 2017: LTCFocus staffing 2, PBJ staffing 2, Care Compare staffing 1, health deficiencies 2, survey summary 2
- 2018: LTCFocus staffing 0, PBJ staffing 2, Care Compare staffing 2, health deficiencies 1, survey summary 1
- 2019: LTCFocus staffing 0, PBJ staffing 2, Care Compare staffing 2, health deficiencies 2, survey summary 2
- 2020: LTCFocus staffing 0, PBJ staffing 2, Care Compare staffing 2, health deficiencies 1, survey summary 0
- 2021: LTCFocus staffing 0, PBJ staffing 2, Care Compare staffing 2, health deficiencies 1, survey summary 0

Transaction references:
- Houlihan Lokey transaction page identifying `FC Encore, LP` as the seller:
  `https://hl.com/about-us/transactions/houlihan-lokey-advises-fc-encore/`
- Skilled Nursing News coverage describing Omega's closing of the Encore/Consulate deal:
  `https://skillednursingnews.com/2019/11/omega-closes-735m-skilled-nursing-deal-confirms-consulate-as-primary-operator/`
