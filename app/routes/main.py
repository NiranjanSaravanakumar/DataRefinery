"""
DataRefinery — Main Routes (GET /)
=====================================
Serves the landing page with the CSV upload form.
"""

from __future__ import annotations

from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index() -> str:
    """
    Home page — renders the upload form.

    Returns:
        Rendered index.html template.
    """
    return render_template("index.html")
