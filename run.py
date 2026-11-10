"""
Application Entry Point.
Executes the Flask development server when run directly.
"""

import os
from app import create_app

# Retrieve environment or default to development
config_name = os.environ.get("FLASK_ENV", "development")
app = create_app(config_name)

if __name__ == "__main__":
    # Starter entry point: Run development server
    app.run(host="127.0.0.1", port=5000, debug=True)
