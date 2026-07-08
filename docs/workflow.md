# Workflow Guide

This document explains how data flows through **DataRefinery** step by step.

---

## 1. Input Data

The pipeline expects a CSV file with these **9 required columns**:

| Column | Expected Format | Example |
|---|---|---|
| `order_id` | Any non-blank string | `ORD-1001` |
| `customer_id` | Any non-blank string | `c-224` |
| `order_date` | `YYYY-MM-DD` | `2026-05-01` |
| `ship_date` | `YYYY-MM-DD` | `2026-05-03` |
| `region` | See region aliases | `Northeast`, `NE`, `ne` |
| `category` | Any non-blank string | `software` |
| `quantity` | Positive integer | `2` |
| `unit_price` | Positive decimal | `129.00` or `$129.00` |
| `status` | See valid statuses | `Delivered`, `shipped` |

---

## 2. Validation Stage

Each row is checked in this order:

### Step 1 — Required Fields
All 9 columns must be present and non-blank.
- Severity: **high**
- Any blank required field causes the entire row to be rejected.

### Step 2 — Duplicate Order ID
The `order_id` is checked against a set of all previously seen order IDs in the same file.
- Severity: **high**
- The second occurrence of a duplicate ID is rejected.

### Step 3 — Date Validation
Both `order_date` and `ship_date` must be valid `YYYY-MM-DD` dates.
Additionally, `ship_date` must not be earlier than `order_date`.
- Severity: **high**
- An invalid or illogical date causes rejection.

### Step 4 — Numeric Validation
Both `quantity` and `unit_price` must be positive (> 0).
- Severity: **high**
- Zero or negative values cause rejection.
- Currency symbols (`$`) in `unit_price` are stripped before parsing.

### Step 5 — Status Validation
The `status` field must match one of 5 accepted values (case-insensitive):
- `delivered` → `Delivered`
- `shipped` → `Shipped`
- `processing` → `Processing`
- `cancelled` → `Cancelled`
- `returned` → `Returned`
- Severity: **high**
- Unrecognised values (e.g. `packed`) cause rejection.

### Step 6 — Region Standardisation
The `region` field is matched against a set of known aliases (case-insensitive):
- `NE`, `ne`, `north east`, `northeast` → `Northeast`
- `SE`, `se`, `south east`, `southeast` → `Southeast`
- `midwest` → `Midwest`
- `west` → `West`
- Severity: **medium** (unrecognised region is logged but the row is still accepted)

---

## 3. Transformation Stage

Rows that pass all high-severity checks are enriched with computed fields:

| Field | Transformation |
|---|---|
| `customer_id` | Uppercased: `c-224` → `C-224` |
| `region` | Alias resolved or original value kept |
| `category` | Title-cased: `cloud services` → `Cloud Services` |
| `unit_price` | Formatted to 2 d.p.: `129` → `129.00` |
| `quantity` | Converted to integer string: `2.0` → `2` |
| `revenue` | Calculated: `quantity × unit_price` |
| `fulfillment_days` | Calculated: `ship_date − order_date` in days |
| `priority_lane` | `Yes` if `revenue ≥ 500` or `status == "Processing"`, else `No` |

---

## 4. Output Stage

Three files are written to the output directory:

### `clean_orders.csv`
Contains only accepted, transformed rows.
One row per accepted order. Includes all original columns plus computed fields.

### `pipeline_issues.csv`
Contains every validation failure found across all rows.
Multiple issues can exist for the same row (e.g., both `order_date` and `quantity` invalid).

### `pipeline_summary.json`
A single JSON object with aggregate statistics for the entire run. Useful for dashboards and monitoring.

---

## 5. Typical Run with Sample Data

The included `data/raw_orders.csv` contains 14 rows with deliberate data quality issues:

| Issue | Row(s) | Description |
|---|---|---|
| Invalid status `packed` | ORD-1011 | Not in the accepted status list |
| Ship date before order date | ORD-1004 | `2026-05-01` < `2026-05-03` |
| Zero quantity | ORD-1006 | `quantity = 0` is invalid |
| Invalid ship date | ORD-1012 | `not-a-date` is not a valid date |
| Duplicate order ID | ORD-1008 (row 14) | Same ID appears twice |
| Missing order ID | Row 15 | `order_id` is blank |

**Result:** 8 clean records, 6 rejected records, 18 total issues, pipeline score = 46.
