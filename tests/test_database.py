"""
Database and ORM Relationship Test Suite.
Verifies table creation, model constraints, relationships, password security, and cascades.
"""

import sys
from pathlib import Path
from datetime import date

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app import create_app
from app.extensions import db
from app.models import User, ReportCategory, IncidentReport, EvidenceFile, AuditLog, Notification


def test_database_schema_and_relationships():
    """End-to-end verification of SQLite database models and relationships."""
    # Use testing config (in-memory SQLite)
    app = create_app("testing")

    with app.app_context():
        db.create_all()

        # 1. Test User creation & Password Hashing
        user = User(
            full_name="Alice Smith",
            email="alice@example.com",
            role="user"
        )
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        assert user.id is not None
        assert user.password_hash != "SecurePass123!"  # Password must never be plain text
        assert user.check_password("SecurePass123!") is True
        assert user.check_password("WrongPassword") is False
        assert user.is_admin is False

        # Test Admin User
        admin = User(
            full_name="Bob Admin",
            email="bob.admin@example.gov",
            role="admin"
        )
        admin.set_password("AdminSecret#99")
        db.session.add(admin)
        db.session.commit()
        assert admin.is_admin is True

        # 2. Test ReportCategory
        category = ReportCategory(
            category_name="Cyberbullying",
            description="Online harassment targeted at individuals."
        )
        db.session.add(category)
        db.session.commit()
        assert category.id is not None

        # 3. Test IncidentReport
        report = IncidentReport(
            report_number="REP-2026-TEST001",
            user_id=user.id,
            category_id=category.id,
            title="Threatening messages on social media",
            description="Received repeated abusive messages on my profile.",
            incident_date=date(2026, 11, 10),
            incident_platform="Instagram",
            status=IncidentReport.STATUS_PENDING
        )
        db.session.add(report)
        db.session.commit()

        assert report.id is not None
        assert report.user.email == "alice@example.com"
        assert report.category.category_name == "Cyberbullying"
        assert user.reports.count() == 1
        assert category.reports.count() == 1

        # 4. Test EvidenceFile (Stored outside public web root)
        evidence = EvidenceFile(
            report_id=report.id,
            original_filename="screenshot_chat.png",
            stored_filename="evidence_uuid_12345.png",
            file_path="uploads/evidence/evidence_uuid_12345.png",
            file_type="image/png"
        )
        db.session.add(evidence)
        db.session.commit()

        assert evidence.id is not None
        assert evidence.report.report_number == "REP-2026-TEST001"
        assert report.evidence_files.count() == 1

        # 5. Test AuditLog (Nullable user_id supported)
        audit = AuditLog(
            user_id=admin.id,
            action="REPORT_STATUS_CHANGE",
            description="Changed status from Pending to Under Review",
            ip_address="192.168.1.50"
        )
        db.session.add(audit)
        db.session.commit()

        assert audit.id is not None
        assert audit.user.full_name == "Bob Admin"
        assert admin.audit_logs.count() == 1

        # 6. Test Notification
        notification = Notification(
            user_id=user.id,
            report_id=report.id,
            message="Your report REP-2026-TEST001 is now Under Review.",
            is_read=False
        )
        db.session.add(notification)
        db.session.commit()

        assert notification.id is not None
        assert notification.is_read is False
        assert user.notifications.count() == 1

        # 7. Test Cascade Delete: deleting a report cascades to its evidence and notifications
        report_id = report.id
        db.session.delete(report)
        db.session.commit()

        # Evidence and notifications for this report should be deleted
        assert EvidenceFile.query.filter_by(report_id=report_id).first() is None
        assert Notification.query.filter_by(report_id=report_id).first() is None
        # User and category must still exist
        assert db.session.get(User, user.id) is not None
        assert db.session.get(ReportCategory, category.id) is not None

        print("✓ All database models, constraints, and relationships passed verification!")


if __name__ == "__main__":
    test_database_schema_and_relationships()
