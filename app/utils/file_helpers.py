"""
DataRefinery — File Handling Utilities
========================================
Provides helpers for validating uploaded CSV files, managing
per-session directories, and cleaning up old sessions.
"""

from __future__ import annotations

import csv
import io
import shutil
import time
from pathlib import Path

from werkzeug.datastructures import FileStorage

# Maximum number of rows to read during validation (avoids loading huge files into RAM)
_PROBE_ROWS = 5


def validate_csv_file(file: FileStorage) -> str | None:
    """
    Validate an uploaded file to ensure it is a readable CSV.

    Checks:
      1. File extension is `.csv`
      2. File is non-empty (at least a header row)
      3. No encoding issues (UTF-8; BOM is accepted and stripped by the pipeline)
      4. Delimiter sniff — warns if the content does not appear to be
         comma-separated (wrong delimiter, binary data, etc.)
      5. First few rows can be parsed as CSV without error

    Args:
        file: The Werkzeug FileStorage object from the request.

    Returns:
        An error message string if validation fails, or None if valid.
    """
    filename = file.filename or ""

    # --- Extension check ---
    if not filename.lower().endswith(".csv"):
        return (
            f"Invalid file type: '{filename}'. " "Only CSV files (.csv) are accepted."
        )

    # --- Readability check (probe first chunk) ---
    try:
        # Read a limited chunk to avoid loading the entire file into memory.
        chunk = file.read(65536)  # 64 KB is enough to detect encoding/format issues
        file.seek(0)

        if not chunk.strip():
            return "The uploaded file is empty. Please upload a CSV file with data."

        # --- Encoding check ---
        # Attempt strict UTF-8 decode (BOM prefix b'\xef\xbb\xbf' is also OK — the
        # pipeline uses utf-8-sig which strips it automatically).
        try:
            text = chunk.decode("utf-8-sig")
        except UnicodeDecodeError:
            return (
                "The file contains characters that cannot be decoded as UTF-8. "
                "Please save your CSV with UTF-8 encoding and try again."
            )

        # --- Delimiter / structure sniff ---
        # Use csv.Sniffer on the first 2 KB. If it cannot detect a delimiter or
        # detects something other than a comma, the file is likely not a valid CSV.
        sample = text[:2048]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            if dialect.delimiter != ",":
                return (
                    f"The file appears to use '{dialect.delimiter}' as a delimiter "
                    "instead of a comma. Please export your file as a comma-separated "
                    "CSV and try again."
                )
        except csv.Error:
            # Sniffer failure means very few rows or unusual structure — fall through
            # and let the DictReader probe below catch actual parse errors.
            pass

        # --- Header + row parse check ---
        reader = csv.DictReader(io.StringIO(text))
        header = reader.fieldnames

        if not header:
            return "The CSV file has no header row. Please ensure the first row contains column names."

        # Try to read a few rows to catch malformed CSV structures (ragged rows, etc.)
        for _ in zip(reader, range(_PROBE_ROWS)):
            pass

    except Exception as exc:
        return f"Could not read the file as CSV: {exc}"

    return None  # Validation passed


def get_session_dir(base_upload_dir: Path, session_id: str) -> Path:
    """
    Return the Path for a session-specific directory, creating it if needed.

    Each upload gets its own isolated directory named by a UUID, so
    concurrent users never share or overwrite each other's files.

    Args:
        base_upload_dir: The root uploads folder from app config.
        session_id:      The UUID string for this session.

    Returns:
        Path to the session directory (guaranteed to exist).
    """
    session_dir = base_upload_dir / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def cleanup_old_sessions(base_upload_dir: Path, max_age_hours: int = 2) -> int:
    """
    Delete session directories older than `max_age_hours`.

    Called after each upload as a best-effort cleanup. Errors are silently
    ignored so that they never break the upload flow.

    Args:
        base_upload_dir: The root uploads folder.
        max_age_hours:   Maximum allowed age of a session folder in hours.

    Returns:
        Number of session directories deleted.
    """
    if not base_upload_dir.exists():
        return 0

    cutoff = time.time() - max_age_hours * 3600
    deleted = 0

    for session_dir in base_upload_dir.iterdir():
        if not session_dir.is_dir():
            continue
        try:
            if session_dir.stat().st_mtime < cutoff:
                shutil.rmtree(session_dir, ignore_errors=True)
                deleted += 1
        except Exception:
            pass  # Best effort — never crash the calling request

    return deleted
