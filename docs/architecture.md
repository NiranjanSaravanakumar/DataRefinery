# Architecture

This document describes the technical architecture of **BB DataRefinery**.

---

## Overview

BB DataRefinery is a **single-package Python ETL application** following a classical Extract → Validate → Transform → Load (ETL) pattern. It is implemented entirely using the Python standard library and requires no external runtime dependencies.

```
bb_datapipeline/
├── __init__.py     ← Public API surface
├── __main__.py     ← CLI entry point
└── pipeline.py     ← All ETL logic
```

---

## Design Principles

| Principle | How It Is Applied |
|---|---|
| **Pure functions** | All logic lives in top-level functions with no shared mutable state |
| **Immutable data containers** | `PipelineIssue` and `PipelineResult` are frozen `dataclass`es |
| **Zero runtime dependencies** | Only the Python standard library is used |
| **Exact arithmetic** | `decimal.Decimal` is used for all financial calculations (no float errors) |
| **Clear separation of concerns** | Extract, validate, transform, and load steps are distinct functions |
| **Fail-fast on high severity** | Rows with `high` issues are rejected immediately; they never reach the transform stage |

---

## Data Flow

```
raw_orders.csv
    │
    ▼
_read_csv(path)
    │   Returns: list[dict[str, str]]
    │   Each dict = one CSV row keyed by column header
    │
    ▼
run_pipeline(input_path) — iterates over every row
    │
    ├── [Per Row] Required field checks
    ├── [Per Row] Duplicate order ID check
    ├── [Per Row] Date format and logic validation
    ├── [Per Row] Numeric range validation (quantity, unit_price)
    ├── [Per Row] Status normalisation
    ├── [Per Row] Region alias resolution
    │
    ├── If no HIGH severity issue → _transform_row() → added to cleaned_rows
    └── All issues (high + medium) → added to issues list
    │
    ▼
PipelineResult(cleaned_rows, issues, summary)
    │
    ▼
write_reports(result, output_dir)
    │
    ├── clean_orders.csv          ← _write_clean_orders()
    ├── pipeline_issues.csv       ← _write_issues()
    └── pipeline_summary.json     ← json.dumps(result.summary)
```

---

## Key Data Structures

### `PipelineIssue`

```python
@dataclass(frozen=True)
class PipelineIssue:
    row_number: int    # CSV row number (2-indexed; row 1 is the header)
    order_id:   str    # The affected order ID, or "UNKNOWN" if missing
    field:      str    # The column name that caused the issue
    severity:   str    # "high" (row rejected) or "medium" (row kept)
    message:    str    # Human-readable description of the problem
```

### `PipelineResult`

```python
@dataclass(frozen=True)
class PipelineResult:
    cleaned_rows: list[dict[str, str]]   # Accepted, transformed records
    issues:       list[PipelineIssue]    # All validation failures
    summary:      dict[str, object]      # Aggregate metrics
```

---

## Validation Severity Model

```
Every row
    │
    ├── Has HIGH issues? ─── Yes ──► Rejected (excluded from clean_orders.csv)
    │                                          Included in pipeline_issues.csv
    │
    └── No HIGH issues ──────────► Accepted (included in clean_orders.csv)
              │
              └── Has MEDIUM issues? ─── Yes ──► Kept, but issues logged
```

---

## Pipeline Score Formula

```python
issue_penalty    = total_issues × 4 + high_severity_issues × 5
pipeline_score   = max(0, min(100, 100 − issue_penalty))
```

This produces a 0–100 quality indicator. A perfect dataset with zero issues scores 100. The sample dataset scores 46.

---

## Module Dependency Graph

```
__main__.py
    └── imports: pipeline.run_pipeline
                 pipeline.write_reports

__init__.py
    └── imports: pipeline.run_pipeline
                 pipeline.PipelineResult
                 (re-exports both as public API)

pipeline.py
    └── imports: csv, json, dataclasses, datetime,
                 decimal, pathlib, typing
                 (all standard library — no third-party packages)
```

---

## Why No Classes?

The pipeline deliberately avoids class-based design for the business logic. All processing is done by standalone functions that accept input, return output, and have no side effects. This makes each function:

- Independently testable with no setup
- Easy to read (no `self`, no `__init__`, no instance state)
- Composable (functions can be called from anywhere)

The only classes used are `dataclass`es (`PipelineIssue`, `PipelineResult`), which serve as **typed data containers** — not objects with behaviour.

---

## Why `Decimal` Instead of `float`?

Financial calculations must be exact. IEEE 754 floating-point arithmetic produces rounding errors:

```python
>>> 0.1 + 0.2
0.30000000000000004

>>> Decimal("0.1") + Decimal("0.2")
Decimal('0.3')
```

Using `Decimal` for `quantity`, `unit_price`, and `revenue` ensures that currency values are always precise to the cent.
