"""
DataRefinery — API Routes
===========================
Handles file upload, pipeline processing, and file downloads.
All state is managed per-session via UUID keys stored in URL
parameters (stateless — no server-side session storage).
"""

from __future__ import annotations

import io
import json
import uuid
import zipfile

from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    request,
    send_file,
)
from werkzeug.utils import secure_filename

from ..services.cleaner import CleaningService
from ..services.report import ReportService
from ..utils.file_helpers import (
    validate_csv_file,
    get_session_dir,
    cleanup_old_sessions,
)

api_bp = Blueprint("api", __name__)


def _valid_session_id(session_id: str) -> bool:
    """Return True if session_id is a valid version-4 UUID string.

    This prevents path traversal attacks where a crafted session_id
    (e.g. '../../../etc/passwd') could escape the uploads directory.
    """
    try:
        val = uuid.UUID(session_id, version=4)
        return str(val) == session_id
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


@api_bp.route("/upload", methods=["POST"])
def upload() -> tuple:
    """
    POST /upload — Accepts a CSV file, validates it, and saves it to a session folder.

    Expects a multipart/form-data request with the file under the key 'file'.

    Returns:
        JSON with { session_id, filename, size_bytes } on success.
        JSON with { error } on failure (400 / 415).
    """
    if "file" not in request.files:
        return (
            jsonify(
                {"error": "No file part in the request. Please attach a CSV file."}
            ),
            400,
        )

    file = request.files["file"]

    if file.filename == "" or file.filename is None:
        return jsonify({"error": "No file selected. Please choose a CSV file."}), 400

    # Validate extension and readability
    error = validate_csv_file(file)
    if error:
        return jsonify({"error": error}), 415

    # Create a fresh session directory for this upload
    session_id = str(uuid.uuid4())
    session_dir = get_session_dir(current_app.config["UPLOAD_FOLDER"], session_id)

    # Save the uploaded file with a safe filename
    filename = secure_filename(file.filename or "upload.csv")
    save_path = session_dir / filename
    file.seek(0)
    file.save(save_path)

    # Asynchronously clean up old sessions (non-blocking, best-effort)
    try:
        cleanup_old_sessions(
            current_app.config["UPLOAD_FOLDER"],
            max_age_hours=current_app.config.get("SESSION_MAX_AGE_HOURS", 2),
        )
    except Exception:
        pass  # Never let cleanup break an upload

    return (
        jsonify(
            {
                "session_id": session_id,
                "filename": filename,
                "size_bytes": save_path.stat().st_size,
            }
        ),
        200,
    )


# ---------------------------------------------------------------------------
# Clean / Process
# ---------------------------------------------------------------------------


@api_bp.route("/clean", methods=["POST"])
def clean() -> tuple:
    """
    POST /clean — Runs the ETL pipeline on the previously uploaded CSV.

    Expects JSON body: { "session_id": "<uuid>", "filename": "<name.csv>" }

    Returns:
        JSON redirect hint: { "redirect": "/result/<session_id>" } on success.
        JSON with { "error" } on failure (400 / 404 / 500).
    """
    data = request.get_json(silent=True) or {}
    session_id: str = data.get("session_id", "")
    filename: str = data.get("filename", "")

    if not session_id or not filename:
        return jsonify({"error": "Missing session_id or filename."}), 400

    if not _valid_session_id(session_id):
        return jsonify({"error": "Invalid session ID format."}), 400

    session_dir = get_session_dir(current_app.config["UPLOAD_FOLDER"], session_id)
    input_path = session_dir / filename

    if not input_path.exists():
        return jsonify({"error": "Uploaded file not found. Please upload again."}), 404

    try:
        svc = CleaningService()
        result = svc.process(input_path, session_dir)
        # Save result summary as JSON for the result page
        summary_path = session_dir / "web_summary.json"
        summary_path.write_text(json.dumps(result, default=str), encoding="utf-8")
    except Exception as exc:
        return jsonify({"error": f"Pipeline error: {exc}"}), 500

    return jsonify({"redirect": f"/result/{session_id}"}), 200


# ---------------------------------------------------------------------------
# Result page
# ---------------------------------------------------------------------------


@api_bp.route("/result/<session_id>")
def result(session_id: str) -> str | tuple:
    """
    GET /result/<session_id> — Renders the results page after cleaning.

    Args:
        session_id: UUID of the processing session.

    Returns:
        Rendered result.html template, or 404 if session not found.
    """
    if not _valid_session_id(session_id):
        return jsonify({"error": "Invalid session ID format."}), 400

    session_dir = get_session_dir(current_app.config["UPLOAD_FOLDER"], session_id)
    summary_path = session_dir / "web_summary.json"

    if not summary_path.exists():
        return (
            render_template(
                "index.html",
                error="Session not found or expired. Please upload your file again.",
            ),
            404,
        )

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return render_template("result.html", summary=summary, session_id=session_id)


# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------


@api_bp.route("/download/cleaned/<session_id>")
def download_cleaned(session_id: str) -> object:
    """
    GET /download/cleaned/<session_id> — Streams the cleaned CSV to the browser.

    Args:
        session_id: UUID of the processing session.

    Returns:
        CSV file attachment, or 404 JSON if not found.
    """
    if not _valid_session_id(session_id):
        return jsonify({"error": "Invalid session ID format."}), 400

    session_dir = get_session_dir(current_app.config["UPLOAD_FOLDER"], session_id)
    cleaned_path = session_dir / "clean_orders.csv"

    if not cleaned_path.exists():
        return jsonify({"error": "Cleaned file not found."}), 404

    return send_file(
        cleaned_path,
        mimetype="text/csv",
        as_attachment=True,
        download_name="clean_orders.csv",
    )


@api_bp.route("/download/report/<session_id>")
def download_report(session_id: str) -> object:
    """
    GET /download/report/<session_id> — Streams the HTML report to the browser.

    Args:
        session_id: UUID of the processing session.

    Returns:
        HTML file attachment, or 404 JSON if not found.
    """
    if not _valid_session_id(session_id):
        return jsonify({"error": "Invalid session ID format."}), 400

    session_dir = get_session_dir(current_app.config["UPLOAD_FOLDER"], session_id)
    summary_path = session_dir / "web_summary.json"

    if not summary_path.exists():
        return jsonify({"error": "Report not found."}), 404

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    html_content = ReportService.generate_html(summary)

    return send_file(
        io.BytesIO(html_content.encode("utf-8")),
        mimetype="text/html",
        as_attachment=True,
        download_name="datapipeline_report.html",
    )


@api_bp.route("/download/zip/<session_id>")
def download_zip(session_id: str) -> object:
    """
    GET /download/zip/<session_id> — Streams a ZIP file containing the cleaned CSV
    and the HTML report.

    Args:
        session_id: UUID of the processing session.

    Returns:
        ZIP file attachment, or 404 JSON if the session is missing.
    """
    if not _valid_session_id(session_id):
        return jsonify({"error": "Invalid session ID format."}), 400

    session_dir = get_session_dir(current_app.config["UPLOAD_FOLDER"], session_id)
    cleaned_path = session_dir / "clean_orders.csv"
    summary_path = session_dir / "web_summary.json"

    if not cleaned_path.exists() or not summary_path.exists():
        return (
            jsonify({"error": "Session files not found. Please process a file first."}),
            404,
        )

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    report_html = ReportService.generate_html(summary)

    # Build ZIP in memory — no temp files needed
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(cleaned_path, arcname="clean_orders.csv")
        zf.writestr("datapipeline_report.html", report_html)
        # Also include the raw JSON summary for power users
        zf.write(session_dir / "pipeline_issues.csv", arcname="pipeline_issues.csv")
        zf.writestr(
            "pipeline_summary.json",
            json.dumps(summary.get("pipeline_summary", {}), indent=2),
        )

    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name="datarefinery_output.zip",
    )
