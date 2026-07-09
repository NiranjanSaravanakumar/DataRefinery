# DataRefinery

A Python ETL project that turns messy CSV order files into clean, validated data and downloadable quality reports. The repository includes both a core pipeline library and a Flask web app for uploading files and reviewing results in the browser.

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Tests](https://img.shields.io/badge/tests-33%20passing-brightgreen)](#running-tests)
[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-blue)](.github/workflows/ci.yml)

## Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Architecture](#architecture)
- [Folder Structure](#folder-structure)
- [Installation](#installation)
- [Git Setup](#git-setup)
- [Running the Project](#running-the-project)
- [Environment Variables](#environment-variables)
- [API Routes](#api-routes)
- [Configuration Files](#configuration-files)
- [Tests](#tests)
- [Deployment Notes](#deployment-notes)

## Project Overview

DataRefinery solves a common data engineering problem: validating and cleaning messy CSV exports before they are used downstream. The project has two parts:

1. A core ETL pipeline in [datapipeline](datapipeline) that reads raw CSV rows, applies validation rules, transforms accepted rows, and writes output files.
2. A Flask web interface in [app](app) that lets a user upload a CSV, run the pipeline, and download the cleaned file and report.

### What problem it solves

Many CSV files contain formatting issues, invalid values, duplicates, and inconsistent categories. This project identifies those problems, rejects rows with high-severity issues, keeps rows with only warnings, and produces a clean dataset plus a detailed audit trail.

### Main features

- Validates required fields, dates, quantities, prices, statuses, and regions
- Standardizes regions, statuses, customer IDs, and categories
- Computes revenue and fulfillment timing
- Assigns a pipeline quality score from 0 to 100
- Produces three output files: cleaned data, issues log, and summary JSON
- Offers a browser-based upload flow with progress feedback and downloadable results
- Includes 33 automated tests and GitHub Actions CI

### Tech stack

- Python 3.11+
- Flask
- Jinja2 templates
- Vanilla JavaScript and CSS
- pytest, black, ruff, and mypy

### Architecture at a glance

```text
Upload CSV -> Flask routes -> CleaningService -> datapipeline.run_pipeline() -> reports -> browser download
```

The core pipeline is dependency-light and uses only the Python standard library. The web layer adds file upload handling, session-based storage, and HTML report generation.

## Screenshots

![DataRefinery dashboard](assets/datapipeline-dashboard.png)

## Folder Structure

```text
DataRefinery/
├── app/                  # Flask application and UI
│   ├── routes/           # Home page and API endpoints
│   ├── services/         # Cleaning and report generation services
│   ├── static/           # CSS and JavaScript assets
│   ├── templates/        # HTML templates
│   └── utils/            # CSV and session helpers
├── datapipeline/         # Core ETL pipeline package
├── data/                 # Sample CSV input
├── docs/                 # Architecture and workflow notes
├── reports/              # Generated pipeline outputs
├── tests/                # Unit and route tests
├── uploads/              # Session uploads created during local runs
├── .env.example          # Environment variable template
├── requirements.txt      # Python dependencies
├── run.py                # Flask entry point
└── README.md             # Project documentation
```

### Why each folder exists

- [app](app): contains the Flask app factory, templates, static assets, and route handlers for the browser experience
- [datapipeline](datapipeline): contains the pipeline logic without any Flask dependency
- [data](data): includes sample input data used for testing and demos
- [docs](docs): contains architecture and workflow documentation for developers
- [reports](reports): stores generated outputs when the pipeline is run locally
- [tests](tests): verifies pipeline rules and Flask routes
- [uploads](uploads): stores per-upload session files created by the web app

## Installation

### Prerequisites

- Python 3.11 or newer
- Git
- A terminal such as PowerShell, Command Prompt, or Bash

No Node.js, npm, Java, or database server is required for this project.

### Clone the repository

```bash
git clone https://github.com/NiranjanSaravanakumar/DataRefinery.git
cd DataRefinery
```

What each command does:

- `git clone`: downloads the repository to your machine
- `cd DataRefinery`: moves you into the project directory

### Create a virtual environment

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Install dependency explanation

The dependencies in [requirements.txt](requirements.txt) are:

- `flask`: powers the web app and routing
- `python-dotenv`: loads variables from `.env`
- `Werkzeug`: supports file upload and secure filename handling
- `pytest`: runs automated tests
- `black`: formats the codebase
- `ruff`: lints the codebase
- `mypy`: performs static type checking

### Optional environment file

```bash
copy .env.example .env
```

On macOS or Linux:

```bash
cp .env.example .env
```

## Git Setup

If you are starting from scratch, these are the common git commands you will use:

```bash
git init
```

- Creates a new Git repository in the current folder.

```bash
git remote add origin <repository-url>
```

- Connects your local repository to a remote GitHub repository.

```bash
git status
```

- Shows which files have changed.

```bash
git add .
```

- Stages your changes so they can be committed.

```bash
git commit -m "Describe your change"
```

- Saves your staged changes with a message.

```bash
git push origin main
```

- Uploads your committed changes to GitHub.

### Branching

```bash
git branch
```

- Lists all branches.

```bash
git checkout -b feature/my-change
```

- Creates and switches to a new branch.

```bash
git switch main
```

- Switches back to the main branch.

```bash
git pull origin main
```

- Downloads the latest updates from GitHub.

```bash
git merge feature/my-change
```

- Applies the changes from another branch into the current branch.

### Resolving conflicts

When Git cannot merge changes automatically, it marks the conflicting files. Open the file, resolve the differences, then run:

```bash
git add <file>
git commit
```

## Environment Variables

The project uses environment variables through Python and Flask. A template is provided in [.env.example](.env.example).

### Variables used by the current application

- `FLASK_SECRET_KEY`: secret value used for Flask session security
- `FLASK_DEBUG`: enables or disables debug mode
- `FLASK_HOST`: host used by the development server
- `FLASK_PORT`: port used by the development server
- `FLASK_ENV`: selects the environment configuration (`development`, `testing`, `production`)
- `MAX_UPLOAD_MB`: maximum upload size in megabytes
- `SESSION_MAX_AGE_HOURS`: how long uploaded session folders are kept before cleanup

### How to configure them

1. Copy [.env.example](.env.example) to `.env`
2. Edit the values you need
3. Restart the Flask app so the new values are loaded

The app also has sensible defaults, so local development will usually work without changes.

## Running the Project

### Start the web app

```bash
python run.py
```

Then open http://127.0.0.1:5000/ in your browser.

The web flow is:

1. Upload a CSV file
2. Wait for the upload to finish
3. Click the cleaning button
4. Review the results page
5. Download the cleaned CSV, report, or ZIP bundle

### Run the CLI pipeline directly

```bash
python -m datapipeline --input data/raw_orders.csv --out reports
```

This writes the output files into the reports folder without starting the web server.

### Run the tests

```bash
pytest
```

The current repository has 33 passing tests.

## API Routes

The Flask app exposes these routes:

| Method | Route | Purpose |
|---|---|---|
| GET | `/` | Shows the upload page |
| POST | `/upload` | Accepts a CSV file and creates a session folder |
| POST | `/clean` | Runs the pipeline on the uploaded file |
| GET | `/result/<session_id>` | Renders the results page |
| GET | `/download/cleaned/<session_id>` | Downloads the cleaned CSV |
| GET | `/download/report/<session_id>` | Downloads the HTML report |
| GET | `/download/zip/<session_id>` | Downloads a ZIP bundle |

### Example request

```bash
curl -X POST http://127.0.0.1:5000/upload -F "file=@data/raw_orders.csv"
```

The response includes a `session_id` that is used for the later processing and download endpoints.

## Backend Explanation

The backend is organized around a small Flask application factory:

- [app/__init__.py](app/__init__.py): creates the Flask app and registers the blueprints
- [app/routes/main.py](app/routes/main.py): renders the home page
- [app/routes/api.py](app/routes/api.py): handles uploads, processing, result rendering, and downloads
- [app/services/cleaner.py](app/services/cleaner.py): orchestrates the ETL pipeline and prepares web-friendly summary data
- [app/services/report.py](app/services/report.py): creates the downloadable HTML report
- [app/utils/file_helpers.py](app/utils/file_helpers.py): validates uploaded CSV files and manages session folders

There is no database layer in the current implementation. Uploads are kept in session-specific folders under [uploads](uploads).

## Data and Pipeline Outputs

The sample dataset in [data/raw_orders.csv](data/raw_orders.csv) contains intentional data quality issues.

When the pipeline runs, it writes three files:

- `clean_orders.csv`: accepted, transformed rows
- `pipeline_issues.csv`: every validation issue encountered
- `pipeline_summary.json`: aggregate metrics including the pipeline score

The example dataset currently produces 8 clean records, 6 rejected records, 18 issues, and a pipeline score of 46 out of 100.

## Configuration Files

- [requirements.txt](requirements.txt): Python dependencies for runtime, tests, and linting
- [run.py](run.py): starts the Flask development server
- [app/config.py](app/config.py): config classes for development, testing, and production
- [.env.example](.env.example): environment variable template
- [.github/workflows/ci.yml](.github/workflows/ci.yml): CI pipeline for tests and linting

## Tests

The project uses both unit and integration tests:

- [tests/test_pipeline.py](tests/test_pipeline.py): validates the core ETL rules and report generation
- [tests/test_routes.py](tests/test_routes.py): verifies the Flask routes and download behavior

Run them with:

```bash
pytest
```

## Deployment Notes

The project is currently designed for local development and simple deployment with a WSGI server such as Gunicorn. The app is not connected to a database or external storage service, so it is best suited for single-instance or small-scale deployments.

For production, make sure to:

- set a strong `FLASK_SECRET_KEY`
- disable debug mode
- use a real WSGI server
- protect the upload directory and limit file sizes

## Contributing

1. Create a feature branch
2. Make your changes
3. Run the test suite
4. Open a pull request with a clear description
