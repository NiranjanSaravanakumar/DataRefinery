<div align="center">

# ⚗️ DataRefinery

**A production-style Python ETL pipeline with a Flask web interface — upload a messy CSV, get back a cleaned file and a full quality report.**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen)](#running-tests)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[**Report a Bug**](https://github.com/NiranjanSaravanakumar/DataRefinery/issues) · [**Request a Feature**](https://github.com/NiranjanSaravanakumar/DataRefinery/issues)

</div>

---

## 📸 Dashboard Preview

![DataRefinery Dashboard](assets/datapipeline-dashboard.png)

---

## 📋 Table of Contents

- [Project Overview](#-project-overview)
- [Features](#-features)
- [Architecture Overview](#-architecture-overview)
- [Folder Structure](#-folder-structure)
- [Technologies Used](#-technologies-used)
- [Installation](#-installation)
- [How to Run](#-how-to-run)
- [Running Tests](#-running-tests)
- [API Routes](#-api-routes)
- [Pipeline Validation Rules](#-pipeline-validation-rules)
- [Pipeline Output Files](#-pipeline-output-files)
- [Data Transformations](#-data-transformations)
- [Pipeline Score](#-pipeline-score)
- [Future Improvements](#-future-improvements)

---

## 📖 Project Overview

**DataRefinery** is a full-stack Python ETL application consisting of two layers:

1. **Core ETL pipeline** (`datapipeline/`) — a pure-Python package that reads raw CSV order data, applies 9 validation rules, transforms accepted rows, and writes three structured output files. Zero external runtime dependencies.

2. **Flask web interface** (`app/`) — a browser-based frontend that lets users upload a CSV file, runs the ETL pipeline on the server, and presents an interactive results dashboard with download options.

| Output File | Description |
|---|---|
| `clean_orders.csv` | Validated, standardised, enriched order records |
| `pipeline_issues.csv` | Row-level log of every validation failure found |
| `pipeline_summary.json` | Aggregate metrics: revenue, scores, status counts |

**Why this project?**
Most portfolio projects only show *displaying* data. This project demonstrates the harder, more valuable skill: *cleaning and validating* data before it reaches any dashboard or downstream system — which is what real data engineering teams actually spend their time doing.

---

## ✨ Features

- **Validation Engine** — 9 rules: required fields, date formats, numeric ranges, duplicate IDs, status and region standardisation
- **Data Standardisation** — Normalises region aliases (`NE` → `Northeast`), status casings, customer IDs, and category titles
- **Revenue Calculation** — Computes `revenue = quantity × unit_price` using `decimal.Decimal` (no float errors)
- **Fulfillment Timing** — Calculates `fulfillment_days` from order date to ship date
- **Priority Lane Flag** — Marks high-value or time-sensitive orders as `priority_lane: Yes`
- **Severity-based Filtering** — `high`-severity rows are rejected; `medium`-severity rows are kept and flagged
- **Pipeline Score** — A 0–100 quality score based on issue count and severity
- **Flask Web App** — Drag-and-drop CSV upload, progress bar, results dashboard, and download buttons
- **Session Isolation** — Each upload gets its own UUID-keyed directory; sessions auto-expire after 2 hours
- **Unit + Integration Tests** — Pipeline tests and full Flask route tests via `pytest`

---

## 🏗 Architecture Overview

```
Browser
  │
  │  POST /upload (multipart CSV)
  ▼
Flask (app/)
  ├── routes/main.py       GET /                → Upload page
  ├── routes/api.py        POST /upload         → Validate & save file
  │                        POST /clean          → Run ETL pipeline
  │                        GET  /result/<id>    → Results page
  │                        GET  /download/…     → CSV / HTML / ZIP downloads
  │
  ├── services/
  │   ├── cleaner.py       Wraps datapipeline, builds web_summary dict
  │   └── report.py        Generates standalone HTML report
  │
  └── utils/
      └── file_helpers.py  CSV validation, session dir management, cleanup

Core ETL (datapipeline/)
  └── pipeline.py
        _read_csv()         EXTRACT  — CSV rows → list[dict]
        run_pipeline()      VALIDATE — 9 rules, per-row
        _transform_row()    TRANSFORM — enrich accepted rows
        write_reports()     LOAD     — 3 output files
```

---

## 📁 Folder Structure

```text
DataRefinery/
│
├── app/                          # Flask web application
│   ├── __init__.py               # App factory (create_app)
│   ├── config.py                 # Dev / Testing / Production config classes
│   ├── routes/
│   │   ├── main.py               # GET / (upload page)
│   │   └── api.py                # POST /upload, /clean, GET /result, /download
│   ├── services/
│   │   ├── cleaner.py            # ETL orchestration + web summary builder
│   │   └── report.py             # Standalone HTML report generator
│   ├── utils/
│   │   └── file_helpers.py       # CSV validation, session dirs, cleanup
│   ├── templates/
│   │   ├── base.html             # Shared layout (nav, footer, Google Fonts)
│   │   ├── index.html            # Upload form page
│   │   └── result.html           # Results dashboard page
│   └── static/
│       ├── css/style.css         # All application styles
│       └── js/upload.js          # Drag-and-drop upload flow + XHR
│
├── datapipeline/                 # Core ETL package (no Flask dependency)
│   ├── __init__.py               # Public API: run_pipeline, PipelineResult
│   ├── __main__.py               # CLI entry point (python -m datapipeline)
│   └── pipeline.py               # All ETL logic: validate, transform, report
│
├── data/
│   └── raw_orders.csv            # Sample input (14 rows, intentional errors)
│
├── reports/                      # Generated outputs (git-ignored)
│   ├── clean_orders.csv
│   ├── pipeline_issues.csv
│   └── pipeline_summary.json
│
├── tests/
│   ├── test_pipeline.py          # Unit tests for the ETL pipeline
│   └── test_routes.py            # Integration tests for Flask routes
│
├── docs/
│   ├── architecture.md           # Technical architecture deep-dive
│   └── workflow.md               # Step-by-step data flow explanation
│
├── assets/
│   └── datapipeline-dashboard.png  # README screenshot
│
├── run.py                        # Flask dev server entry point
├── requirements.txt              # All Python dependencies
├── .env.example                  # Environment variable template
└── .gitignore                    # Standard Python + Flask gitignore
```

---

## 🛠 Technologies Used

| Technology | Version | Purpose |
|---|---|---|
| **Python** | 3.11+ | Core language |
| **Flask** | 3.0+ | Web framework |
| **Werkzeug** | 3.0+ | File handling utilities |
| **python-dotenv** | 1.0+ | `.env` file loader |
| `csv` (stdlib) | — | CSV reading and writing |
| `json` (stdlib) | — | Summary report serialisation |
| `dataclasses` (stdlib) | — | Immutable pipeline data containers |
| `decimal` (stdlib) | — | Exact arithmetic for financial values |
| `datetime` (stdlib) | — | Date parsing and validation |
| `pathlib` (stdlib) | — | Cross-platform file path handling |
| `uuid` (stdlib) | — | Session isolation |
| **HTML / CSS / JS** | — | Frontend (vanilla, no frameworks) |
| **pytest** | 8.0+ | Test runner |
| **black** | 24.0+ | Code formatter |
| **ruff** | 0.4+ | Linter |
| **mypy** | 1.10+ | Static type checker |

---

## ⚙️ Installation

### Prerequisites

- **Python 3.11 or higher** — [Download Python](https://www.python.org/downloads/)
- **Git** — [Download Git](https://git-scm.com/)

### Step 1 — Clone the repository

```bash
git clone https://github.com/NiranjanSaravanakumar/DataRefinery.git
cd DataRefinery
```

### Step 2 — Create a virtual environment

**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Configure environment (optional)

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Edit `.env` to set your `FLASK_SECRET_KEY` and any other overrides. All values have sensible defaults so this step is optional for local development.

---

## ▶️ How to Run

### Option A — Flask web server (recommended)

```bash
python run.py
```

Then open **http://127.0.0.1:5000/** in your browser.

**What you can do:**
1. **Upload** a CSV file via drag-and-drop or the file picker
2. **Clean** — click "Upload & Clean Data" to run the ETL pipeline
3. **Review** — the results dashboard shows before/after stats, issue severity, revenue breakdown, and quality score
4. **Download** — get the cleaned CSV, a standalone HTML report, or a ZIP bundle containing both

**Environment variables (all optional):**

| Variable | Default | Description |
|---|---|---|
| `FLASK_HOST` | `127.0.0.1` | Server host |
| `FLASK_PORT` | `5000` | Server port |
| `FLASK_DEBUG` | `true` | Enable debug mode |
| `FLASK_ENV` | `development` | Environment (`development` / `production` / `testing`) |
| `FLASK_SECRET_KEY` | *(random)* | Secret key for session signing |
| `MAX_UPLOAD_MB` | `32` | Maximum upload file size in MB |
| `SESSION_MAX_AGE_HOURS` | `2` | Hours before uploaded sessions are auto-deleted |

### Option B — CLI pipeline (no web server)

```bash
python -m datapipeline --input data/raw_orders.csv --out reports
```

**Arguments:**

| Argument | Default | Description |
|---|---|---|
| `--input` | `data/raw_orders.csv` | Path to the raw CSV input file |
| `--out` | `reports` | Directory where output files will be written |

**Expected output:**
```
Processed 14 rows.
Clean records: 8
Issues found: 18
Pipeline score: 46/100
```

---

## 🧪 Running Tests

The project includes unit tests for the ETL pipeline and integration tests for all Flask routes.

```bash
pytest
```

**Expected result:**
```
tests/test_pipeline.py ...     [ 3 tests ]
tests/test_routes.py .......   [13 tests]
----------------------------------------------------------------------
All tests passed.
```

To run with verbose output:
```bash
pytest -v
```

---

## 🌐 API Routes

| Method | Route | Description |
|---|---|---|
| `GET` | `/` | Upload page |
| `GET` | `/health` | Health check — returns JSON `{ status: "ok", version, timestamp }` |
| `POST` | `/upload` | Accept a CSV file; returns `{ session_id, filename, size_bytes }` |
| `POST` | `/clean` | Run ETL on a session file; returns `{ redirect: "/result/<id>" }` |
| `GET` | `/result/<session_id>` | Results dashboard page |
| `GET` | `/download/cleaned/<session_id>` | Download cleaned CSV |
| `GET` | `/download/report/<session_id>` | Download standalone HTML report |
| `GET` | `/download/zip/<session_id>` | Download ZIP (cleaned CSV + HTML report + JSON summary) |

---

## ✅ Pipeline Validation Rules

| Rule | Severity | Description |
|---|---|---|
| Missing required field | `high` | Any of the 9 required columns is blank |
| Duplicate order ID | `high` | The same `order_id` appears more than once |
| Invalid order date | `high` | `order_date` is not a valid `YYYY-MM-DD` date |
| Invalid ship date | `high` | `ship_date` is not a valid `YYYY-MM-DD` date |
| Ship before order | `high` | `ship_date` is earlier than `order_date` |
| Non-positive quantity | `high` | `quantity` is 0 or negative |
| Non-positive unit price | `high` | `unit_price` is 0 or negative |
| Invalid status | `high` | `status` is not one of the 5 accepted values |
| Unrecognised region | `medium` | `region` cannot be mapped to a standard name |

> Rows with **any** `high`-severity issue are excluded from `clean_orders.csv`. Rows with only `medium` issues are included but flagged.

---

## 📤 Pipeline Output Files

### `clean_orders.csv`
Accepted records with computed fields added:

| Column | Description |
|---|---|
| `order_id` | Original order identifier |
| `customer_id` | Uppercased customer identifier |
| `order_date` | ISO 8601 date string |
| `ship_date` | ISO 8601 date string |
| `fulfillment_days` | Days between order and ship date |
| `region` | Standardised region name |
| `category` | Title-cased category |
| `quantity` | Integer quantity |
| `unit_price` | Price formatted to 2 decimal places |
| `revenue` | `quantity × unit_price` |
| `status` | Standardised status label |
| `priority_lane` | `Yes` if revenue ≥ $500 or status is Processing |

### `pipeline_issues.csv`
Row-level validation log:

| Column | Description |
|---|---|
| `row_number` | CSV row number (header = row 1) |
| `order_id` | Affected order ID (or `UNKNOWN` if missing) |
| `field` | Column that caused the issue |
| `severity` | `high` or `medium` |
| `message` | Human-readable description |

### `pipeline_summary.json`
Aggregate run metrics:

```json
{
  "rows_processed": 14,
  "clean_records": 8,
  "rejected_records": 6,
  "issues_found": 18,
  "high_severity_issues": 13,
  "pipeline_score": 46,
  "total_revenue": "6002.50",
  "revenue_by_region": { "Midwest": "...", "Northeast": "...", ... },
  "status_counts": { "Delivered": 4, "Shipped": 2, ... },
  "top_issue_fields": { "order_date": 3, ... }
}
```

---

## 🔄 Data Transformations

| Field | Transformation Applied |
|---|---|
| `customer_id` | Converted to uppercase (`c-224` → `C-224`) |
| `region` | Alias-mapped (`NE`, `north east` → `Northeast`) |
| `status` | Normalised to title case (`shipped` → `Shipped`) |
| `category` | Title-cased (`cloud services` → `Cloud Services`) |
| `unit_price` | Currency symbol stripped, formatted to 2 d.p. |
| `revenue` | Computed as `quantity × unit_price` |
| `fulfillment_days` | Computed as `ship_date − order_date` in calendar days |
| `priority_lane` | `Yes` if revenue ≥ 500 or status is Processing |

---

## 📊 Pipeline Score

The **Pipeline Score** is a 0–100 quality metric computed at the end of each run:

```
score = max(0, min(100, 100 − (issues × 4) − (high_severity_issues × 5)))
```

| Score Range | Interpretation |
|---|---|
| 90 – 100 | Excellent data quality |
| 70 – 89 | Good — minor issues present |
| 50 – 69 | Fair — significant cleanup needed |
| 0 – 49 | Poor — major data quality problems |

The sample dataset intentionally scores **46/100** to demonstrate the pipeline's issue-detection capability.

---

## 💡 Future Improvements

- [ ] Add support for Excel (`.xlsx`) input files via `openpyxl`
- [ ] Add a configurable rules file (JSON/YAML) so validation rules can be changed without editing source code
- [ ] Extend region aliases to support all US regions and international markets
- [ ] Add a `--verbose` CLI flag for detailed per-row output
- [ ] Add GitHub Actions CI workflow to run tests automatically on every push
- [ ] Add Dockerfile for containerised deployment
- [ ] Package `datapipeline` and publish to PyPI

---

<div align="center">

⭐ **If this project was useful to you, please consider starring the repository!** ⭐

</div>
