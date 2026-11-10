"""
Audit Log and Notification Models.
Handles security auditing of user and administrative actions,
as well as citizen status notifications.
"""

from datetime import datetime, timezone
from app.extensions import db


class AuditLog(db.Model):
    """
    Immutable audit log for security accountability.
    Tracks critical system events (e.g. login, status transition, evidence access).
    """
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # Supports IPv4 and IPv6
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    user = db.relationship("User", back_populates="audit_logs")

    def to_dict(self) -> dict:
        """Serializes audit log entry."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "description": self.description,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action='{self.action}' user_id={self.user_id}>"


class Notification(db.Model):
    """
    User notification entity for status updates and alerts.
    """
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    report_id = db.Column(db.Integer, db.ForeignKey("incident_reports.id", ondelete="CASCADE"), nullable=True, index=True)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = db.relationship("User", back_populates="notifications")
    report = db.relationship("IncidentReport", back_populates="notifications")

    def to_dict(self) -> dict:
        """Serializes notification."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "report_id": self.report_id,
            "message": self.message,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Notification id={self.id} user_id={self.user_id} read={self.is_read}>"
