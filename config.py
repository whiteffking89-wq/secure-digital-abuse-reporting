"""
Configuration Module for Secure Digital Abuse Reporting Platform.
Defines application settings and security boundaries for different environments.
"""

import os
from pathlib import Path

# Base directory: points to the root of the project
BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Base configuration with shared security defaults."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-fallback-insecure-key-change-in-production")
    
    # SQLite Database stored inside data/database/
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'data' / 'database' / 'abuse_reporting.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # CRITICAL SECURITY REQUIREMENT:
    # Uploaded evidence files are strictly stored OUTSIDE app/static/
    # This prevents unauthenticated users or web crawlers from viewing sensitive evidence directly.
    UPLOAD_FOLDER = BASE_DIR / "uploads" / "evidence"
    
    # Maximum allowed file upload size: 16 MB
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    # Whitelisted file extensions for evidence
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf", "mp4", "txt"}
    
    # Session Cookie Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class DevelopmentConfig(Config):
    """Development environment settings."""
    DEBUG = True


class TestingConfig(Config):
    """Testing environment settings with in-memory database."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production environment with hardened security headers."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True  # Requires HTTPS in production


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
