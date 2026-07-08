"""
DataRefinery — Main Routes (GET, POST /)
=========================================
Serves the landing page with the CSV upload form.
Accepts both GET and POST so index.html can be rendered
after a form submission or an internal redirect.
"""

from __future__ import annotations

from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/", methods=["GET", "POST"])
def index() -> str:
    """
    Home page — renders the upload form.

    Accepts GET (normal page load) and POST (redirect from form submission
    or internal redirect after a failed operation).

    Returns:
        Rendered index.html template.
    """
    return render_template("index.html")
