"""
Secure File Handling & Validation Service.
Enforces strict security checks on uploaded evidence:
1. Allowed extension whitelist validation (e.g., png, jpg, jpeg, pdf, mp4, txt)
2. Safe unique filename generation with UUID prefixing to prevent collisions and path traversal
3. Maximum file size restrictions (up to 16 MB)
4. Storage strictly inside isolated uploads directory (outside app/static/)
5. SHA-256 integrity checksumming
"""

import os
import uuid
import hashlib
import mimetypes
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from werkzeug.utils import secure_filename

# Whitelist of strictly permitted file extensions for digital abuse evidence
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf", "mp4", "txt"}

# Maximum allowed file size in bytes: 16 MB
MAX_FILE_SIZE = 16 * 1024 * 1024


def allowed_file(filename: str) -> bool:
    """
    Checks if a filename contains an allowed extension.
    Example: 'screenshot.png' -> True, 'script.exe' -> False
    """
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def sanitize_and_save_evidence(
    file_storage,
    upload_folder: Path | str
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Validates, sanitizes, checksums, and securely saves an uploaded evidence file.

    Args:
        file_storage: Werkzeug FileStorage object from request.files
        upload_folder: Path or string pointing to the secure uploads/evidence directory

    Returns:
        (metadata_dict, None) on success.
        (None, error_message) on failure.
    """
    if not file_storage or not file_storage.filename:
        return None, "No file was selected for upload."

    raw_filename = file_storage.filename.strip()

    # Step 1: Whitelist extension check
    if not allowed_file(raw_filename):
        allowed_list = ", ".join(f".{ext}" for ext in sorted(ALLOWED_EXTENSIONS))
        return None, f"Unsupported file type. Permitted formats are: {allowed_list}"

    # Step 2: Sanitize original filename (remove directory traversals like ../ or special characters)
    clean_original = secure_filename(raw_filename)
    if not clean_original:
        clean_original = "evidence_file"

    # Step 3: Extract extension and generate collision-proof, unguessable stored filename
    ext = raw_filename.rsplit(".", 1)[1].lower()
    stored_filename = f"ev_{uuid.uuid4().hex}.{ext}"

    # Ensure upload directory exists
    folder_path = Path(upload_folder).resolve()
    folder_path.mkdir(parents=True, exist_ok=True)
    target_path = folder_path / stored_filename

    # Step 4: Stream file content, verify size, and compute SHA-256 checksum
    hasher = hashlib.sha256()
    file_size = 0

    try:
        # Seek to start
        file_storage.seek(0)
        with open(target_path, "wb") as destination:
            while chunk := file_storage.read(64 * 1024):  # 64 KB chunks
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE:
                    # Clean up partially written file
                    destination.close()
                    if target_path.exists():
                        target_path.unlink()
                    return None, f"File exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)} MB."
                hasher.update(chunk)
                destination.write(chunk)
    except Exception as e:
        if target_path.exists():
            target_path.unlink()
        return None, f"Failed to save evidence file safely: {str(e)}"

    # Determine MIME type
    mime_type, _ = mimetypes.guess_type(clean_original)
    if not mime_type:
        mime_type = file_storage.mimetype or "application/octet-stream"

    return {
        "original_filename": clean_original,
        "stored_filename": stored_filename,
        "file_path": str(target_path),
        "file_type": mime_type,
        "file_size": file_size,
        "checksum": hasher.hexdigest(),
    }, None


def get_safe_evidence_path(stored_filename: str, upload_folder: Path | str) -> Optional[Path]:
    """
    Guarantees the requested stored filename resolves strictly within the upload folder,
    preventing Path Traversal vulnerabilities (e.g. ../../etc/passwd).
    """
    if not stored_filename or "/" in stored_filename or "\\" in stored_filename or ".." in stored_filename:
        return None

    folder_path = Path(upload_folder).resolve()
    target_file = (folder_path / stored_filename).resolve()

    # Ensure target_file is strictly inside folder_path
    try:
        target_file.relative_to(folder_path)
    except ValueError:
        return None

    if not target_file.is_file():
        return None

    return target_file
