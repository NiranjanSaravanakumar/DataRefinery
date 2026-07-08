"""
DataRefinery — Pipeline Unit Tests
=====================================
Tests for the core ETL pipeline (datapipeline/).
Covers all 9 validation rules, malformed input, multi-issue rows,
output file creation, and the no-revenue-totals contract.
"""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from datapipeline import run_pipeline
from datapipeline.pipeline import write_reports

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "raw_orders.csv"

# A valid base row — all 9 required fields present and correct.
HEADER = (
    "order_id,customer_id,order_date,ship_date,"
    "region,category,quantity,unit_price,status"
)
GOOD_ROW = "ORD-T01,c-001,2026-01-01,2026-01-03,northeast,software,2,100.00,delivered"


# ── Helper ─────────────────────────────────────────────────────────────────────


def _csv_path(*data_rows: str) -> Path:
    """Write a CSV temp file containing HEADER + given rows; return its Path."""
    content = HEADER + "\n" + "\n".join(data_rows)
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    )
    tmp.write(content)
    tmp.close()
    return Path(tmp.name)


# ── Integration tests (full sample file) ──────────────────────────────────────


class PipelineTests(unittest.TestCase):
    def test_pipeline_creates_summary(self):
        result = run_pipeline(DATA_PATH)

        self.assertEqual(result.summary["rows_processed"], 14)
        self.assertEqual(result.summary["clean_records"], 8)
        self.assertEqual(result.summary["rejected_records"], 6)
        self.assertEqual(result.summary["pipeline_score"], 46)

    def test_summary_has_no_revenue_totals(self):
        """total_revenue and revenue_by_region must not appear in the summary."""
        result = run_pipeline(DATA_PATH)
        self.assertNotIn("total_revenue", result.summary)
        self.assertNotIn("revenue_by_region", result.summary)

    def test_pipeline_standardizes_clean_records(self):
        result = run_pipeline(DATA_PATH)
        first_row = result.cleaned_rows[0]

        self.assertEqual(first_row["customer_id"], "C-224")
        self.assertEqual(first_row["region"], "Northeast")
        self.assertEqual(first_row["status"], "Delivered")
        self.assertEqual(first_row["revenue"], "258.00")

    def test_reports_are_written(self):
        result = run_pipeline(DATA_PATH)

        with tempfile.TemporaryDirectory() as tmp_dir:
            write_reports(result, Path(tmp_dir))

            self.assertTrue((Path(tmp_dir) / "clean_orders.csv").exists())
            self.assertTrue((Path(tmp_dir) / "pipeline_issues.csv").exists())
            self.assertTrue((Path(tmp_dir) / "pipeline_summary.json").exists())


# ── Rule-specific unit tests ───────────────────────────────────────────────────


class ValidationRuleTests(unittest.TestCase):
    """One test per validation rule (9 rules total)."""

    # Rule 1 — Missing required field
    def test_rule1_missing_required_field(self):
        path = _csv_path(
            "ORD-R1,,2026-01-01,2026-01-03,northeast,software,2,100.00,delivered"
        )
        result = run_pipeline(path)
        self.assertEqual(result.summary["clean_records"], 0)
        issues = [i for i in result.issues if i.field == "customer_id"]
        self.assertTrue(any(i.severity == "high" for i in issues))

    # Rule 2 — Duplicate order ID
    def test_rule2_duplicate_order_id(self):
        path = _csv_path(GOOD_ROW, GOOD_ROW)  # same order_id twice
        result = run_pipeline(path)
        dup_issues = [i for i in result.issues if "Duplicate" in i.message]
        self.assertEqual(len(dup_issues), 1)  # second occurrence rejected
        self.assertEqual(result.summary["clean_records"], 1)  # first copy accepted

    # Rule 3 — Invalid order_date format
    def test_rule3_invalid_order_date(self):
        path = _csv_path(
            "ORD-R3,c-001,not-a-date,2026-01-03,northeast,software,2,100.00,delivered"
        )
        result = run_pipeline(path)
        self.assertEqual(result.summary["clean_records"], 0)
        issues = [i for i in result.issues if i.field == "order_date"]
        self.assertTrue(any(i.severity == "high" for i in issues))

    # Rule 4 — Invalid ship_date format
    def test_rule4_invalid_ship_date(self):
        path = _csv_path(
            "ORD-R4,c-001,2026-01-01,99-99-99,northeast,software,2,100.00,delivered"
        )
        result = run_pipeline(path)
        self.assertEqual(result.summary["clean_records"], 0)
        issues = [i for i in result.issues if i.field == "ship_date"]
        self.assertTrue(any(i.severity == "high" for i in issues))

    # Rule 5 — Ship date before order date
    def test_rule5_ship_before_order(self):
        path = _csv_path(
            "ORD-R5,c-001,2026-06-01,2026-01-01,northeast,software,2,100.00,delivered"
        )
        result = run_pipeline(path)
        self.assertEqual(result.summary["clean_records"], 0)
        issues = [i for i in result.issues if "before order date" in i.message]
        self.assertTrue(len(issues) >= 1)

    # Rule 6 — Non-positive quantity
    def test_rule6_non_positive_quantity(self):
        path = _csv_path(
            "ORD-R6,c-001,2026-01-01,2026-01-03,northeast,software,0,100.00,delivered"
        )
        result = run_pipeline(path)
        self.assertEqual(result.summary["clean_records"], 0)
        issues = [i for i in result.issues if i.field == "quantity"]
        self.assertTrue(any(i.severity == "high" for i in issues))

    # Rule 7 — Non-positive unit price
    def test_rule7_non_positive_unit_price(self):
        path = _csv_path(
            "ORD-R7,c-001,2026-01-01,2026-01-03,northeast,software,2,-5.00,delivered"
        )
        result = run_pipeline(path)
        self.assertEqual(result.summary["clean_records"], 0)
        issues = [i for i in result.issues if i.field == "unit_price"]
        self.assertTrue(any(i.severity == "high" for i in issues))

    # Rule 8 — Invalid status
    def test_rule8_invalid_status(self):
        path = _csv_path(
            "ORD-R8,c-001,2026-01-01,2026-01-03,northeast,software,2,100.00,unknown_status"
        )
        result = run_pipeline(path)
        self.assertEqual(result.summary["clean_records"], 0)
        issues = [i for i in result.issues if i.field == "status"]
        self.assertTrue(any(i.severity == "high" for i in issues))

    # Rule 9 — Unrecognised region (medium severity — row is kept)
    def test_rule9_unrecognised_region_medium_severity(self):
        path = _csv_path(
            "ORD-R9,c-001,2026-01-01,2026-01-03,atlantis,software,2,100.00,delivered"
        )
        result = run_pipeline(path)
        # Row should be KEPT (medium severity only)
        self.assertEqual(result.summary["clean_records"], 1)
        region_issues = [i for i in result.issues if i.field == "region"]
        self.assertTrue(any(i.severity == "medium" for i in region_issues))


# ── Edge-case tests ────────────────────────────────────────────────────────────


class EdgeCaseTests(unittest.TestCase):
    """Tests for unusual inputs and multi-issue scenarios."""

    def test_malformed_csv_wrong_delimiter(self):
        """A semicolon-delimited file should produce no clean records."""
        content = "order_id;customer_id;order_date;ship_date;region;category;quantity;unit_price;status\n"
        content += "ORD-SC1;c-001;2026-01-01;2026-01-03;northeast;software;2;100.00;delivered\n"
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        )
        tmp.write(content)
        tmp.close()
        # The pipeline will treat the whole semicolon-delimited row as a single
        # un-parseable blob — all required fields will be missing.
        result = run_pipeline(Path(tmp.name))
        self.assertEqual(result.summary["clean_records"], 0)

    def test_extra_columns_are_ignored(self):
        """CSV files with extra unexpected columns should still be accepted."""
        content = HEADER + ",extra_col\n"
        content += GOOD_ROW + ",ignored_value\n"
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        )
        tmp.write(content)
        tmp.close()
        result = run_pipeline(Path(tmp.name))
        self.assertEqual(result.summary["clean_records"], 1)

    def test_bom_prefix_is_stripped(self):
        """CSV files with a UTF-8 BOM should be read correctly."""
        content = "\ufeff" + HEADER + "\n" + GOOD_ROW + "\n"
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        )
        tmp.write(content)
        tmp.close()
        result = run_pipeline(Path(tmp.name))
        self.assertEqual(result.summary["clean_records"], 1)

    def test_multiple_simultaneous_high_severity_issues_logged_individually(self):
        """A row with 3 separate high-severity issues must produce 3 issue records."""
        # missing customer_id, invalid order_date, zero quantity
        path = _csv_path(
            "ORD-MI,,not-a-date,2026-01-03,northeast,software,0,100.00,delivered"
        )
        result = run_pipeline(path)
        # 3 distinct issues: customer_id missing, order_date invalid, quantity <= 0
        high_issues = [i for i in result.issues if i.severity == "high"]
        high_fields = {i.field for i in high_issues}
        self.assertIn("customer_id", high_fields)
        self.assertIn("order_date", high_fields)
        self.assertIn("quantity", high_fields)
        # All logged as separate records (not merged)
        self.assertGreaterEqual(len(high_issues), 3)
        self.assertEqual(result.summary["clean_records"], 0)

    def test_pipeline_issues_written_one_per_issue(self):
        """pipeline_issues.csv must have one row per issue, not per problematic row."""
        # Row with 2 issues: missing customer_id, invalid order_date
        path = _csv_path(
            "ORD-IP,,not-a-date,2026-01-03,northeast,software,2,100.00,delivered"
        )
        result = run_pipeline(path)

        with tempfile.TemporaryDirectory() as tmp_dir:
            write_reports(result, Path(tmp_dir))
            issues_csv = Path(tmp_dir) / "pipeline_issues.csv"
            rows = list(csv.DictReader(issues_csv.open(encoding="utf-8")))
            # Each issue is its own row
            self.assertGreaterEqual(len(rows), 2)
            fields = {r["field"] for r in rows}
            self.assertIn("customer_id", fields)
            self.assertIn("order_date", fields)


if __name__ == "__main__":
    unittest.main()
