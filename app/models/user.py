"""
User Model.
Handles user authentication, password hashing, roles (user/admin), and relationships.
"""

from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(db.Model):
    """
    User entity representing registered citizens, reviewers, and system administrators.
    Passwords are never stored in plain-text; only salted hashes are persisted.
    """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")  # 'user' or 'admin'
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    reports = db.relationship(
        "IncidentReport",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    audit_logs = db.relationship(
        "AuditLog",
        back_populates="user",
        lazy="dynamic"
    )
    notifications = db.relationship(
        "Notification",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        """
        Hashes the plain-text password using Werkzeug's secure hashing algorithm.
        Plain-text passwords are never stored in the database.
        """
        if not password:
            raise ValueError("Password cannot be empty.")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verifies a plain-text password against the stored password hash."""
        if not password or not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        """Convenience property to check if the user has an admin/reviewer role."""
        return self.role.lower() == "admin"

    def to_dict(self) -> dict:
        """Serializes user info safely without exposing the password hash."""
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<User id={self.id} email='{self.email}' role='{self.role}'>"
