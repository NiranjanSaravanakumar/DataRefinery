"""
DataRefinery — Flask Route Tests
==================================
Tests for the Flask web API routes.
Uses Flask's built-in test client for fast, in-process testing.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from app import create_app

# Path to the real sample CSV bundled with the project
SAMPLE_CSV = Path(__file__).resolve().parents[1] / "data" / "raw_orders.csv"


@pytest.fixture
def client(tmp_path):
    """Create a Flask test client with an isolated upload folder."""
    app = create_app("testing")
    app.config["UPLOAD_FOLDER"] = tmp_path / "uploads"
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── Home page ─────────────────────────────────────────────────────────────────


class TestHomePage:
    def test_home_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_home_contains_upload_form(self, client):
        resp = client.get("/")
        assert b"file-input" in resp.data


# ── Upload endpoint ───────────────────────────────────────────────────────────


class TestUpload:
    def _csv_bytes(self):
        return SAMPLE_CSV.read_bytes()

    def test_upload_valid_csv(self, client):
        data = {"file": (io.BytesIO(self._csv_bytes()), "raw_orders.csv")}
        resp = client.post("/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert "session_id" in body
        assert "filename" in body

    def test_upload_no_file_returns_400(self, client):
        resp = client.post("/upload", data={}, content_type="multipart/form-data")
        assert resp.status_code == 400

    def test_upload_wrong_extension_returns_415(self, client):
        data = {"file": (io.BytesIO(b"hello world"), "data.txt")}
        resp = client.post("/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 415

    def test_upload_empty_file_returns_415(self, client):
        data = {"file": (io.BytesIO(b""), "empty.csv")}
        resp = client.post("/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 415


# ── Clean endpoint ────────────────────────────────────────────────────────────


class TestClean:
    def _upload_sample(self, client):
        """Helper: upload the sample CSV and return (session_id, filename)."""
        csv_bytes = SAMPLE_CSV.read_bytes()
        data = {"file": (io.BytesIO(csv_bytes), "raw_orders.csv")}
        resp = client.post("/upload", data=data, content_type="multipart/form-data")
        body = json.loads(resp.data)
        return body["session_id"], body["filename"]

    def test_clean_pipeline_succeeds(self, client):
        sid, fname = self._upload_sample(client)
        resp = client.post(
            "/clean",
            data=json.dumps({"session_id": sid, "filename": fname}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert "redirect" in body
        assert sid in body["redirect"]

    def test_clean_missing_session_returns_400(self, client):
        resp = client.post(
            "/clean",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_clean_unknown_session_returns_404(self, client):
        # Use a valid UUID format that doesn't match any real session directory
        resp = client.post(
            "/clean",
            data=json.dumps(
                {
                    "session_id": "00000000-0000-4000-8000-000000000000",
                    "filename": "x.csv",
                }
            ),
            content_type="application/json",
        )
        assert resp.status_code == 404


# ── Result page ───────────────────────────────────────────────────────────────


class TestResult:
    def _process_sample(self, client):
        """Upload + clean the sample CSV and return session_id."""
        csv_bytes = SAMPLE_CSV.read_bytes()
        data = {"file": (io.BytesIO(csv_bytes), "raw_orders.csv")}
        upload_resp = client.post(
            "/upload", data=data, content_type="multipart/form-data"
        )
        body = json.loads(upload_resp.data)
        sid, fname = body["session_id"], body["filename"]
        client.post(
            "/clean",
            data=json.dumps({"session_id": sid, "filename": fname}),
            content_type="application/json",
        )
        return sid

    def test_result_page_renders(self, client):
        sid = self._process_sample(client)
        resp = client.get(f"/result/{sid}")
        assert resp.status_code == 200
        assert b"Pipeline" in resp.data

    def test_result_page_shows_correct_counts(self, client):
        sid = self._process_sample(client)
        resp = client.get(f"/result/{sid}")
        # The sample dataset: 14 rows in, 8 clean
        assert b"14" in resp.data
        assert b"8" in resp.data


# ── Downloads ─────────────────────────────────────────────────────────────────


class TestDownloads:
    def _process_sample(self, client):
        csv_bytes = SAMPLE_CSV.read_bytes()
        data = {"file": (io.BytesIO(csv_bytes), "raw_orders.csv")}
        upload_resp = client.post(
            "/upload", data=data, content_type="multipart/form-data"
        )
        body = json.loads(upload_resp.data)
        sid, fname = body["session_id"], body["filename"]
        client.post(
            "/clean",
            data=json.dumps({"session_id": sid, "filename": fname}),
            content_type="application/json",
        )
        return sid

    def test_download_cleaned_csv(self, client):
        sid = self._process_sample(client)
        resp = client.get(f"/download/cleaned/{sid}")
        assert resp.status_code == 200
        assert b"order_id" in resp.data  # CSV header row

    def test_download_report_html(self, client):
        sid = self._process_sample(client)
        resp = client.get(f"/download/report/{sid}")
        assert resp.status_code == 200
        assert b"<!DOCTYPE html>" in resp.data

    def test_download_zip(self, client):
        sid = self._process_sample(client)
        resp = client.get(f"/download/zip/{sid}")
        assert resp.status_code == 200
        assert resp.content_type == "application/zip"

    def test_download_unknown_session_returns_404(self, client):
        # Use a valid UUID format that doesn't match any real session directory
        resp = client.get("/download/cleaned/00000000-0000-4000-8000-000000000000")
        assert resp.status_code == 404
