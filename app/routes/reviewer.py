"""
Reviewer & Admin Dashboard Routes Blueprint.
Manages case reviews, status escalation/resolution, evidence inspection, and audit log viewing.
"""

from flask import Blueprint

reviewer_bp = Blueprint("reviewer", __name__, url_prefix="/reviewer")

# Starter endpoints to be implemented:
# - GET /dashboard: Overview dashboard with metrics (pending, escalated, resolved reports)
# - GET /reports: Filterable list of complaints by category, severity, status, and date
# - GET/POST /reports/<int:report_id>: Detailed case view, status updater, internal notes
# - GET /audit-logs: View audit trails of actions taken on complaints (Admin only)
