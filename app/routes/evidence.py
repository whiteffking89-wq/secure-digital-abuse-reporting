"""
Secure Evidence Serving Blueprint.
Ensures uploaded digital abuse evidence files are NEVER publicly accessible.
Enforces strict authentication and role-based ownership checks before streaming any file.
"""

from pathlib import Path
from flask import Blueprint, session, jsonify, request, send_from_directory, current_app
from app.extensions import db
from app.models import EvidenceFile
from app.services.auth_service import login_required
from app.services.file_service import get_safe_evidence_path
from app.services.audit_service import log_audit

evidence_bp = Blueprint("evidence", __name__, url_prefix="/evidence")


@evidence_bp.route("/view/<int:file_id>", methods=["GET"])
@evidence_bp.route("/api/view/<int:file_id>", methods=["GET"])
@login_required
def view_evidence(file_id: int):
    """
    Secure Evidence Download / View Endpoint.
    
    Security Controls:
    1. Requires active authenticated session (@login_required).
    2. Enforces Role-Based Ownership: Only the report owner OR a verified admin can access the file.
    3. Resolves files strictly within the private upload folder to prevent path traversal.
    4. Records an immutable audit log entry for every access or unauthorized attempt.
    """
    evidence = db.session.get(EvidenceFile, file_id)
    if not evidence:
        return jsonify({
            "success": False,
            "error": "Evidence record not found."
        }), 404

    current_user_id = session.get("user_id")
    is_admin = session.get("role") == "admin"
    is_owner = evidence.report and evidence.report.user_id == current_user_id

    # Enforce Authorization Check
    if not is_owner and not is_admin:
        log_audit(
            action="UNAUTHORIZED_EVIDENCE_ACCESS_ATTEMPT",
            description=f"User ID {current_user_id} attempted unauthorized access to evidence ID {file_id}.",
            user_id=current_user_id,
            ip_address=request.remote_addr
        )
        return jsonify({
            "success": False,
            "error": "Access denied. You do not have permission to access this evidence."
        }), 403

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    safe_path = get_safe_evidence_path(evidence.stored_filename, upload_folder)
    if not safe_path:
        return jsonify({
            "success": False,
            "error": "Evidence file could not be located on disk."
        }), 404

    # Log successful evidence access in audit trail
    log_audit(
        action="EVIDENCE_ACCESSED",
        description=f"Evidence ID {file_id} (file: {evidence.stored_filename}) accessed by user ID {current_user_id}.",
        user_id=current_user_id,
        ip_address=request.remote_addr
    )

    # Determine whether to download as attachment or view inline (e.g. ?download=1)
    as_attachment = request.args.get("download", "0") in ("1", "true", "yes")

    return send_from_directory(
        directory=Path(upload_folder).resolve(),
        path=evidence.stored_filename,
        as_attachment=as_attachment,
        download_name=evidence.original_filename,
        mimetype=evidence.file_type
    )
