# Python Scripts

The Python entrypoints stay flat in this folder so they can be run directly
without import-path surprises. Their outputs are organized elsewhere.

Main groups:

- treatment research
  - `build_pe_treatment_dataset.py`
- CMS raw-to-intermediate builds
  - `build_cms_foundation_panel.py`
  - `refresh_cms_deficiency_history.py`
  - `refresh_cms_provider_history.py`
- LTCFocus and controls
  - `build_ltcfocus_intermediates.py`
  - `build_control_candidate_pools.py`
- treated and analysis panels
  - `build_treated_sample_panels.py`
  - `build_regression_analysis_panel.py`
  - `build_regression_analysis_panel_same_state.py`
  - `build_matched_control_panel.py`
- descriptive / diagnostics helpers
  - `evaluate_matched_control_variants.py`
  - `export_table1_baseline_formats.py`
- pipeline wrapper
  - `run_data_pipeline.py`
