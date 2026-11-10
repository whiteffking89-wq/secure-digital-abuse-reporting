"""
Authentication and Role-Based Access Control (RBAC) Test Suite.
Tests registration, login, logout, password hashing, session state, input validation, and RBAC.
"""

import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app import create_app
from app.extensions import db
from app.models import User, AuditLog


def setup_test_app():
    """Helper to spin up an isolated test app instance with clean in-memory database."""
    app = create_app("testing")
    with app.app_context():
        db.create_all()
    return app


def test_user_registration_success():
    """Tests successful user registration API with valid payload."""
    app = setup_test_app()
    client = app.test_client()

    payload = {
        "full_name": "Test Citizen",
        "email": "citizen.test@example.com",
        "password": "Password123"
    }
    response = client.post("/auth/register", json=payload)
    data = response.get_json()

    assert response.status_code == 201
    assert data["success"] is True
    assert data["user"]["email"] == "citizen.test@example.com"
    assert data["user"]["full_name"] == "Test Citizen"
    assert data["user"]["role"] == "user"
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]

    # Verify password was hashed in the database
    with app.app_context():
        user = User.query.filter_by(email="citizen.test@example.com").first()
        assert user is not None
        assert user.password_hash != "Password123"
        assert user.check_password("Password123") is True

        # Verify audit log was created
        audit = AuditLog.query.filter_by(user_id=user.id, action="USER_REGISTERED").first()
        assert audit is not None


def test_user_registration_duplicate_email():
    """Tests that registering with an existing email returns 409 Conflict."""
    app = setup_test_app()
    client = app.test_client()

    payload = {
        "full_name": "First User",
        "email": "duplicate@example.com",
        "password": "Password123"
    }
    # First registration
    res1 = client.post("/auth/register", json=payload)
    assert res1.status_code == 201

    # Second registration with duplicate email
    res2 = client.post("/auth/register", json=payload)
    data2 = res2.get_json()
    assert res2.status_code == 409
    assert data2["success"] is False
    assert "already exists" in data2["error"].lower()


def test_user_registration_validation():
    """Tests input validation for missing or invalid registration fields."""
    app = setup_test_app()
    client = app.test_client()

    # Missing name
    res = client.post("/auth/register", json={"email": "a@b.com", "password": "Password123"})
    assert res.status_code == 400
    assert "name" in res.get_json()["error"].lower()

    # Invalid email
    res = client.post("/auth/register", json={"full_name": "Jane", "email": "not-an-email", "password": "Password123"})
    assert res.status_code == 400
    assert "valid email" in res.get_json()["error"].lower()

    # Weak password (< 8 chars)
    res = client.post("/auth/register", json={"full_name": "Jane", "email": "jane@example.com", "password": "pass1"})
    assert res.status_code == 400
    assert "8 characters" in res.get_json()["error"].lower()

    # Password missing digits
    res = client.post("/auth/register", json={"full_name": "Jane", "email": "jane@example.com", "password": "PasswordOnly"})
    assert res.status_code == 400
    assert "number" in res.get_json()["error"].lower()


def test_user_login_success():
    """Tests successful login and session establishment."""
    app = setup_test_app()
    client = app.test_client()

    # Register user first
    client.post("/auth/register", json={
        "full_name": "John Doe",
        "email": "john@example.com",
        "password": "SecretPass1"
    })

    # Log in
    res = client.post("/auth/login", json={
        "email": "john@example.com",
        "password": "SecretPass1"
    })
    data = res.get_json()
    assert res.status_code == 200
    assert data["success"] is True
    assert data["user"]["email"] == "john@example.com"

    # Verify session profile endpoint (/auth/me) works with active session
    me_res = client.get("/auth/me")
    me_data = me_res.get_json()
    assert me_res.status_code == 200
    assert me_data["success"] is True
    assert me_data["user"]["email"] == "john@example.com"

    # Verify audit log recorded LOGIN_SUCCESS
    with app.app_context():
        user = User.query.filter_by(email="john@example.com").first()
        audit = AuditLog.query.filter_by(user_id=user.id, action="LOGIN_SUCCESS").first()
        assert audit is not None


def test_user_login_unsuccessful():
    """Tests unsuccessful login with incorrect password and non-existent email."""
    app = setup_test_app()
    client = app.test_client()

    # Register user
    client.post("/auth/register", json={
        "full_name": "John Doe",
        "email": "john@example.com",
        "password": "SecretPass1"
    })

    # Wrong password
    res = client.post("/auth/login", json={
        "email": "john@example.com",
        "password": "WrongPassword99"
    })
    assert res.status_code == 401
    assert res.get_json()["success"] is False
    assert "invalid" in res.get_json()["error"].lower()

    # Non-existent email
    res2 = client.post("/auth/login", json={
        "email": "nobody@example.com",
        "password": "SecretPass1"
    })
    assert res2.status_code == 401
    assert res2.get_json()["success"] is False

    # Missing credentials
    res3 = client.post("/auth/login", json={"email": ""})
    assert res3.status_code == 400


def test_user_logout_and_session_clearing():
    """Tests logout API and ensures session is cleared."""
    app = setup_test_app()
    client = app.test_client()

    # Register and login
    client.post("/auth/register", json={
        "full_name": "Sara Connor",
        "email": "sara@example.com",
        "password": "Password99"
    })
    client.post("/auth/login", json={
        "email": "sara@example.com",
        "password": "Password99"
    })

    # Verify logged in
    res_me = client.get("/auth/me")
    assert res_me.status_code == 200

    # Logout
    logout_res = client.post("/auth/logout")
    assert logout_res.status_code == 200
    assert logout_res.get_json()["success"] is True

    # After logout, /auth/me must return 401 Unauthorized
    res_me_after = client.get("/auth/me")
    assert res_me_after.status_code == 401


def test_role_based_access_control():
    """Tests RBAC: citizen vs admin route authorization."""
    app = setup_test_app()
    client = app.test_client()

    # 1. Unauthenticated request to admin route -> 401 Unauthorized
    res_unauth = client.get("/auth/admin/check", headers={"Accept": "application/json"})
    assert res_unauth.status_code == 401

    # 2. Register regular user (role='user')
    client.post("/auth/register", json={
        "full_name": "Regular Citizen",
        "email": "citizen@example.com",
        "password": "Password123",
        "role": "user"
    })
    client.post("/auth/login", json={
        "email": "citizen@example.com",
        "password": "Password123"
    })

    # Access admin route as regular user -> 403 Forbidden
    res_forbidden = client.get("/auth/admin/check", headers={"Accept": "application/json"})
    assert res_forbidden.status_code == 403
    assert "access denied" in res_forbidden.get_json()["error"].lower()

    # 3. Register admin user (role='admin')
    client.post("/auth/logout")
    client.post("/auth/register", json={
        "full_name": "Portal Admin",
        "email": "admin@example.com",
        "password": "AdminPassword1",
        "role": "admin"
    })
    client.post("/auth/login", json={
        "email": "admin@example.com",
        "password": "AdminPassword1"
    })

    # Access admin route as admin user -> 200 OK
    res_admin = client.get("/auth/admin/check", headers={"Accept": "application/json"})
    assert res_admin.status_code == 200
    assert res_admin.get_json()["success"] is True
    assert res_admin.get_json()["admin"]["role"] == "admin"


if __name__ == "__main__":
    test_user_registration_success()
    test_user_registration_duplicate_email()
    test_user_registration_validation()
    test_user_login_success()
    test_user_login_unsuccessful()
    test_user_logout_and_session_clearing()
    test_role_based_access_control()
    print("✓ All Authentication, Session, and RBAC tests passed successfully!")
