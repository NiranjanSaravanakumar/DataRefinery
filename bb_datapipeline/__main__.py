"""Command line entry point for BB Data Pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import run_pipeline, write_reports


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the BB Data Pipeline ETL workflow.")
    parser.add_argument("--input", default="data/raw_orders.csv", help="Path to raw CSV order data.")
    parser.add_argument("--out", default="reports", help="Directory where reports should be written.")
    args = parser.parse_args()

    result = run_pipeline(Path(args.input))
    write_reports(result, Path(args.out))

    print(f"Processed {result.summary['rows_processed']} rows.")
    print(f"Clean records: {result.summary['clean_records']}")
    print(f"Issues found: {result.summary['issues_found']}")
    print(f"Pipeline score: {result.summary['pipeline_score']}/100")


if __name__ == "__main__":
    main()
