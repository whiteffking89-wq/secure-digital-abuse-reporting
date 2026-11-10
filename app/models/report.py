"""
Incident Report and Evidence File Models.
Handles digital abuse complaint tracking, incident details, categories,
and secure file upload metadata (without storing binary content in the database).
"""

from datetime import datetime, date, timezone
from app.extensions import db


class IncidentReport(db.Model):
    """
    Incident Report entity.
    Tracks digital abuse complaints, platform channels, submission dates,
    and reviewer status progression.
    """
    __tablename__ = "incident_reports"

    # Status Constants
    STATUS_PENDING = "Pending"
    STATUS_UNDER_REVIEW = "Under Review"
    STATUS_RESOLVED = "Resolved"
    STATUS_REJECTED = "Rejected"

    VALID_STATUSES = {
        STATUS_PENDING,
        STATUS_UNDER_REVIEW,
        STATUS_RESOLVED,
        STATUS_REJECTED,
    }

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    report_number = db.Column(db.String(36), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("report_categories.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    incident_date = db.Column(db.Date, nullable=False, default=date.today)
    incident_platform = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(30), nullable=False, default=STATUS_PENDING, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = db.relationship("User", back_populates="reports")
    category = db.relationship("ReportCategory", back_populates="reports")
    evidence_files = db.relationship(
        "EvidenceFile",
        back_populates="report",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    notifications = db.relationship(
        "Notification",
        back_populates="report",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        """Serializes report record to dictionary."""
        return {
            "id": self.id,
            "report_number": self.report_number,
            "user_id": self.user_id,
            "category": self.category.category_name if self.category else None,
            "title": self.title,
            "description": self.description,
            "incident_date": self.incident_date.isoformat() if self.incident_date else None,
            "incident_platform": self.incident_platform,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<IncidentReport id={self.id} report_number='{self.report_number}' status='{self.status}'>"


class EvidenceFile(db.Model):
    """
    Evidence File Metadata entity.
    
    SECURITY NOTE:
    Actual file binaries are stored in the secure uploads directory (outside app/static/).
    Only sanitized metadata, stored filename, and local secure paths are kept in SQLite.
    """
    __tablename__ = "evidence_files"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    report_id = db.Column(db.Integer, db.ForeignKey("incident_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), unique=True, nullable=False, index=True)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    report = db.relationship("IncidentReport", back_populates="evidence_files")

    def to_dict(self) -> dict:
        """Serializes evidence metadata."""
        return {
            "id": self.id,
            "report_id": self.report_id,
            "original_filename": self.original_filename,
            "stored_filename": self.stored_filename,
            "file_type": self.file_type,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }

    def __repr__(self) -> str:
        return f"<EvidenceFile id={self.id} report_id={self.report_id} filename='{self.stored_filename}'>"
