"""Shared file validation utilities for CSV/Excel data sources.

Phase 13: CSV & Excel File Support

Common validation functions used by both FileSourceHandler and
FileSourceDuckDBSession to prevent path traversal and SQL injection.
"""
import re
from pathlib import Path
from typing import Optional


def validate_file_path(file_path: str, upload_dir: Path) -> str:
    """
    Validate and canonicalize file path to prevent path traversal attacks.

    Args:
        file_path: The file path to validate
        upload_dir: The allowed upload directory

    Returns:
        Canonicalized absolute path

    Raises:
        ValueError: If path is invalid or outside allowed directory
    """
    if not file_path:
        raise ValueError("File path cannot be empty")

    # Get the allowed upload directory
    resolved_upload_dir = upload_dir.resolve()

    # Canonicalize the path (resolves symlinks and ..)
    try:
        canonical_path = Path(file_path).resolve()
    except (OSError, ValueError) as e:
        raise ValueError(f"Invalid file path: {e}")

    # Ensure path is within upload directory
    try:
        canonical_path.relative_to(resolved_upload_dir)
    except ValueError:
        raise ValueError(f"File path must be within upload directory: {resolved_upload_dir}")

    # Check file exists
    if not canonical_path.exists():
        raise ValueError(f"File does not exist: {canonical_path}")

    return str(canonical_path)


def sanitize_sheet_name(sheet_name: Optional[str]) -> str:
    """
    Sanitize Excel sheet name to prevent SQL injection.

    Args:
        sheet_name: The sheet name to sanitize

    Returns:
        Sanitized sheet name safe for SQL queries
    """
    if not sheet_name:
        return 'Sheet1'

    # Remove any characters that could be used for SQL injection
    # Allow only alphanumeric, spaces, underscores, hyphens
    sanitized = re.sub(r"[^a-zA-Z0-9 _\-]", '', sheet_name)

    # Remove SQL comment sequences (double hyphens)
    sanitized = sanitized.replace('--', '')

    # Limit length
    sanitized = sanitized[:100]

    # Ensure not empty after sanitization
    if not sanitized.strip():
        return 'Sheet1'

    return sanitized
