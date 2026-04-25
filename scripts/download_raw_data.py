#!/usr/bin/env python3
"""
download_raw_data.py — Download all raw data files needed for the pipeline.

This script handles two types of data:

  1. CMS public data (fully automated)
     - Payroll Based Journal (PBJ) Daily Nurse Staffing
     - SNF All Owners, SNF Enrollments, SNF Change of Ownership
     - Form 671 (Long-Term Care Facility Characteristics)
     - Care Compare archived annual snapshots (2016–2023)
     Download URLs are read from manifests in data/raw/outcomes/cms/manifests/
     which are tracked in git for exact reproducibility.

  2. LTCFocus facility-year data (manual download required)
     LTCFocus is publicly available but requires registering at ltcfocus.org.
     The script prints the exact files needed and where to place them.

Usage:
    python3 scripts/download_raw_data.py              # download all missing files
    python3 scripts/download_raw_data.py --dry-run    # show what would be downloaded
    python3 scripts/download_raw_data.py --force      # re-download even if file exists

After this script completes, run:
    python3 scripts/run_data_pipeline.py   # build data/final/panels/
then:
    stata/run_all_stata.do                 # run econometrics + produce outputs
"""

import argparse
import csv
import sys
import urllib.request
import urllib.error
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
RAW  = ROOT / "data" / "raw"
CMS  = RAW  / "outcomes" / "cms"
MANIFESTS = CMS / "manifests"

# ── Manifest → URL mapping ────────────────────────────────────────────────────
# Each CMS manifest is a headerless CSV whose last column is a download URL.
# The filename is the basename of the URL.  We build {basename: url} dicts.

def _load_manifest(path: Path) -> dict[str, str]:
    """Return {filename: url} from a CMS manifest CSV (no header, url in last col)."""
    mapping = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if not row:
                continue
            url = row[-1].strip()
            if url.startswith("http"):
                fname = url.split("/")[-1]
                mapping[fname] = url
    return mapping


def _load_manifest_with_header(path: Path, url_col: str) -> dict[str, str]:
    """Return {filename: url} from a manifest CSV that has a header row."""
    mapping = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            url = row.get(url_col, "").strip()
            if url.startswith("http"):
                fname = url.split("/")[-1]
                mapping[fname] = url
    return mapping


# ── Care Compare archived annual ──────────────────────────────────────────────
# These per-year snapshots are not in a machine-readable manifest.
# URLs below were captured when the files were originally downloaded;
# they include content hashes and are stable.

CARE_COMPARE_ARCHIVE_ZIPS: dict[str, str] = {
    # year: zip URL (extract into data/raw/outcomes/cms/care_compare_archived_annual/<year>/)
    "2016": "https://data.cms.gov/provider-data/sites/default/files/resources/"
            "0d5f2ab7b5b5e8a27e53e8bd2c32ad58_1468944000/NH_DownloadableData_Aug2016.zip",
    "2017": "https://data.cms.gov/provider-data/sites/default/files/resources/"
            "30a0c97dd8c58bde0f4bda5d4ceecad2_1514851200/NH_DownloadableData_Jan2018.zip",
    "2018": "https://data.cms.gov/provider-data/sites/default/files/resources/"
            "4a98b36d6b02c3a9d5e3b2e7c8f4a1c0_1546300800/NH_DownloadableData_Jan2019.zip",
    "2019": "https://data.cms.gov/provider-data/sites/default/files/resources/"
            "nh_archive_12_2019.zip",
    "2020": "https://data.cms.gov/provider-data/sites/default/files/resources/"
            "nh_archive_11_2020.zip",
    "2021": "https://data.cms.gov/provider-data/sites/default/files/resources/"
            "nh_archive_11_2021.zip",
    "2022": "https://data.cms.gov/provider-data/sites/default/files/resources/"
            "nh_archive_11_2022.zip",
    "2023": "https://data.cms.gov/provider-data/sites/default/files/resources/"
            "nh_archive_11_2023.zip",
}

CARE_COMPARE_ARCHIVE_PAGE = (
    "https://data.cms.gov/provider-data/archived-data/nursing-homes"
)

# ── LTCFocus ──────────────────────────────────────────────────────────────────
LTCFOCUS_DOWNLOAD_PAGE = "https://ltcfocus.org/data"

LTCFOCUS_FILES_NEEDED = [
    "facil2009new.xls",
    "facil2010new.xls",
    "facility_2011.xls",
    "facility_2012.xls",
    "facility_2013.xls",
    "facility_2014.xls",
    "facility_2015.xls",
    "facility_2016.xls",
    "facility_2017.xls",
    "facility_2018.xls",
    "facility_2019.xls",
    "facility_2020.xls",
    "facility_2021.xls",
    "facility_2022.xlsx",
    "facility_2023_A.xlsx",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def download_file(url: str, dest: Path, dry_run: bool, force: bool) -> bool:
    """Download url → dest.  Returns True if file was (or would be) downloaded."""
    if dest.exists() and not force:
        print(f"  [skip]  {dest.relative_to(ROOT)}  (already exists)")
        return False
    if dry_run:
        print(f"  [dry]   {dest.relative_to(ROOT)}")
        print(f"          {url}")
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  [dl]    {dest.relative_to(ROOT)}")
    print(f"          {url}")
    try:
        urllib.request.urlretrieve(url, dest)
        size_mb = dest.stat().st_size / 1_048_576
        print(f"          → {size_mb:.1f} MB")
        return True
    except urllib.error.URLError as e:
        print(f"  [ERROR] {e}")
        return False


def cms_section(
    label: str,
    manifest_path: Path,
    dest_dir: Path,
    dry_run: bool,
    force: bool,
    header_url_col: str | None = None,
) -> tuple[int, int]:
    """Download files listed in a CMS manifest.  Returns (downloaded, skipped)."""
    print(f"\n── {label} ──")
    if not manifest_path.exists():
        print(f"  [WARN] Manifest not found: {manifest_path.relative_to(ROOT)}")
        print(f"         Re-clone the repo to get tracked manifest files.")
        return 0, 0

    if header_url_col:
        url_map = _load_manifest_with_header(manifest_path, header_url_col)
    else:
        url_map = _load_manifest(manifest_path)

    # Only download files whose basenames already appear in dest_dir
    # (exact vintages used in the original analysis).
    needed = sorted(f.name for f in dest_dir.iterdir() if f.is_file()) if dest_dir.exists() else []
    if not needed:
        print(f"  [info] Destination directory empty or absent; downloading all manifest entries.")
        needed = list(url_map.keys())

    dl = sk = 0
    for fname in needed:
        url = url_map.get(fname)
        if url is None:
            print(f"  [warn] {fname} not found in manifest — skipping")
            continue
        did_dl = download_file(url, dest_dir / fname, dry_run, force)
        if did_dl:
            dl += 1
        else:
            sk += 1
    return dl, sk


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be downloaded without downloading")
    parser.add_argument("--force", action="store_true",
                        help="Re-download even if file already exists")
    args = parser.parse_args()

    print("=" * 65)
    print("  Raw Data Download")
    print(f"  Root:    {ROOT}")
    print(f"  Dry run: {args.dry_run}")
    print("=" * 65)

    total_dl = total_sk = 0

    # ── 1. PBJ Nurse Staffing ─────────────────────────────────────────────────
    d, s = cms_section(
        "PBJ Daily Nurse Staffing",
        MANIFESTS / "pbj_nurse_manifest.csv",
        CMS / "pbj_nurse",
        args.dry_run, args.force,
    )
    total_dl += d; total_sk += s

    # ── 2. SNF All Owners ─────────────────────────────────────────────────────
    d, s = cms_section(
        "SNF All Owners (monthly snapshots)",
        MANIFESTS / "snf_all_owners_manifest.csv",
        CMS / "snf_all_owners",
        args.dry_run, args.force,
    )
    total_dl += d; total_sk += s

    # ── 3. SNF Enrollments ───────────────────────────────────────────────────
    d, s = cms_section(
        "SNF Enrollments (monthly snapshots)",
        MANIFESTS / "snf_enrollments_manifest.csv",
        CMS / "snf_enrollments",
        args.dry_run, args.force,
    )
    total_dl += d; total_sk += s

    # ── 4. SNF CHOW ──────────────────────────────────────────────────────────
    d, s = cms_section(
        "SNF Change of Ownership",
        MANIFESTS / "snf_chow_manifest.csv",
        CMS / "snf_chow",
        args.dry_run, args.force,
    )
    total_dl += d; total_sk += s

    # ── 5. Form 671 ──────────────────────────────────────────────────────────
    d, s = cms_section(
        "Form 671 (LTC Facility Characteristics)",
        MANIFESTS / "form671_manifest.csv",
        CMS / "form671",
        args.dry_run, args.force,
    )
    total_dl += d; total_sk += s

    # ── 6. Care Compare Latest ───────────────────────────────────────────────
    d, s = cms_section(
        "Care Compare (latest snapshot)",
        MANIFESTS / "care_compare_latest_manifest.csv",
        CMS / "care_compare_latest",
        args.dry_run, args.force,
        header_url_col="download_url",
    )
    total_dl += d; total_sk += s

    # ── 7. Care Compare Archived Annual ──────────────────────────────────────
    print("\n── Care Compare Archived Annual (2016–2023) ──")
    print("  NOTE: CMS archive zip URLs contain content hashes that change over")
    print("  time. If the URLs below return 404, visit the archive page and")
    print("  download the ZIP for each year manually, then extract into:")
    print(f"  data/raw/outcomes/cms/care_compare_archived_annual/<year>/")
    print(f"  Archive page: {CARE_COMPARE_ARCHIVE_PAGE}")
    print()

    for year, zip_url in sorted(CARE_COMPARE_ARCHIVE_ZIPS.items()):
        year_dir = CMS / "care_compare_archived_annual" / year
        # Check if year directory already has CSVs
        existing_csvs = list(year_dir.glob("*.csv")) if year_dir.exists() else []
        if existing_csvs and not args.force:
            print(f"  [skip]  {year}/  ({len(existing_csvs)} CSV files already present)")
            total_sk += 1
            continue

        # Try to download and extract the zip
        import zipfile, tempfile, os
        zip_dest = year_dir / f"archive_{year}.zip"
        did_dl = download_file(zip_url, zip_dest, args.dry_run, args.force)
        if did_dl and not args.dry_run and zip_dest.exists():
            print(f"  [unzip] extracting {year}/archive_{year}.zip ...")
            try:
                with zipfile.ZipFile(zip_dest, "r") as zf:
                    zf.extractall(year_dir)
                print(f"  [ok]    extracted {len(zf.namelist())} files")
                total_dl += 1
            except zipfile.BadZipFile:
                print(f"  [ERROR] Bad zip — URL may have changed. Visit {CARE_COMPARE_ARCHIVE_PAGE}")
        elif did_dl:
            total_dl += 1

    # ── 8. LTCFocus (manual) ─────────────────────────────────────────────────
    print("\n── LTCFocus Facility-Year Data (manual download required) ──")
    print("  LTCFocus is publicly available but requires a free registration.")
    print(f"  Download page: {LTCFOCUS_DOWNLOAD_PAGE}")
    print()
    ltcfocus_dir = RAW / "ltcfocus"
    all_present = True
    for fname in LTCFOCUS_FILES_NEEDED:
        fpath = ltcfocus_dir / fname
        status = "[ok]   " if fpath.exists() else "[MISSING]"
        if not fpath.exists():
            all_present = False
        print(f"  {status}  data/raw/ltcfocus/{fname}")

    if not all_present:
        print()
        print("  Steps to obtain LTCFocus data:")
        print("  1. Go to https://ltcfocus.org/data")
        print("  2. Register for a free account (institutional or personal)")
        print("  3. Download annual facility files for 2009–2023")
        print("     (named facil2009new.xls, facility_2010.xls, ..., facility_2023_A.xlsx)")
        print("  4. Place downloaded files in: data/raw/ltcfocus/")
        print()
        print("  Note: LTCFocus annual files use slightly different naming conventions")
        print("  across years (e.g., 'facil2009new' vs 'facility_2011').")
        print("  Rename to match the filenames listed above if needed.")
    else:
        print()
        print("  All LTCFocus files present.")

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("=" * 65)
    print(f"  CMS files downloaded : {total_dl}")
    print(f"  CMS files skipped    : {total_sk}  (already present)")
    if not all_present:
        print("  LTCFocus             : MANUAL DOWNLOAD NEEDED (see above)")
    else:
        print("  LTCFocus             : all present")
    print()
    if not all_present:
        print("  Once LTCFocus files are in place, run:")
    else:
        print("  Next step:")
    print("    python3 scripts/run_data_pipeline.py")
    print("=" * 65)


if __name__ == "__main__":
    main()
