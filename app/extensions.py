"""
Application Extensions Module.
Initializes shared extension instances to prevent circular imports across models and blueprints.
"""

from flask_sqlalchemy import SQLAlchemy

# Global database instance
db = SQLAlchemy()
