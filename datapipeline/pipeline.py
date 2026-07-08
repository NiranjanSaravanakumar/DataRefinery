"""
BB DataRefinery — Core ETL Pipeline
=====================================

Implements a single-pass CSV ETL workflow:
  1. Extract  — read raw CSV rows into Python dicts
  2. Validate — check each row against 9 validation rules
  3. Transform — enrich accepted rows with computed fields
  4. Load      — write three structured output files

Design decisions:
- All logic lives in pure, standalone functions (no class state).
- `decimal.Decimal` is used for all financial math to avoid float rounding.
- `dataclass(frozen=True)` is used for output containers — immutable by design.
- Rows with ANY high-severity issue are rejected before transformation.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------------
# Constants — validation whitelists and alias maps
# ---------------------------------------------------------------------------

# All CSV columns that must be present and non-blank for a row to be accepted.
REQUIRED_FIELDS = [
    "order_id",
    "customer_id",
    "order_date",
    "ship_date",
    "region",
    "category",
    "quantity",
    "unit_price",
    "status",
]

# Maps lowercase status values (from raw data) → canonical display strings.
# Any status not in this dict is treated as invalid (high-severity issue).
VALID_STATUSES = {
    "delivered": "Delivered",
    "shipped": "Shipped",
    "processing": "Processing",
    "cancelled": "Cancelled",
    "returned": "Returned",
}

# Maps common region abbreviations and alternate spellings → canonical names.
# Lookup is always done after .strip().lower(), so case is irrelevant.
REGION_ALIASES = {
    "northeast": "Northeast",
    "north east": "Northeast",
    "ne": "Northeast",
    "southeast": "Southeast",
    "south east": "Southeast",
    "se": "Southeast",
    "midwest": "Midwest",
    "west": "West",
}


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PipelineIssue:
    """
    Represents a single validation failure found during pipeline processing.

    Attributes:
        row_number: The CSV row number where the issue was found (2-indexed;
                    row 1 is the header, so data rows start at 2).
        order_id:   The order ID on that row, or "UNKNOWN" if the field is blank.
        field:      The column name that failed validation.
        severity:   "high" causes the row to be rejected; "medium" is a warning.
        message:    A human-readable description of what went wrong.
    """
    row_number: int
    order_id: str
    field: str
    severity: str
    message: str


@dataclass(frozen=True)
class PipelineResult:
    """
    The immutable result object returned by `run_pipeline()`.

    Attributes:
        cleaned_rows: List of accepted, transformed row dicts ready for export.
        issues:       List of every PipelineIssue found across all rows.
        summary:      Dict of aggregate metrics (revenue, scores, status counts, etc.).
    """
    cleaned_rows: list[dict[str, str]]
    issues: list[PipelineIssue]
    summary: dict[str, object]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_pipeline(input_path: Path) -> PipelineResult:
    """
    Execute the full ETL pipeline against a raw CSV file.

    Reads every row, applies validation rules, transforms accepted rows,
    computes summary metrics, and returns a PipelineResult.

    Args:
        input_path: Path to the raw CSV input file.

    Returns:
        A PipelineResult containing cleaned rows, all issues, and a summary dict.
    """
    rows = _read_csv(input_path)

    # Track seen order IDs within this file to detect duplicates.
    seen_order_ids: set[str] = set()

    cleaned_rows: list[dict[str, str]] = []
    issues: list[PipelineIssue] = []

    # Enumerate starting at 2 because row 1 is the CSV header.
    for index, row in enumerate(rows, start=2):
        order_id = row.get("order_id", "").strip()
        row_issues: list[PipelineIssue] = []

        # ── Rule 1: Required field presence ───────────────────────────────
        for field in REQUIRED_FIELDS:
            if not row.get(field, "").strip():
                row_issues.append(_issue(index, order_id, field, "high", f"{field} is required."))

        # ── Rule 2: Duplicate order ID detection ──────────────────────────
        if order_id:
            if order_id in seen_order_ids:
                row_issues.append(_issue(index, order_id, "order_id", "high", "Duplicate order ID found."))
            seen_order_ids.add(order_id)

        # ── Rules 3–4: Date format and logical consistency ─────────────────
        # _parse_date() returns None for any value that isn't a valid YYYY-MM-DD.
        order_date = _parse_date(row.get("order_date", ""))
        ship_date = _parse_date(row.get("ship_date", ""))

        if row.get("order_date") and order_date is None:
            row_issues.append(_issue(index, order_id, "order_date", "high", "Order date is not a valid YYYY-MM-DD date."))
        if row.get("ship_date") and ship_date is None:
            row_issues.append(_issue(index, order_id, "ship_date", "high", "Ship date is not a valid YYYY-MM-DD date."))
        if order_date and ship_date and ship_date < order_date:
            # A ship date before the order date is logically impossible.
            row_issues.append(_issue(index, order_id, "ship_date", "high", "Ship date occurs before order date."))

        # ── Rules 5–6: Numeric range validation ───────────────────────────
        quantity = _parse_decimal(row.get("quantity", ""))
        unit_price = _parse_decimal(row.get("unit_price", ""))

        if row.get("quantity") and (quantity is None or quantity <= 0):
            row_issues.append(_issue(index, order_id, "quantity", "high", "Quantity must be greater than zero."))
        if row.get("unit_price") and (unit_price is None or unit_price <= 0):
            row_issues.append(_issue(index, order_id, "unit_price", "high", "Unit price must be greater than zero."))

        # ── Rule 7: Status whitelist validation ───────────────────────────
        status = _clean_status(row.get("status", ""))
        if row.get("status") and status is None:
            row_issues.append(_issue(index, order_id, "status", "high", "Status is outside the expected values."))

        # ── Rule 8: Region alias resolution (medium — row is kept) ────────
        region = _clean_region(row.get("region", ""))
        if row.get("region") and region is None:
            row_issues.append(_issue(index, order_id, "region", "medium", "Region could not be standardized."))

        # Accumulate all issues for this row into the master list.
        issues.extend(row_issues)

        # Only transform and accept the row if it has NO high-severity issues.
        if not any(issue.severity == "high" for issue in row_issues):
            cleaned_rows.append(
                _transform_row(
                    row=row,
                    order_date=order_date,
                    ship_date=ship_date,
                    quantity=quantity,
                    unit_price=unit_price,
                    status=status,
                    region=region,
                )
            )

    return PipelineResult(
        cleaned_rows=cleaned_rows,
        issues=issues,
        summary=_build_summary(rows, cleaned_rows, issues),
    )


def write_reports(result: PipelineResult, output_dir: Path) -> None:
    """
    Write the three pipeline output files to the given directory.

    Creates the directory (and any parents) if it does not already exist.

    Args:
        result:     The PipelineResult returned by run_pipeline().
        output_dir: Directory where the three output files will be written.

    Output files:
        clean_orders.csv       — Accepted, transformed records.
        pipeline_issues.csv    — All validation failures with row references.
        pipeline_summary.json  — Aggregate metrics for the entire run.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_clean_orders(result.cleaned_rows, output_dir / "clean_orders.csv")
    _write_issues(result.issues, output_dir / "pipeline_issues.csv")
    (output_dir / "pipeline_summary.json").write_text(
        json.dumps(result.summary, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Private helpers — Extract
# ---------------------------------------------------------------------------

def _read_csv(path: Path) -> list[dict[str, str]]:
    """
    Read a CSV file and return all rows as a list of dicts.

    Uses csv.DictReader so each row is keyed by the header column name.
    Opens with newline="" as required by the csv module to avoid
    platform-specific newline translation issues.

    Args:
        path: Path to the CSV file.

    Returns:
        List of row dicts. Empty list if the file contains only a header.
    """
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


# ---------------------------------------------------------------------------
# Private helpers — Validation
# ---------------------------------------------------------------------------

def _issue(row_number: int, order_id: str, field: str, severity: str, message: str) -> PipelineIssue:
    """
    Convenience constructor for PipelineIssue.

    Replaces a blank order_id with the string "UNKNOWN" so that every
    issue record is always identifiable in the output report.

    Args:
        row_number: CSV row number (2-indexed).
        order_id:   The order ID from that row (may be empty string).
        field:      Column name that caused the issue.
        severity:   "high" or "medium".
        message:    Human-readable description of the problem.

    Returns:
        A new PipelineIssue instance.
    """
    return PipelineIssue(
        row_number=row_number,
        order_id=order_id or "UNKNOWN",
        field=field,
        severity=severity,
        message=message,
    )


def _parse_date(value: str) -> date | None:
    """
    Parse a date string in YYYY-MM-DD format.

    Args:
        value: Raw string from the CSV cell (may contain whitespace).

    Returns:
        A `datetime.date` object if valid, otherwise None.
    """
    value = value.strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        # Any format that doesn't match YYYY-MM-DD (e.g. "not-a-date") returns None.
        return None


def _parse_decimal(value: str) -> Decimal | None:
    """
    Parse a numeric string into a Decimal, stripping currency symbols.

    Strips leading/trailing whitespace and removes '$' characters so that
    values like "$129.00" and "129.00" are both parsed correctly.

    Args:
        value: Raw string from the CSV cell.

    Returns:
        A `decimal.Decimal` if the value is a valid number, otherwise None.
    """
    value = value.strip().replace("$", "")
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _clean_status(value: str) -> str | None:
    """
    Map a raw status string to its canonical form using the VALID_STATUSES whitelist.

    The lookup is case-insensitive (always lower-cased before lookup).

    Args:
        value: Raw status string from the CSV cell.

    Returns:
        The canonical status string (e.g. "Delivered"), or None if not found.
    """
    return VALID_STATUSES.get(value.strip().lower())


def _clean_region(value: str) -> str | None:
    """
    Map a raw region string to its canonical form using the REGION_ALIASES dict.

    Accepts abbreviations (NE, SE), alternate spellings (North East), and
    the canonical name itself (Northeast). The lookup is case-insensitive.

    Args:
        value: Raw region string from the CSV cell.

    Returns:
        The canonical region name (e.g. "Northeast"), or None if not found.
    """
    return REGION_ALIASES.get(value.strip().lower())


# ---------------------------------------------------------------------------
# Private helpers — Transform
# ---------------------------------------------------------------------------

def _transform_row(
    row: dict[str, str],
    order_date: date | None,
    ship_date: date | None,
    quantity: Decimal | None,
    unit_price: Decimal | None,
    status: str | None,
    region: str | None,
) -> dict[str, str]:
    """
    Enrich a validated row with standardised values and computed fields.

    This function is only called for rows that passed all high-severity
    validation checks, so all critical fields are guaranteed to be present
    and valid. Defaults guard against the rare edge case where a medium-only
    issue left a field blank.

    Args:
        row:        The raw dict of CSV field values.
        order_date: Parsed order date (guaranteed non-None for accepted rows).
        ship_date:  Parsed ship date (guaranteed non-None for accepted rows).
        quantity:   Parsed quantity as Decimal.
        unit_price: Parsed unit price as Decimal.
        status:     Canonical status string, or None if only a medium issue.
        region:     Canonical region string, or None if unrecognised.

    Returns:
        A dict of cleaned, standardised, and enriched string values suitable
        for writing directly to the output CSV.
    """
    # Fall back to zero only if parsing somehow failed (medium-severity rows).
    quantity = quantity or Decimal("0")
    unit_price = unit_price or Decimal("0")

    # Revenue: the key business metric derived from each order.
    revenue = quantity * unit_price

    # Fulfillment time: how many calendar days from order to shipment.
    # Empty string is used (not zero) so that missing dates are distinguishable.
    fulfillment_days = (ship_date - order_date).days if order_date and ship_date else ""

    return {
        "order_id": row.get("order_id", "").strip(),
        # Uppercase for consistent customer ID lookups in downstream systems.
        "customer_id": row.get("customer_id", "").strip().upper(),
        # ISO 8601 format ensures universal date interoperability.
        "order_date": order_date.isoformat() if order_date else "",
        "ship_date": ship_date.isoformat() if ship_date else "",
        "fulfillment_days": str(fulfillment_days),
        # If region alias resolution succeeded, use the canonical name.
        # Otherwise, keep the original value (it had only a medium issue).
        "region": region or row.get("region", "").strip(),
        # Title-case normalises "cloud services" → "Cloud Services".
        "category": row.get("category", "").strip().title(),
        "quantity": str(int(quantity)),
        "unit_price": f"{unit_price:.2f}",
        "revenue": f"{revenue:.2f}",
        # Canonical status from whitelist, or title-cased original if medium-only.
        "status": status or row.get("status", "").strip().title(),
        # Priority lane marks high-value or time-sensitive orders for expedited handling.
        "priority_lane": "Yes" if revenue >= Decimal("500") or status == "Processing" else "No",
    }


# ---------------------------------------------------------------------------
# Private helpers — Summarise
# ---------------------------------------------------------------------------

def _build_summary(
    raw_rows: list[dict[str, str]],
    cleaned_rows: list[dict[str, str]],
    issues: list[PipelineIssue],
) -> dict[str, object]:
    """
    Compute aggregate metrics for the entire pipeline run.

    Args:
        raw_rows:     All rows read from the input CSV (before validation).
        cleaned_rows: All accepted, transformed rows.
        issues:       All PipelineIssue objects collected during the run.

    Returns:
        A dict suitable for JSON serialisation containing counts, revenue
        breakdowns, status distributions, top issue fields, and a pipeline score.
    """
    # Sum revenue across all accepted rows. Uses Decimal for exact arithmetic.
    total_revenue = sum(Decimal(row["revenue"]) for row in cleaned_rows) if cleaned_rows else Decimal("0")

    # Count issues grouped by field name and by severity level.
    issue_fields = _count_by((issue.field for issue in issues))
    severity_counts = _count_by((issue.severity for issue in issues))

    # Revenue and order count per region and per status.
    revenue_by_region: dict[str, Decimal] = {}
    status_counts: dict[str, int] = {}
    for row in cleaned_rows:
        revenue_by_region[row["region"]] = (
            revenue_by_region.get(row["region"], Decimal("0")) + Decimal(row["revenue"])
        )
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1

    # Pipeline score: starts at 100, deducted for each issue.
    # High-severity issues carry an extra 5-point penalty on top of the base 4-point deduction.
    issue_penalty = len(issues) * 4 + severity_counts.get("high", 0) * 5
    pipeline_score = max(0, min(100, 100 - issue_penalty))

    return {
        "rows_processed": len(raw_rows),
        "clean_records": len(cleaned_rows),
        "rejected_records": len(raw_rows) - len(cleaned_rows),
        "issues_found": len(issues),
        "high_severity_issues": severity_counts.get("high", 0),
        "pipeline_score": pipeline_score,
        "total_revenue": f"{total_revenue:.2f}",
        # Sorted alphabetically for deterministic, diffable output.
        "revenue_by_region": {key: f"{value:.2f}" for key, value in sorted(revenue_by_region.items())},
        "status_counts": dict(sorted(status_counts.items())),
        # Top 5 fields most frequently causing issues — useful for targeted data quality improvements.
        "top_issue_fields": dict(sorted(issue_fields.items(), key=lambda item: item[1], reverse=True)[:5]),
    }


def _count_by(values: Iterable[str]) -> dict[str, int]:
    """
    Count occurrences of each unique value in an iterable.

    Equivalent to `collections.Counter` but avoids importing that module.

    Args:
        values: Any iterable of strings.

    Returns:
        A dict mapping each unique string to its occurrence count.
    """
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Private helpers — Load (write outputs)
# ---------------------------------------------------------------------------

def _write_clean_orders(rows: list[dict[str, str]], path: Path) -> None:
    """
    Write accepted, transformed order rows to a CSV file.

    If there are no clean rows (e.g. every row was rejected), writes an
    empty file rather than failing or raising an exception.

    Args:
        rows: List of transformed row dicts to write.
        path: Destination file path.
    """
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", newline="", encoding="utf-8") as csv_file:
        # Use the keys of the first row as the column headers.
        # This preserves the output column order defined in _transform_row().
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_issues(issues: list[PipelineIssue], path: Path) -> None:
    """
    Write all pipeline validation issues to a CSV file.

    Writes a header row even if there are no issues, so downstream tools
    always receive a consistently structured file.

    Args:
        issues: List of PipelineIssue objects to write.
        path:   Destination file path.
    """
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["row_number", "order_id", "field", "severity", "message"],
        )
        writer.writeheader()
        for issue in issues:
            writer.writerow(
                {
                    "row_number": issue.row_number,
                    "order_id": issue.order_id,
                    "field": issue.field,
                    "severity": issue.severity,
                    "message": issue.message,
                }
            )
