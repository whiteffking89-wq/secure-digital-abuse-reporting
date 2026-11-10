"""
Application Factory Package.
Initializes Flask app, database extensions, and registers route blueprints.
"""

from pathlib import Path
from flask import Flask
from config import config_by_name
from app.extensions import db


def create_app(config_name: str = "default") -> Flask:
    """
    Factory function to create and configure the Flask application instance.
    """
    flask_app = Flask(__name__)
    flask_app.config.from_object(config_by_name[config_name])

    # Ensure required secure directories exist at runtime
    upload_folder = Path(flask_app.config["UPLOAD_FOLDER"])
    upload_folder.mkdir(parents=True, exist_ok=True)

    # Ensure SQLite database directory exists
    db_uri = flask_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if db_uri.startswith("sqlite:///"):
        db_path = Path(db_uri.replace("sqlite:///", ""))
        db_path.parent.mkdir(parents=True, exist_ok=True)

    # Initialize database extensions
    db.init_app(flask_app)

    # Import models and register blueprints within app context
    with flask_app.app_context():
        from app import models as _models  # noqa: F401
        from app.routes.auth import auth_bp
        from app.routes.citizen import citizen_bp
        from app.routes.evidence import evidence_bp

        flask_app.register_blueprint(auth_bp)
        flask_app.register_blueprint(citizen_bp)
        flask_app.register_blueprint(evidence_bp)

    return flask_app
