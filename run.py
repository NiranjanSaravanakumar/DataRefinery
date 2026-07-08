"""
DataRefinery — Flask Entry Point
==================================
Run the Flask development server with:

    python run.py

Or for production use a WSGI server:

    gunicorn "app:create_app()" --bind 0.0.0.0:5000

Environment variables are loaded from a .env file if present.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env before anything else so all os.environ reads see the values
load_dotenv(Path(__file__).parent / ".env")

from app import create_app  # noqa: E402 — must come after load_dotenv

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() in ("1", "true", "yes")

    print(f"\n  DataRefinery v2.0 is running!")
    print(f"  -> http://{host}:{port}/\n")

    app.run(host=host, port=port, debug=debug)
