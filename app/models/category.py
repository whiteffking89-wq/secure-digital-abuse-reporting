"""
Report Category Model.
Represents standardized digital abuse classification categories.
"""

from app.extensions import db


class ReportCategory(db.Model):
    """
    Standardized categories of digital abuse (e.g. Cyberbullying, Harassment, Impersonation).
    """
    __tablename__ = "report_categories"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category_name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)

    # Relationships
    reports = db.relationship(
        "IncidentReport",
        back_populates="category",
        lazy="dynamic"
    )

    def to_dict(self) -> dict:
        """Serializes report category to a dictionary."""
        return {
            "id": self.id,
            "category_name": self.category_name,
            "description": self.description,
        }

    def __repr__(self) -> str:
        return f"<ReportCategory id={self.id} name='{self.category_name}'>"
