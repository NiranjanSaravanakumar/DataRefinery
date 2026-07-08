"""
DataRefinery Flask Application Factory
========================================
Creates and configures the Flask app instance.
Uses the app factory pattern for testability and config flexibility.
"""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask

from .config import get_config


def create_app(env: str | None = None) -> Flask:
    """
    Flask application factory.

    Creates the Flask app, applies configuration, registers blueprints,
    and ensures the upload directory exists.

    Args:
        env: Optional environment name ('development', 'production', 'testing').
             Falls back to the FLASK_ENV environment variable, then 'development'.

    Returns:
        A configured Flask application instance.
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Load configuration
    cfg = get_config(env)
    app.config.from_object(cfg)

    # Ensure the upload directory exists at startup
    upload_folder: Path = app.config["UPLOAD_FOLDER"]
    upload_folder.mkdir(parents=True, exist_ok=True)

    # Register blueprints
    from .routes.main import main_bp
    from .routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    return app
