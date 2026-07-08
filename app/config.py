"""
DataRefinery Flask Configuration
=================================
Provides configuration classes for the Flask application.
All sensitive values are read from environment variables via python-dotenv.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

# Base directory of the project (one level above this file)
BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """Base configuration — all environments share these defaults."""

    # Flask core
    SECRET_KEY: str = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))
    DEBUG: bool = False
    TESTING: bool = False

    # Upload settings
    UPLOAD_FOLDER: Path = BASE_DIR / "uploads"
    MAX_CONTENT_LENGTH: int = int(os.environ.get("MAX_UPLOAD_MB", "32")) * 1024 * 1024
    ALLOWED_EXTENSIONS: frozenset[str] = frozenset({"csv"})

    # Session expiry for uploaded files (in hours)
    SESSION_MAX_AGE_HOURS: int = 2

    # Application metadata
    APP_NAME: str = "DataRefinery"
    APP_VERSION: str = "2.0.0"


class DevelopmentConfig(Config):
    """Development configuration — enables debug mode and verbose logging."""

    DEBUG: bool = True
    TESTING: bool = False


class TestingConfig(Config):
    """Testing configuration — uses a temporary upload folder."""

    TESTING: bool = True
    DEBUG: bool = True
    UPLOAD_FOLDER: Path = BASE_DIR / "uploads_test"


class ProductionConfig(Config):
    """Production configuration — strict security settings."""

    DEBUG: bool = False
    SECRET_KEY: str = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(64))


# Map string names to config classes for easy lookup
config_map: dict[str, type[Config]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config(env: str | None = None) -> Config:
    """
    Return the appropriate Config instance for the given environment name.

    Args:
        env: One of 'development', 'testing', 'production', or None (reads FLASK_ENV).

    Returns:
        An instantiated Config object.
    """
    env = env or os.environ.get("FLASK_ENV", "development")
    config_class = config_map.get(env, DevelopmentConfig)
    return config_class()
