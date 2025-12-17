"""Input validation utilities for PM MCP server."""

import re
from typing import Any

# Jira issue key format: PROJECT-123 (supports single-letter projects like A-1)
JIRA_ISSUE_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")

# User input constraints
MAX_MESSAGE_LENGTH = 10 * 1024  # 10KB
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

# Allowed calendar metadata keys (whitelist)
ALLOWED_METADATA_KEYS = {"jira_project_key", "confluence_space_key", "version"}


class ValidationError(ValueError):
    """Raised when validation fails."""

    pass


def validate_issue_keys(keys: list[str]) -> list[str]:
    """Validate Jira issue keys format.

    Args:
        keys: List of issue key strings to validate

    Returns:
        List of valid issue keys

    Raises:
        ValidationError: If no valid keys found in non-empty input
    """
    if not keys:
        return []

    valid_keys = []
    for key in keys:
        if not isinstance(key, str):
            continue
        if len(key) > 50:  # Reasonable max length
            continue
        if JIRA_ISSUE_KEY_PATTERN.match(key):
            valid_keys.append(key)

    if not valid_keys and keys:
        raise ValidationError(
            f"No valid issue keys found. Expected format: PROJECT-123. "
            f"Got: {', '.join(str(k) for k in keys[:3])}"
        )

    return valid_keys


def sanitize_user_input(text: str) -> str:
    """Sanitize user input for A2A messages.

    Args:
        text: Raw user input

    Returns:
        Sanitized text

    Raises:
        ValidationError: If input exceeds limits or is empty
    """
    if not text:
        raise ValidationError("Message content cannot be empty")

    # Length check
    if len(text) > MAX_MESSAGE_LENGTH:
        raise ValidationError(
            f"Message too long: {len(text)} bytes > {MAX_MESSAGE_LENGTH} bytes"
        )

    # Remove control characters (except newline \n and tab \t)
    sanitized = CONTROL_CHARS.sub("", text)

    # Strip excessive whitespace
    sanitized = sanitized.strip()

    if not sanitized:
        raise ValidationError("Message contains only whitespace or control characters")

    return sanitized


def validate_metadata_dict(data: dict[str, Any]) -> dict[str, str]:
    """Validate and filter calendar metadata.

    Only allows whitelisted keys to prevent metadata pollution.

    Args:
        data: Raw metadata dictionary

    Returns:
        Filtered dict with only allowed keys
    """
    return {
        k: str(v) for k, v in data.items() if k in ALLOWED_METADATA_KEYS and v is not None
    }
