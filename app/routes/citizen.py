"""
Citizen / Reporter Routes Blueprint.
Manages digital abuse complaint submission, evidence file association,
unique reference code generation, status tracking, and report history
for both interactive web browser users and JSON API clients.
"""

import uuid
from datetime import datetime, date, timezone
from flask import (
    Blueprint,
    request,
    jsonify,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    current_app
)
from app.extensions import db
from app.models import IncidentReport, EvidenceFile, ReportCategory, Notification
from app.services.auth_service import login_required, get_current_user
from app.services.file_service import sanitize_and_save_evidence
from app.services.audit_service import log_audit

citizen_bp = Blueprint("citizen", __name__)


def generate_unique_report_number() -> str:
    """
    Generates an unguessable, collision-free tracking reference code.
    Format: REP-YYYY-<8-HEX> (e.g., 'REP-2026-F9A8C2B1')
    """
    year = datetime.now().year
    while True:
        token = uuid.uuid4().hex[:8].upper()
        candidate = f"REP-{year}-{token}"
        existing = IncidentReport.query.filter_by(report_number=candidate).first()
        if not existing:
            return candidate


# ============================================================================
# Home Page
# ============================================================================

@citizen_bp.route("/", methods=["GET"])
def index():
    """Renders the public portal landing page."""
    return render_template("citizen/index.html")


# ============================================================================
# Categories Endpoint
# ============================================================================

@citizen_bp.route("/categories", methods=["GET"])
@citizen_bp.route("/api/categories", methods=["GET"])
def get_categories():
    """Returns available standardized digital abuse report categories."""
    categories = ReportCategory.query.order_by(ReportCategory.category_name).all()
    return jsonify({
        "success": True,
        "categories": [c.to_dict() for c in categories]
    }), 200


# ============================================================================
# Incident Report Submission (Browser & API)
# ============================================================================

@citizen_bp.route("/report", methods=["GET", "POST"], endpoint="report_page")
@citizen_bp.route("/api/report", methods=["POST"], endpoint="api_report")
@login_required
def submit_report():
    """
    Incident Report Submission Endpoint.
    - GET: Renders the incident reporting form.
    - POST (Browser): Validates, uploads evidence, flashes message, redirects to tracker.
    - POST (API/JSON): Returns 201 Created or 400 Bad Request JSON responses.
    """
    if request.method == "GET":
        categories = ReportCategory.query.order_by(ReportCategory.category_name).all()
        today_str = date.today().isoformat()
        return render_template("citizen/report.html", categories=categories, today_str=today_str)

    # Extract data from either multipart form or JSON
    if request.is_json and request.get_json():
        data = request.get_json()
    else:
        data = request.form.to_dict()

    user_id = session.get("user_id")
    is_browser = data.get("browser_submit") == "1" or session.get("_browser_session") is True

    # Helper for rendering form error
    def _render_form_error(error_msg: str, status_code: int = 400):
        if is_browser:
            flash(error_msg, "danger")
            categories = ReportCategory.query.order_by(ReportCategory.category_name).all()
            today_str = date.today().isoformat()
            return render_template("citizen/report.html", categories=categories, today_str=today_str), status_code
        return jsonify({"success": False, "error": error_msg}), status_code

    # 1. Validate Title
    title = data.get("title", "").strip()
    if not title:
        return _render_form_error("Report title is required.")
    if len(title) < 3 or len(title) > 200:
        return _render_form_error("Title must be between 3 and 200 characters.")

    # 2. Validate Category ID
    category_id = data.get("category_id")
    if not category_id:
        return _render_form_error("Abuse category is required.")
    try:
        category_id = int(category_id)
    except (ValueError, TypeError):
        return _render_form_error("Category ID must be an integer.")

    category = db.session.get(ReportCategory, category_id)
    if not category:
        return _render_form_error(f"Invalid category ID '{category_id}'.")

    # 3. Validate Description
    description = data.get("description", "").strip()
    if not description:
        return _render_form_error("Incident description is required.")
    if len(description) < 10:
        return _render_form_error("Description must be at least 10 characters long.")

    # 4. Validate Incident Date
    incident_date_str = data.get("incident_date", "").strip()
    if not incident_date_str:
        return _render_form_error("Incident date is required (format: YYYY-MM-DD).")
    try:
        parsed_date = datetime.strptime(incident_date_str, "%Y-%m-%d").date()
    except ValueError:
        return _render_form_error("Incident date must be in YYYY-MM-DD format.")

    if parsed_date > date.today():
        return _render_form_error("Incident date cannot be in the future.")

    # 5. Validate Incident Platform
    incident_platform = data.get("incident_platform", "").strip()
    if not incident_platform:
        return _render_form_error("Incident platform is required (e.g., WhatsApp, Instagram, Telegram).")
    if len(incident_platform) > 100:
        return _render_form_error("Incident platform name is too long.")

    # 6. Generate Unique Tracking Reference Number
    report_number = generate_unique_report_number()

    # 7. Create Incident Report Record
    report = IncidentReport(
        report_number=report_number,
        user_id=user_id,
        category_id=category_id,
        title=title,
        description=description,
        incident_date=parsed_date,
        incident_platform=incident_platform,
        status=IncidentReport.STATUS_PENDING
    )
    db.session.add(report)
    db.session.flush()

    # 8. Process Uploaded Evidence Files
    evidence_records = []
    upload_folder = current_app.config["UPLOAD_FOLDER"]

    files_to_process = []
    if "evidence" in request.files:
        files_to_process = request.files.getlist("evidence")

    for file_storage in files_to_process:
        if not file_storage or not file_storage.filename:
            continue

        file_metadata, file_error = sanitize_and_save_evidence(file_storage, upload_folder)
        if file_error:
            db.session.rollback()
            return _render_form_error(file_error, 400)

        evidence_entry = EvidenceFile(
            report_id=report.id,
            original_filename=file_metadata["original_filename"],
            stored_filename=file_metadata["stored_filename"],
            file_path=file_metadata["file_path"],
            file_type=file_metadata["file_type"]
        )
        db.session.add(evidence_entry)
        evidence_records.append(evidence_entry)

    # 9. Create Citizen Notification
    notification = Notification(
        user_id=user_id,
        report_id=report.id,
        message=f"Your complaint ({report_number}) has been registered and is pending review.",
        is_read=False
    )
    db.session.add(notification)

    # 10. Record Security Audit Log
    log_audit(
        action="REPORT_SUBMITTED",
        description=f"Complaint {report_number} submitted by user ID {user_id}. Evidence files: {len(evidence_records)}.",
        user_id=user_id,
        ip_address=request.remote_addr
    )

    db.session.commit()

    if is_browser:
        flash(f"Incident report submitted successfully! Reference ID: {report.report_number}", "success")
        return redirect(url_for("citizen.track_page", report_number=report.report_number))

    return jsonify({
        "success": True,
        "message": "Incident report submitted successfully.",
        "report": {
            "id": report.id,
            "report_number": report.report_number,
            "title": report.title,
            "category": category.category_name,
            "incident_date": report.incident_date.isoformat(),
            "incident_platform": report.incident_platform,
            "status": report.status,
            "created_at": report.created_at.isoformat(),
            "evidence_files": [e.to_dict() for e in evidence_records]
        }
    }), 201


# ============================================================================
# Citizen Reports History (Browser & API)
# ============================================================================

@citizen_bp.route("/my-reports", methods=["GET"], endpoint="my_reports_page")
@citizen_bp.route("/api/my-reports", methods=["GET"], endpoint="api_my_reports")
@login_required
def get_my_reports():
    """
    Returns reports submitted by the logged-in citizen.
    - Browser: Renders the my_reports.html template with reports table.
    - API: Returns JSON list of reports.
    """
    user_id = session.get("user_id")
    reports = (
        IncidentReport.query.filter_by(user_id=user_id)
        .order_by(IncidentReport.created_at.desc())
        .all()
    )

    # Determine whether the client expects HTML or JSON
    accept = request.headers.get("Accept", "").strip()
    is_html = (
        session.get("_browser_session") is True
        or request.args.get("format") == "html"
        or ("text/html" in accept and "*/*" != accept)
    )

    if is_html and not request.path.startswith("/api/"):
        return render_template("citizen/my_reports.html", reports=reports)

    result = []
    for r in reports:
        report_dict = r.to_dict()
        report_dict["evidence_count"] = r.evidence_files.count()
        result.append(report_dict)

    return jsonify({
        "success": True,
        "count": len(result),
        "reports": result
    }), 200


# ============================================================================
# Complaint Tracking Endpoints (Browser & API)
# ============================================================================

@citizen_bp.route("/track", methods=["GET"], endpoint="track_search_page")
def track_search():
    """Renders the complaint tracking search page."""
    return render_template("citizen/track.html", report=None)


@citizen_bp.route("/track", methods=["POST"], endpoint="track_search_submit")
def track_search_post():
    """Handles tracking search form submission and redirects to the report status page."""
    report_number = request.form.get("report_number", "").strip().upper()
    if not report_number:
        flash("Please enter a valid complaint reference code.", "warning")
        return redirect(url_for("citizen.track_search_page"))
    return redirect(url_for("citizen.track_page", report_number=report_number))


@citizen_bp.route("/track/<string:report_number>", methods=["GET"], endpoint="track_page")
@citizen_bp.route("/api/track/<string:report_number>", methods=["GET"], endpoint="api_track")
def track_report(report_number: str):
    """
    Status Tracking Endpoint.
    - Browser: Renders status card with progress badge and evidence links if authorized.
    - API: Returns JSON status payload.
    """
    clean_code = report_number.strip().upper()
    report = IncidentReport.query.filter_by(report_number=clean_code).first()

    # Determine whether the client expects HTML or JSON
    accept = request.headers.get("Accept", "").strip()
    is_html = (
        session.get("_browser_session") is True
        or request.args.get("format") == "html"
        or ("text/html" in accept and "*/*" != accept)
    )

    if not is_html or request.path.startswith("/api/"):
        if not report:
            return jsonify({
                "success": False,
                "error": f"No incident report found with reference code '{clean_code}'."
            }), 404

        current_user_id = session.get("user_id")
        is_admin = session.get("role") == "admin"
        is_owner = current_user_id is not None and report.user_id == current_user_id

        payload = {
            "report_number": report.report_number,
            "status": report.status,
            "category": report.category.category_name if report.category else "Unknown",
            "incident_platform": report.incident_platform,
            "incident_date": report.incident_date.isoformat(),
            "created_at": report.created_at.isoformat(),
            "updated_at": report.updated_at.isoformat(),
        }

        if is_owner or is_admin:
            payload["title"] = report.title
            payload["description"] = report.description
            payload["evidence_files"] = [e.to_dict() for e in report.evidence_files.all()]

        return jsonify({
            "success": True,
            "report": payload
        }), 200

    # HTML browser rendering
    if not report:
        flash(f"No incident report found with reference code '{clean_code}'.", "danger")
        return render_template("citizen/track.html", report=None, searched_number=clean_code), 404

    current_user_id = session.get("user_id")
    is_admin = session.get("role") == "admin"
    is_owner = current_user_id is not None and report.user_id == current_user_id

    return render_template(
        "citizen/track.html",
        report=report,
        is_owner=is_owner,
        is_admin=is_admin,
        searched_number=clean_code
    )
