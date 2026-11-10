"""
Authentication & Authorization Service.
Handles input validation, user registration, authentication, session state,
and role-based access control (RBAC) decorators.
"""

import re
from functools import wraps
from typing import Optional, Tuple
from flask import session, request, jsonify, redirect, url_for
from app.extensions import db
from app.models import User
from app.services.audit_service import log_audit

# RFC 5322 standard compliant basic regex for email validation
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validate_registration_input(data: dict) -> Tuple[bool, Optional[str]]:
    """
    Validates user registration input fields.
    
    Checks:
    - full_name is provided, non-empty, between 2 and 100 characters.
    - email is provided and matches a valid email format.
    - password is at least 8 characters long and contains both letters and digits.
    """
    if not isinstance(data, dict):
        return False, "Request body must be a valid JSON object or form."

    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not full_name:
        return False, "Full name is required."
    if len(full_name) < 2 or len(full_name) > 100:
        return False, "Full name must be between 2 and 100 characters."

    if not email:
        return False, "Email address is required."
    if len(email) > 120 or not EMAIL_REGEX.match(email):
        return False, "Please enter a valid email address."

    if not password:
        return False, "Password is required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(char.isalpha() for char in password):
        return False, "Password must contain at least one letter."
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one number."

    return True, None


def validate_login_input(data: dict) -> Tuple[bool, Optional[str]]:
    """Validates login credentials presence."""
    if not isinstance(data, dict):
        return False, "Request body must be a valid JSON object or form."

    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email:
        return False, "Email address is required."
    if not password:
        return False, "Password is required."

    return True, None


def register_user(
    full_name: str,
    email: str,
    password: str,
    role: str = "user",
    ip_address: Optional[str] = None
) -> Tuple[Optional[User], Optional[str]]:
    """
    Registers a new user account with hashed password and checks for duplicates.
    
    Returns:
        (User, None) on success.
        (None, error_message) on failure.
    """
    normalized_email = email.strip().lower()

    # Prevent duplicate email registrations
    existing_user = User.query.filter_by(email=normalized_email).first()
    if existing_user:
        return None, "An account with this email address already exists."

    # Validate role assignment (only 'user' and 'admin' allowed)
    safe_role = "admin" if role.lower() == "admin" else "user"

    new_user = User(
        full_name=full_name.strip(),
        email=normalized_email,
        role=safe_role
    )
    # Secure password hashing (never stores plain-text password)
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    # Record registration in immutable audit trail
    log_audit(
        action="USER_REGISTERED",
        description=f"New account registered: {normalized_email} (Role: {safe_role})",
        user_id=new_user.id,
        ip_address=ip_address
    )

    return new_user, None


def authenticate_user(
    email: str,
    password: str,
    ip_address: Optional[str] = None
) -> Tuple[Optional[User], Optional[str]]:
    """
    Authenticates user credentials against the stored password hash.
    
    Returns:
        (User, None) on successful authentication.
        (None, error_message) on failed authentication.
    """
    normalized_email = email.strip().lower()
    user = User.query.filter_by(email=normalized_email).first()

    # Constant-time comparison logic through check_password
    if not user or not user.check_password(password):
        log_audit(
            action="LOGIN_FAILED",
            description=f"Failed login attempt for email: {normalized_email}",
            user_id=user.id if user else None,
            ip_address=ip_address
        )
        return None, "Invalid email or password."

    log_audit(
        action="LOGIN_SUCCESS",
        description=f"Successful login for user: {user.email}",
        user_id=user.id,
        ip_address=ip_address
    )
    return user, None


def login_user_session(user: User) -> None:
    """Sets session variables for authenticated user."""
    session.clear()
    session["user_id"] = user.id
    session["role"] = user.role
    session["full_name"] = user.full_name
    session["email"] = user.email
    session.permanent = True


def logout_user_session(ip_address: Optional[str] = None) -> None:
    """Clears user session and logs the logout event."""
    user_id = session.get("user_id")
    if user_id:
        log_audit(
            action="USER_LOGOUT",
            description=f"User ID {user_id} logged out.",
            user_id=user_id,
            ip_address=ip_address
        )
    session.clear()


def get_current_user() -> Optional[User]:
    """Retrieves current logged-in User instance from session."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


# ============================================================================
# Role-Based Access Control (RBAC) Decorators
# ============================================================================

def login_required(f):
    """Decorator requiring an active user session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            accept = request.headers.get("Accept", "")
            if "text/html" in accept and "application/json" not in accept:
                try:
                    return redirect(url_for("auth.login"))
                except Exception:
                    pass
            return jsonify({
                "success": False,
                "error": "Authentication required. Please log in to access this resource."
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def role_required(*allowed_roles: str):
    """Decorator enforcing specific role permissions (e.g. 'admin', 'user')."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get("user_id")
            if not user_id:
                accept = request.headers.get("Accept", "")
                if "text/html" in accept and "application/json" not in accept:
                    try:
                        return redirect(url_for("auth.login"))
                    except Exception:
                        pass
                return jsonify({
                    "success": False,
                    "error": "Authentication required. Please log in to access this resource."
                }), 401

            user_role = session.get("role", "user")
            if user_role not in allowed_roles:
                return jsonify({
                    "success": False,
                    "error": "Access denied. Insufficient permissions for this action."
                }), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """Convenience decorator protecting administrative-only routes."""
    return role_required("admin")(f)
