"""
Browser Routes and Interactive HTML Forms Test Suite.
Verifies Jinja2 template rendering, browser form submissions, redirects,
flash messages, and end-to-end citizen reporting workflows.
"""

import sys
import io
import tempfile
from pathlib import Path
from datetime import date

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app import create_app
from app.extensions import db
from app.models import User, ReportCategory, IncidentReport, EvidenceFile


def setup_test_app():
    """Sets up an isolated test app with temp upload dir and in-memory DB."""
    temp_dir = tempfile.mkdtemp()
    app = create_app("testing")
    app.config["UPLOAD_FOLDER"] = Path(temp_dir)

    with app.app_context():
        db.create_all()

        # Seed categories
        c1 = ReportCategory(category_name="Cyberbullying", description="Harassment online.")
        c2 = ReportCategory(category_name="Impersonation", description="Fake profile.")
        db.session.add_all([c1, c2])

        # Seed test user
        user = User(full_name="Sarah Connor", email="sarah@test.com", role="user")
        user.set_password("SecretPass123")
        db.session.add(user)
        db.session.commit()

    return app


def test_home_page_renders():
    """Tests that the public home landing page renders HTML with 200 OK."""
    app = setup_test_app()
    client = app.test_client()

    res = client.get("/", headers={"Accept": "text/html"})
    assert res.status_code == 200
    assert b"Secure Digital Abuse Reporting Platform" in res.data
    assert b"File a Report" in res.data
    assert b"Track Existing Complaint" in res.data


def test_browser_registration_flow():
    """Tests browser registration form GET and POST with redirect to login."""
    app = setup_test_app()
    client = app.test_client()

    # GET registration page
    res_get = client.get("/register", headers={"Accept": "text/html"})
    assert res_get.status_code == 200
    assert b"Citizen Registration" in res_get.data

    # POST browser registration form
    form_data = {
        "browser_submit": "1",
        "full_name": "New Citizen",
        "email": "new.citizen@example.com",
        "password": "Password123"
    }
    res_post = client.post("/register", data=form_data, follow_redirects=True)
    assert res_post.status_code == 200
    assert b"Registration successful!" in res_post.data
    assert b"Sign In to Your Account" in res_post.data


def test_browser_registration_validation_error():
    """Tests that invalid form data re-renders registration with flash alert."""
    app = setup_test_app()
    client = app.test_client()

    form_data = {
        "browser_submit": "1",
        "full_name": "New Citizen",
        "email": "invalid-email",
        "password": "Password123"
    }
    res = client.post("/register", data=form_data)
    assert res.status_code == 400
    assert b"Please enter a valid email address" in res.data


def test_browser_login_and_logout_flow():
    """Tests browser login form GET, POST, dashboard redirect, and logout."""
    app = setup_test_app()
    client = app.test_client()

    # GET login page
    res_get = client.get("/login", headers={"Accept": "text/html"})
    assert res_get.status_code == 200
    assert b"Sign In to Your Account" in res_get.data

    # POST valid login credentials
    login_data = {
        "browser_submit": "1",
        "email": "sarah@test.com",
        "password": "SecretPass123"
    }
    res_post = client.post("/login", data=login_data, follow_redirects=True)
    assert res_post.status_code == 200
    assert b"Welcome back, Sarah Connor!" in res_post.data
    assert b"My Submitted Reports" in res_post.data

    # Test browser logout
    res_logout = client.get("/logout", headers={"Accept": "text/html"}, follow_redirects=True)
    assert res_logout.status_code == 200
    assert b"You have been signed out" in res_logout.data


def test_browser_login_invalid_credentials():
    """Tests that bad password flashes error and re-renders login form."""
    app = setup_test_app()
    client = app.test_client()

    login_data = {
        "browser_submit": "1",
        "email": "sarah@test.com",
        "password": "WrongPassword999"
    }
    res = client.post("/login", data=login_data)
    assert res.status_code == 401
    assert b"Invalid email or password" in res.data


def test_browser_report_submission_flow():
    """Tests submitting a complaint via browser form with evidence upload and auto-redirect to tracker."""
    app = setup_test_app()
    client = app.test_client()

    # Unauthenticated GET /report redirects to login
    res_unauth = client.get("/report", headers={"Accept": "text/html"})
    assert res_unauth.status_code == 302
    assert "/login" in res_unauth.headers["Location"]

    # Log in first
    client.post("/login", data={"browser_submit": "1", "email": "sarah@test.com", "password": "SecretPass123"})

    # Authenticated GET /report renders form
    res_form = client.get("/report", headers={"Accept": "text/html"})
    assert res_form.status_code == 200
    assert b"Submit an Incident Report" in res_form.data
    assert b"Cyberbullying" in res_form.data

    # Submit report with evidence file
    evidence_file = (io.BytesIO(b"EvidenceFileContent"), "chat_screenshot.png")
    form_data = {
        "browser_submit": "1",
        "title": "Online Harassment in Group Chat",
        "category_id": "1",
        "incident_platform": "WhatsApp",
        "incident_date": "2026-11-10",
        "description": "Repeated offensive and threatening comments targeted at me.",
        "evidence": evidence_file
    }
    res_submit = client.post("/report", data=form_data, follow_redirects=True)
    assert res_submit.status_code == 200
    assert b"Incident report submitted successfully!" in res_submit.data
    assert b"COMPLAINT REFERENCE" in res_submit.data
    assert b"Status: Pending" in res_submit.data
    assert b"chat_screenshot.png" in res_submit.data


def test_browser_my_reports_and_tracking_pages():
    """Tests viewing My Reports table and tracking a complaint in the browser."""
    app = setup_test_app()
    client = app.test_client()

    # Log in and create a report
    client.post("/login", data={"browser_submit": "1", "email": "sarah@test.com", "password": "SecretPass123"})
    client.post("/report", data={
        "browser_submit": "1",
        "title": "Stalking Incident",
        "category_id": "1",
        "incident_platform": "Instagram",
        "incident_date": "2026-11-08",
        "description": "Persistent unwanted direct messages and threats."
    })

    # View My Reports page in browser
    res_my_reports = client.get("/my-reports", headers={"Accept": "text/html"})
    assert res_my_reports.status_code == 200
    assert b"Stalking Incident" in res_my_reports.data
    assert b"Instagram" in res_my_reports.data

    # Test Track Search page
    res_track_search = client.get("/track", headers={"Accept": "text/html"})
    assert res_track_search.status_code == 200
    assert b"Complaint Status Tracker" in res_track_search.data


if __name__ == "__main__":
    test_home_page_renders()
    test_browser_registration_flow()
    test_browser_registration_validation_error()
    test_browser_login_and_logout_flow()
    test_browser_login_invalid_credentials()
    test_browser_report_submission_flow()
    test_browser_my_reports_and_tracking_pages()
    print("✓ All browser routes and interactive HTML form tests passed successfully!")
