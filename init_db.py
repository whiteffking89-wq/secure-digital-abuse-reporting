"""
Database Initialization and Seeding Script.
Creates all SQLite database tables and populates default categories and test users.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from app import create_app
from app.extensions import db
from app.models import User, ReportCategory, AuditLog

DEFAULT_CATEGORIES = [
    {
        "category_name": "Cyberbullying",
        "description": "Harassment, insulting comments, trolling, and intimidation targeted at an individual online."
    },
    {
        "category_name": "Online Harassment & Stalking",
        "description": "Persistent unwanted contact, monitoring, threats, and cyberstalking across digital platforms."
    },
    {
        "category_name": "Impersonation & Fake Profiles",
        "description": "Unauthorized creation of fake accounts or theft of digital identity to defame, mislead, or deceive."
    },
    {
        "category_name": "Non-Consensual Image Sharing",
        "description": "Sharing or threatening to share intimate, private, or manipulated images without explicit consent."
    },
    {
        "category_name": "Financial Fraud & Extortion",
        "description": "Online blackmail, sextortion, crypto scams, and identity-driven financial extortion."
    },
    {
        "category_name": "Hate Speech & Discriminatory Abuse",
        "description": "Promoting violence, humiliation, or severe hostility against individuals or protected groups."
    },
    {
        "category_name": "Doxxing & Privacy Violation",
        "description": "Malicious distribution of private personal data, contact information, or home addresses online."
    },
]


def init_database():
    """Initializes SQLite database tables and seeds starter data."""
    app = create_app("development")

    with app.app_context():
        print("Creating SQLite database tables...")
        db.create_all()
        print("✓ All tables created successfully.")

        # Seed Report Categories
        print("\nSeeding report categories...")
        categories_added = 0
        for cat_data in DEFAULT_CATEGORIES:
            existing = ReportCategory.query.filter_by(category_name=cat_data["category_name"]).first()
            if not existing:
                category = ReportCategory(
                    category_name=cat_data["category_name"],
                    description=cat_data["description"]
                )
                db.session.add(category)
                categories_added += 1

        db.session.commit()
        print(f"✓ {categories_added} categories added ({len(DEFAULT_CATEGORIES)} total available).")

        # Seed Default Admin Account
        admin_email = "admin@digitalabuse.gov"
        existing_admin = User.query.filter_by(email=admin_email).first()
        if not existing_admin:
            admin = User(
                full_name="System Administrator",
                email=admin_email,
                role="admin"
            )
            admin.set_password("Admin@12345")
            db.session.add(admin)
            db.session.flush()

            # Add initial audit log
            audit = AuditLog(
                user_id=admin.id,
                action="SYSTEM_INIT",
                description="Database initialized and default administrator account created.",
                ip_address="127.0.0.1"
            )
            db.session.add(audit)
            db.session.commit()
            print(f"✓ Default Admin created: {admin_email} (Password: Admin@12345)")
        else:
            print(f"• Admin account ({admin_email}) already exists.")

        # Seed Default Citizen Account for Testing
        citizen_email = "citizen@example.com"
        existing_citizen = User.query.filter_by(email=citizen_email).first()
        if not existing_citizen:
            citizen = User(
                full_name="Sample Citizen",
                email=citizen_email,
                role="user"
            )
            citizen.set_password("Citizen@12345")
            db.session.add(citizen)
            db.session.commit()
            print(f"✓ Default Citizen created: {citizen_email} (Password: Citizen@12345)")
        else:
            print(f"• Citizen account ({citizen_email}) already exists.")

        print("\n✓ Database setup completed successfully!")


if __name__ == "__main__":
    init_database()
