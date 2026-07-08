"""
DataRefinery — Cleaning Service
==================================
Wraps the core ETL pipeline (datapipeline.pipeline.run_pipeline) into
a service layer that provides enriched web-friendly metadata alongside
the pipeline result.

This module is the only bridge between the Flask application and the
core ETL logic. The pipeline itself is NOT modified.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from datapipeline.pipeline import PipelineResult, run_pipeline, write_reports


class CleaningService:
    """
    Service layer that orchestrates the ETL pipeline for web requests.

    Calls run_pipeline(), writes output files to the session directory,
    and builds a rich web_summary dict that the UI consumes.
    """

    def process(self, input_path: Path, output_dir: Path) -> dict[str, Any]:
        """
        Run the full pipeline on the given CSV file and write outputs.

        Args:
            input_path: Path to the uploaded CSV.
            output_dir:  Session directory where output files will be written.

        Returns:
            A dict containing all data needed to render the result page.

        Raises:
            ValueError: If the file cannot be read as CSV.
            Exception:  Propagates any pipeline error to the caller.
        """
        # --- Capture raw file metadata before pipeline runs ---
        raw_rows, raw_columns = self._probe_csv(input_path)

        # --- Run the core ETL pipeline (unchanged from original) ---
        result: PipelineResult = run_pipeline(input_path)

        # --- Write the three standard output files ---
        write_reports(result, output_dir)

        # --- Build enriched web summary ---
        return self._build_web_summary(
            result=result,
            input_path=input_path,
            raw_rows=raw_rows,
            raw_columns=raw_columns,
        )

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _probe_csv(self, path: Path) -> tuple[int, list[str]]:
        """
        Read the CSV header and count data rows without running the pipeline.

        Args:
            path: Path to the CSV file.

        Returns:
            Tuple of (row_count, column_names).
        """
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames or []
            row_count = sum(1 for _ in reader)
        return row_count, list(columns)

    def _build_web_summary(
        self,
        result: PipelineResult,
        input_path: Path,
        raw_rows: int,
        raw_columns: list[str],
    ) -> dict[str, Any]:
        """
        Combine PipelineResult data with web-specific metadata into a flat dict.

        Args:
            result:      The PipelineResult from run_pipeline().
            input_path:  Path to the uploaded CSV (for filename metadata).
            raw_rows:    Number of rows in the original CSV.
            raw_columns: Column names from the original CSV.

        Returns:
            A JSON-serializable dict for storage and template rendering.
        """
        summary = result.summary

        # Count missing values: any raw field that was blank before cleaning
        missing_found = sum(
            1 for issue in result.issues
            if "required" in issue.message.lower()
        )

        # Duplicate count
        duplicate_rows = sum(
            1 for issue in result.issues
            if "duplicate" in issue.message.lower()
        )

        # Columns that were modified by the pipeline
        modified_columns = list({
            issue.field for issue in result.issues
        })

        # Issues grouped by field for the UI table
        issues_by_field: dict[str, list[dict]] = {}
        for issue in result.issues:
            entry = {
                "row_number": issue.row_number,
                "order_id": issue.order_id,
                "severity": issue.severity,
                "message": issue.message,
            }
            issues_by_field.setdefault(issue.field, []).append(entry)

        # Output column count (may differ from input because pipeline adds computed fields)
        out_columns = list(result.cleaned_rows[0].keys()) if result.cleaned_rows else raw_columns

        # Revenue stats
        revenues = [Decimal(row["revenue"]) for row in result.cleaned_rows]
        avg_revenue = (sum(revenues) / len(revenues)) if revenues else Decimal("0")
        max_revenue = max(revenues) if revenues else Decimal("0")

        return {
            # ── Identity ─────────────────────────────────────────────────
            "filename": input_path.name,
            "timestamp": datetime.now(timezone.utc).isoformat(),

            # ── Before / After ───────────────────────────────────────────
            "rows_before": raw_rows,
            "cols_before": len(raw_columns),
            "columns_before": raw_columns,
            "rows_after": len(result.cleaned_rows),
            "cols_after": len(out_columns),
            "columns_after": out_columns,

            # ── Issues ───────────────────────────────────────────────────
            "missing_values_found": missing_found,
            "duplicate_rows_removed": duplicate_rows,
            "modified_columns": modified_columns,
            "total_issues": summary["issues_found"],
            "high_severity_issues": summary["high_severity_issues"],
            "medium_severity_issues": summary["issues_found"] - summary["high_severity_issues"],
            "issues_by_field": issues_by_field,

            # ── Pipeline metrics ─────────────────────────────────────────
            "pipeline_score": summary["pipeline_score"],
            "rejected_records": summary["rejected_records"],

            # ── Revenue stats ────────────────────────────────────────────
            "total_revenue": summary["total_revenue"],
            "avg_revenue": f"{avg_revenue:.2f}",
            "max_revenue": f"{max_revenue:.2f}",
            "revenue_by_region": summary["revenue_by_region"],
            "status_counts": summary["status_counts"],
            "top_issue_fields": summary["top_issue_fields"],

            # ── Full pipeline summary (for ZIP download) ─────────────────
            "pipeline_summary": summary,
        }
