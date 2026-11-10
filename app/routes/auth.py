"""
Authentication Routes Blueprint.
Implements user registration, login, logout, session status,
and role-based administrative verification endpoints for both browser and API clients.
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session
from app.services.auth_service import (
    validate_registration_input,
    validate_login_input,
    register_user,
    authenticate_user,
    login_user_session,
    logout_user_session,
    get_current_user,
    login_required,
    admin_required
)

auth_bp = Blueprint("auth", __name__)


def _get_request_data() -> dict:
    """Extracts payload data from either JSON or form input."""
    if request.is_json and request.get_json():
        return request.get_json()
    if request.form:
        return request.form.to_dict()
    return {}


# ============================================================================
# Browser & API Registration Endpoints
# ============================================================================

@auth_bp.route("/register", methods=["GET", "POST"], endpoint="register_page")
@auth_bp.route("/auth/register", methods=["GET", "POST"], endpoint="register")
@auth_bp.route("/auth/api/register", methods=["POST"], endpoint="api_register")
def register():
    """
    User Registration Endpoint.
    - GET: Renders the registration HTML form.
    - POST (Browser): Validates input, creates account, flashes message, redirects to /login.
    - POST (API/JSON): Returns 201 Created or 400/409 JSON responses.
    """
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("citizen.my_reports_page"))
        return render_template("auth/register.html")

    data = _get_request_data()
    is_browser = data.get("browser_submit") == "1"

    # Step 1: Input Validation
    is_valid, validation_error = validate_registration_input(data)
    if not is_valid:
        if is_browser:
            flash(validation_error, "danger")
            return render_template("auth/register.html"), 400
        return jsonify({
            "success": False,
            "error": validation_error
        }), 400

    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    role = data.get("role", "user")
    ip_address = request.remote_addr

    # Step 2: User Creation with Password Hashing & Duplicate Check
    user, reg_error = register_user(
        full_name=full_name,
        email=email,
        password=password,
        role=role,
        ip_address=ip_address
    )

    if reg_error:
        if is_browser:
            flash(reg_error, "danger")
            return render_template("auth/register.html"), 409
        return jsonify({
            "success": False,
            "error": reg_error
        }), 409

    if is_browser:
        flash("Registration successful! Please sign in with your credentials.", "success")
        return redirect(url_for("auth.login_page"))

    return jsonify({
        "success": True,
        "message": "User registered successfully.",
        "user": user.to_dict()
    }), 201


# ============================================================================
# Browser & API Login Endpoints
# ============================================================================

@auth_bp.route("/login", methods=["GET", "POST"], endpoint="login_page")
@auth_bp.route("/auth/login", methods=["GET", "POST"], endpoint="login")
@auth_bp.route("/auth/api/login", methods=["POST"], endpoint="api_login")
def login():
    """
    User Login Endpoint.
    - GET: Renders the sign-in HTML form.
    - POST (Browser): Authenticates, establishes session, flashes message, redirects to dashboard.
    - POST (API/JSON): Returns 200 OK with session or 400/401 JSON responses.
    """
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("citizen.my_reports_page"))
        return render_template("auth/login.html")

    data = _get_request_data()
    is_browser = data.get("browser_submit") == "1"

    # Step 1: Input Validation
    is_valid, validation_error = validate_login_input(data)
    if not is_valid:
        if is_browser:
            flash(validation_error, "danger")
            return render_template("auth/login.html"), 400
        return jsonify({
            "success": False,
            "error": validation_error
        }), 400

    email = data.get("email", "").strip()
    password = data.get("password", "")
    ip_address = request.remote_addr

    # Step 2: Authenticate against stored password hash
    user, auth_error = authenticate_user(email, password, ip_address=ip_address)
    if auth_error:
        if is_browser:
            flash(auth_error, "danger")
            return render_template("auth/login.html"), 401
        return jsonify({
            "success": False,
            "error": auth_error
        }), 401

    # Step 3: Establish Session
    login_user_session(user)

    if is_browser:
        session["_browser_session"] = True
        flash(f"Welcome back, {user.full_name}!", "success")
        next_url = request.form.get("next") or request.args.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)
        return redirect(url_for("citizen.my_reports_page"))

    return jsonify({
        "success": True,
        "message": "Login successful.",
        "user": user.to_dict()
    }), 200


# ============================================================================
# Logout Endpoints
# ============================================================================

@auth_bp.route("/logout", methods=["GET", "POST"], endpoint="logout_page")
@auth_bp.route("/auth/logout", methods=["GET", "POST"], endpoint="logout")
@auth_bp.route("/auth/api/logout", methods=["POST"], endpoint="api_logout")
def logout():
    """
    User Logout Endpoint.
    Clears active session and logs audit trail.
    """
    ip_address = request.remote_addr
    logout_user_session(ip_address=ip_address)

    is_browser = (
        request.method == "GET"
        or "text/html" in request.headers.get("Accept", "")
        and "application/json" not in request.headers.get("Accept", "")
    )

    if is_browser:
        flash("You have been signed out successfully.", "info")
        return redirect(url_for("auth.login_page"))

    return jsonify({
        "success": True,
        "message": "Logged out successfully."
    }), 200


# ============================================================================
# Session Inspection & Admin Verification
# ============================================================================

@auth_bp.route("/auth/me", methods=["GET"])
@auth_bp.route("/auth/api/me", methods=["GET"])
@login_required
def get_profile():
    """Current Session Profile Endpoint."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({
            "success": False,
            "error": "User record not found."
        }), 404

    return jsonify({
        "success": True,
        "user": current_user.to_dict()
    }), 200


@auth_bp.route("/auth/admin/check", methods=["GET"])
@auth_bp.route("/auth/api/admin/check", methods=["GET"])
@admin_required
def admin_verification():
    """Admin Verification Endpoint."""
    current_user = get_current_user()
    return jsonify({
        "success": True,
        "message": "Admin authorization verified successfully.",
        "admin": current_user.to_dict()
    }), 200
