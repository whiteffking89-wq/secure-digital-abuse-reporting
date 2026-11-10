"""
Incident Reporting & Secure Evidence Management Test Suite.
Tests category retrieval, report submission, validation, evidence file validation,
access control, and status tracking.
"""

import sys
import io
import tempfile
from pathlib import Path
from datetime import date, timedelta

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app import create_app
from app.extensions import db
from app.models import User, ReportCategory, IncidentReport, EvidenceFile, Notification, AuditLog


def setup_test_app():
    """Sets up an isolated test application with temporary upload directory and in-memory DB."""
    temp_dir = tempfile.mkdtemp()
    app = create_app("testing")
    app.config["UPLOAD_FOLDER"] = Path(temp_dir)

    with app.app_context():
        db.create_all()

        # Seed test categories
        c1 = ReportCategory(category_name="Cyberbullying", description="Harassment online.")
        c2 = ReportCategory(category_name="Impersonation", description="Fake profile.")
        db.session.add_all([c1, c2])

        # Seed citizen user
        user = User(full_name="Alice Reporter", email="alice@test.com", role="user")
        user.set_password("Password123")

        # Seed second citizen user (to test cross-user access restrictions)
        other_user = User(full_name="Bob Stranger", email="bob@test.com", role="user")
        other_user.set_password("Password123")

        # Seed admin user
        admin = User(full_name="System Admin", email="admin@test.gov", role="admin")
        admin.set_password("AdminPass123")

        db.session.add_all([user, other_user, admin])
        db.session.commit()

    return app


def test_get_categories():
    """Tests category listing endpoint."""
    app = setup_test_app()
    client = app.test_client()

    res = client.get("/categories")
    data = res.get_json()

    assert res.status_code == 200
    assert data["success"] is True
    assert len(data["categories"]) >= 2
    names = [c["category_name"] for c in data["categories"]]
    assert "Cyberbullying" in names
    assert "Impersonation" in names


def test_report_submission_validation():
    """Tests validation of required fields and future date rejection."""
    app = setup_test_app()
    client = app.test_client()

    # Login as citizen
    client.post("/auth/login", json={"email": "alice@test.com", "password": "Password123"})

    # 1. Missing Title
    res = client.post("/report", data={
        "category_id": 1,
        "description": "Valid incident description with sufficient length.",
        "incident_date": "2026-11-10",
        "incident_platform": "Instagram"
    })
    assert res.status_code == 400
    assert "title" in res.get_json()["error"].lower()

    # 2. Invalid Category ID
    res = client.post("/report", data={
        "title": "Harassment on Instagram",
        "category_id": 999,  # Does not exist
        "description": "Valid incident description with sufficient length.",
        "incident_date": "2026-11-10",
        "incident_platform": "Instagram"
    })
    assert res.status_code == 400
    assert "invalid category" in res.get_json()["error"].lower()

    # 3. Short description
    res = client.post("/report", data={
        "title": "Harassment on Instagram",
        "category_id": 1,
        "description": "Short",  # < 10 chars
        "incident_date": "2026-11-10",
        "incident_platform": "Instagram"
    })
    assert res.status_code == 400
    assert "description" in res.get_json()["error"].lower()

    # 4. Future incident date (cannot report incidents from tomorrow)
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    res = client.post("/report", data={
        "title": "Harassment on Instagram",
        "category_id": 1,
        "description": "Valid incident description with sufficient length.",
        "incident_date": tomorrow,
        "incident_platform": "Instagram"
    })
    assert res.status_code == 400
    assert "future" in res.get_json()["error"].lower()

    # 5. Missing Platform
    res = client.post("/report", data={
        "title": "Harassment on Instagram",
        "category_id": 1,
        "description": "Valid incident description with sufficient length.",
        "incident_date": "2026-11-10",
        "incident_platform": ""
    })
    assert res.status_code == 400
    assert "platform" in res.get_json()["error"].lower()


def test_report_submission_without_evidence():
    """Tests successful complaint submission without attached files."""
    app = setup_test_app()
    client = app.test_client()

    client.post("/auth/login", json={"email": "alice@test.com", "password": "Password123"})

    payload = {
        "title": "Repeated offensive comments",
        "category_id": 1,
        "description": "A user on WhatsApp is repeatedly sending offensive and insulting messages.",
        "incident_date": "2026-11-10",
        "incident_platform": "WhatsApp"
    }
    res = client.post("/report", data=payload)
    data = res.get_json()

    assert res.status_code == 201
    assert data["success"] is True
    assert data["report"]["report_number"].startswith("REP-2026-")
    assert data["report"]["status"] == "Pending"
    assert len(data["report"]["evidence_files"]) == 0

    # Verify notification created
    with app.app_context():
        user = User.query.filter_by(email="alice@test.com").first()
        notification = Notification.query.filter_by(user_id=user.id).first()
        assert notification is not None
        assert data["report"]["report_number"] in notification.message

        # Verify audit log recorded
        audit = AuditLog.query.filter_by(user_id=user.id, action="REPORT_SUBMITTED").first()
        assert audit is not None


def test_report_submission_with_evidence():
    """Tests complaint submission with a valid attached evidence file."""
    app = setup_test_app()
    client = app.test_client()

    client.post("/auth/login", json={"email": "alice@test.com", "password": "Password123"})

    # Create dummy PNG file in memory
    dummy_file = (io.BytesIO(b"\x89PNG\r\n\x1a\nFakePngContent"), "screenshot_proof.png")

    data_payload = {
        "title": "Extortion threat in DMs",
        "category_id": 1,
        "description": "User threatened to publish private details unless paid.",
        "incident_date": "2026-11-09",
        "incident_platform": "Telegram",
        "evidence": dummy_file
    }

    res = client.post("/report", data=data_payload, content_type="multipart/form-data")
    data = res.get_json()

    assert res.status_code == 201
    assert data["success"] is True
    assert len(data["report"]["evidence_files"]) == 1

    ev_info = data["report"]["evidence_files"][0]
    assert ev_info["original_filename"] == "screenshot_proof.png"
    assert ev_info["stored_filename"].startswith("ev_")
    assert ev_info["stored_filename"].endswith(".png")

    # Verify file was written to disk
    with app.app_context():
        evidence_entry = EvidenceFile.query.filter_by(stored_filename=ev_info["stored_filename"]).first()
        assert evidence_entry is not None
        assert Path(evidence_entry.file_path).exists()
        assert Path(evidence_entry.file_path).read_bytes() == b"\x89PNG\r\n\x1a\nFakePngContent"


def test_report_submission_invalid_file_extension():
    """Tests that uploading an unpermitted file (e.g. .exe) is rejected."""
    app = setup_test_app()
    client = app.test_client()

    client.post("/auth/login", json={"email": "alice@test.com", "password": "Password123"})

    malicious_file = (io.BytesIO(b"MZ\x90\x00BinaryExe"), "payload.exe")

    data_payload = {
        "title": "Malware sent via chat",
        "category_id": 1,
        "description": "The sender sent a file claimed to be pictures.",
        "incident_date": "2026-11-09",
        "incident_platform": "Email",
        "evidence": malicious_file
    }

    res = client.post("/report", data=data_payload, content_type="multipart/form-data")
    data = res.get_json()

    assert res.status_code == 400
    assert data["success"] is False
    assert "unsupported file type" in data["error"].lower()

    # Ensure transaction was rolled back and no report was persisted
    with app.app_context():
        assert IncidentReport.query.filter_by(title="Malware sent via chat").first() is None


def test_get_my_reports():
    """Tests that a citizen can view their own submitted reports."""
    app = setup_test_app()
    client = app.test_client()

    client.post("/auth/login", json={"email": "alice@test.com", "password": "Password123"})

    # Submit two reports
    client.post("/report", data={
        "title": "Report 1", "category_id": 1, "description": "Description for report number one.",
        "incident_date": "2026-11-08", "incident_platform": "Discord"
    })
    client.post("/report", data={
        "title": "Report 2", "category_id": 2, "description": "Description for report number two.",
        "incident_date": "2026-11-09", "incident_platform": "Twitter"
    })

    res = client.get("/my-reports")
    data = res.get_json()

    assert res.status_code == 200
    assert data["success"] is True
    assert data["count"] == 2
    titles = [r["title"] for r in data["reports"]]
    assert "Report 1" in titles
    assert "Report 2" in titles


def test_track_report():
    """Tests complaint status tracking by reference code."""
    app = setup_test_app()
    client = app.test_client()

    client.post("/auth/login", json={"email": "alice@test.com", "password": "Password123"})

    sub_res = client.post("/report", data={
        "title": "Identity Theft Case",
        "category_id": 2,
        "description": "Someone cloned my Instagram account and is impersonating me.",
        "incident_date": "2026-11-07",
        "incident_platform": "Instagram"
    })
    report_num = sub_res.get_json()["report"]["report_number"]

    # 1. Track as owner (full details returned)
    track_res = client.get(f"/track/{report_num}")
    track_data = track_res.get_json()
    assert track_res.status_code == 200
    assert track_data["success"] is True
    assert track_data["report"]["report_number"] == report_num
    assert track_data["report"]["status"] == "Pending"
    assert "description" in track_data["report"]

    # 2. Track as unauthenticated visitor (privacy-safe status returned, no private description)
    client.post("/auth/logout")
    public_res = client.get(f"/track/{report_num}")
    pub_data = public_res.get_json()
    assert public_res.status_code == 200
    assert pub_data["report"]["report_number"] == report_num
    assert pub_data["report"]["status"] == "Pending"
    assert "description" not in pub_data["report"]  # Protects victim privacy

    # 3. Non-existent reference code -> 404
    missing_res = client.get("/track/REP-9999-DOESNOTEXIST")
    assert missing_res.status_code == 404


def test_evidence_access_control():
    """Tests that only the complaint owner and admins can view uploaded evidence."""
    app = setup_test_app()
    client = app.test_client()

    # 1. Alice logs in and submits report with evidence
    client.post("/auth/login", json={"email": "alice@test.com", "password": "Password123"})
    dummy_file = (io.BytesIO(b"SensitiveChatLogs"), "chat_log.txt")
    sub_res = client.post("/report", data={
        "title": "Abuse with Evidence",
        "category_id": 1,
        "description": "Full description of abusive incident.",
        "incident_date": "2026-11-05",
        "incident_platform": "WhatsApp",
        "evidence": dummy_file
    }, content_type="multipart/form-data")
    evidence_id = sub_res.get_json()["report"]["evidence_files"][0]["id"]

    # 2. Alice (owner) accesses evidence -> 200 OK
    res_owner = client.get(f"/evidence/view/{evidence_id}")
    assert res_owner.status_code == 200
    assert res_owner.data == b"SensitiveChatLogs"

    # 3. Bob (different user) attempts to access Alice's evidence -> 403 Forbidden
    client.post("/auth/logout")
    client.post("/auth/login", json={"email": "bob@test.com", "password": "Password123"})
    res_stranger = client.get(f"/evidence/view/{evidence_id}")
    assert res_stranger.status_code == 403
    assert "access denied" in res_stranger.get_json()["error"].lower()

    # 4. Admin accesses Alice's evidence -> 200 OK
    client.post("/auth/logout")
    client.post("/auth/login", json={"email": "admin@test.gov", "password": "AdminPass123"})
    res_admin = client.get(f"/evidence/view/{evidence_id}")
    assert res_admin.status_code == 200
    assert res_admin.data == b"SensitiveChatLogs"

    # 5. Unauthenticated visitor attempts to access evidence -> 401 Unauthorized
    client.post("/auth/logout")
    res_unauth = client.get(f"/evidence/view/{evidence_id}")
    assert res_unauth.status_code == 401


if __name__ == "__main__":
    test_get_categories()
    test_report_submission_validation()
    test_report_submission_without_evidence()
    test_report_submission_with_evidence()
    test_report_submission_invalid_file_extension()
    test_get_my_reports()
    test_track_report()
    test_evidence_access_control()
    print("✓ All Incident Reporting and Evidence Security tests passed successfully!")
