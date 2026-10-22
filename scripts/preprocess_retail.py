#!/usr/bin/env python3
"""
Preprocess one complete month of UCI Online Retail II into ~100 top SKUs,
deterministic pick frequencies, actual order lines, and synthetic warehouse layout.

Citation: Chen, D. (2012), Online Retail II, DOI 10.24432/C5CG6D (CC BY 4.0)
Official workbook SHA256: bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980
"""
import argparse
import json
import os
from pathlib import Path
import sys

# Ensure repository root is on sys.path when executed directly
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.services.preprocessing import (
    EXPECTED_SHA256,
    UCI_PAGE_URL,
    UCI_DOWNLOAD_URL,
    EXCLUDED_NONPRODUCT_CODES,
    compute_sha256,
    validate_workbook_checksum,
    generate_synthetic_21x21_layout,
    preprocess_retail_month,
    preprocess_dataset,
)


def resolve_input_path(input_arg: str | None) -> tuple[Path | None, str]:
    """
    Resolve input workbook path from explicit argument, environment variable,
    or standard candidate locations in the repository.
    Returns (resolved_path, search_description).
    """
    if input_arg:
        p = Path(input_arg).expanduser()
        if p.is_file():
            return p, f"explicit argument '{input_arg}'"
        return None, f"specified path '{input_arg}'"

    # Check environment variable
    env_path = os.getenv("UCI_DATASET_PATH")
    if env_path:
        p = Path(env_path).expanduser()
        if p.is_file():
            return p, f"environment variable UCI_DATASET_PATH ('{env_path}')"
        return None, f"environment variable UCI_DATASET_PATH ('{env_path}')"

    # Check standard relative candidate locations
    candidates = [
        Path("datasets/online-retail-ii/online_retail_II.xlsx"),
        Path("datasets/online_retail_II.xlsx"),
        Path("data/online_retail_II.xlsx"),
        Path("online_retail_II.xlsx"),
    ]
    for c in candidates:
        if c.is_file():
            return c, f"standard repository path '{c}'"

    return None, "standard locations [datasets/, data/, ./online_retail_II.xlsx] or UCI_DATASET_PATH"


def print_missing_dataset_error(attempted_desc: str):
    """Print actionable error message with download instructions and SHA256 checksum."""
    msg = (
        f"Error: UCI Online Retail II dataset workbook not found via {attempted_desc}.\n\n"
        "To obtain the dataset:\n"
        "  1. Download online_retail_II.xlsx from the UCI Machine Learning Repository:\n"
        f"     {UCI_PAGE_URL}\n"
        f"     Direct download: {UCI_DOWNLOAD_URL}\n"
        f"  2. Expected SHA-256 checksum: {EXPECTED_SHA256}\n\n"
        "Usage:\n"
        "  python scripts/preprocess_retail.py --input /path/to/online_retail_II.xlsx\n"
        "Or set the environment variable:\n"
        "  export UCI_DATASET_PATH=/path/to/online_retail_II.xlsx\n"
    )
    print(msg, file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Preprocess UCI Online Retail II dataset")
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Path to online_retail_II.xlsx (default: checks UCI_DATASET_PATH and standard repo locations)",
    )
    parser.add_argument(
        "--allow-hash-mismatch",
        action="store_true",
        default=False,
        help="Allow processing even if workbook SHA-256 does not match official UCI checksum",
    )
    parser.add_argument("--sheet", type=str, default="Year 2010-2011")
    parser.add_argument("--month", type=str, default="2011-06")
    parser.add_argument("--top-skus", type=int, default=100)
    parser.add_argument("--orders", type=int, default=20)
    parser.add_argument(
        "--output-json",
        type=str,
        default="backend/app/data/demo.json",
        help="Output path for preprocessed demo JSON",
    )
    parser.add_argument(
        "--output-provenance",
        type=str,
        default="backend/app/data/demo-provenance.json",
        help="Output path for provenance JSON",
    )
    parser.add_argument(
        "--sync-frontend",
        action="store_true",
        default=True,
        help="Also write preprocessed outputs to frontend/public/ (default: True)",
    )
    parser.add_argument(
        "--no-sync-frontend",
        dest="sync_frontend",
        action="store_false",
        help="Do not copy preprocessed outputs to frontend/public/",
    )
    args = parser.parse_args()

    resolved_path, desc = resolve_input_path(args.input)
    if not resolved_path:
        print_missing_dataset_error(desc)
        sys.exit(1)

    print(f"Using dataset workbook from {desc}: {resolved_path}")

    demo, prov = preprocess_retail_month(
        filepath=str(resolved_path),
        sheet_name=args.sheet,
        target_month=args.month,
        num_top_skus=args.top_skus,
        num_demo_orders=args.orders,
        allow_hash_mismatch=args.allow_hash_mismatch,
    )

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(demo, f, separators=(",", ":"))
        f.write("\n")
    print(f"Wrote preprocessed snapshot to {out_json}")

    out_prov = Path(args.output_provenance)
    out_prov.parent.mkdir(parents=True, exist_ok=True)
    with open(out_prov, "w", encoding="utf-8") as f:
        json.dump(prov, f, indent=2)
        f.write("\n")
    print(f"Wrote provenance metadata to {out_prov}")

    if args.sync_frontend:
        frontend_json = Path("frontend/public/demo.json")
        frontend_prov = Path("frontend/public/demo-provenance.json")
        if frontend_json.parent.exists():
            with open(frontend_json, "w", encoding="utf-8") as f:
                json.dump(demo, f, separators=(",", ":"))
                f.write("\n")
            with open(frontend_prov, "w", encoding="utf-8") as f:
                json.dump(prov, f, indent=2)
                f.write("\n")
            print("Synchronized preprocessed files to frontend/public/")


if __name__ == "__main__":
    main()
