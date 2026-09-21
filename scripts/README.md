# Analysis support scripts

The scripts in `analysis/` post-process Stata results and render publication
tables. They do not download raw data or rebuild the analysis panels.

- `build_pe_support_outputs.py` prepares PE summary tables and plotting data.
- `build_reit_support_outputs.py` prepares REIT plotting data.
- `build_tables.py` renders selected LaTeX tables to PDF and PNG when
  `pdflatex` and `pdftoppm` are installed.

Run the complete workflow from the repository root with `bash run_all.sh`.
