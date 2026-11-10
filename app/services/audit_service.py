"""
Audit Trail & Security Logging Service.
Records immutable activity logs for user actions, authentication attempts,
and administrative operations.
"""

from typing import Optional
from app.extensions import db
from app.models import AuditLog


def log_audit(
    action: str,
    description: Optional[str] = None,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None
) -> AuditLog:
    """
    Creates and persists an immutable audit log entry.
    
    Args:
        action: Short uppercase identifier (e.g. 'LOGIN_SUCCESS', 'LOGIN_FAILED', 'USER_REGISTERED')
        description: Human-readable narrative detailing the action or security event.
        user_id: ID of the user performing the action (nullable for unauthenticated attempts).
        ip_address: Client IP address.
        
    Returns:
        AuditLog: The persisted audit log entity.
    """
    audit_entry = AuditLog(
        user_id=user_id,
        action=action,
        description=description,
        ip_address=ip_address
    )
    db.session.add(audit_entry)
    db.session.commit()
    return audit_entry
