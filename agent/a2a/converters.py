"""Message conversion utilities for A2A protocol integration."""

import logging
from typing import Any

from a2a.utils.message import get_message_text
from langchain_core.messages import AIMessage, HumanMessage

from agent.core.config import AgentSettings
from agent.core.state import ProjectContext

logger = logging.getLogger(__name__)


def extract_message_content(msg: Any) -> str:
    """Extract text content from A2A message.

    Uses official a2a-sdk utility function for proper message parsing.

    Args:
        msg: A2A Message object

    Returns:
        Message text content

    Raises:
        ValueError: If message format is invalid
    """
    try:
        # Official way to extract text from A2A Message
        return get_message_text(msg)
    except Exception as e:
        # Fallback for backwards compatibility or edge cases
        if hasattr(msg, "content"):
            logger.warning(f"Falling back to .content attribute: {e}")
            return msg.content
        raise ValueError(
            f"Failed to extract content from message (type: {type(msg).__name__}): {e}"
        ) from e


def a2a_to_langchain_message(msg: Any) -> HumanMessage:
    """Convert A2A message to LangChain message.

    Args:
        msg: A2A Message object with 'content' or 'parts' attribute

    Returns:
        LangChain HumanMessage

    Raises:
        ValueError: If message format is invalid (no content or parts)
    """
    content = extract_message_content(msg)
    return HumanMessage(content=content)


def langchain_to_a2a_message(msg: AIMessage) -> dict[str, Any]:
    """Convert LangChain message to A2A message format.

    Args:
        msg: LangChain AIMessage

    Returns:
        A2A message dictionary
    """
    return {
        "role": "assistant",
        "content": msg.content,
    }


def extract_project_context(
    msg: Any,
    settings: AgentSettings,
) -> ProjectContext:
    """Extract ProjectContext from A2A message metadata.

    Agent will determine project_key from conversation context if not provided.

    WARNING: Do not log raw metadata - it may contain sensitive data.

    Args:
        msg: A2A Message object with optional metadata
        settings: Agent settings

    Returns:
        ProjectContext with validated project metadata (project_key may be None)
    """
    metadata = {}
    if hasattr(msg, "metadata") and msg.metadata:
        metadata = msg.metadata

    # Extract with validation (no defaults)
    project_key = metadata.get("project_key")
    sprint_name = metadata.get("sprint_name")
    team_members = metadata.get("team_members", [])

    # Validate types to prevent injection attacks
    if project_key and not isinstance(project_key, str):
        logger.warning(
            f"Invalid project_key type: {type(project_key).__name__}, ignoring"
        )
        project_key = None

    if sprint_name and not isinstance(sprint_name, str):
        logger.warning(
            f"Invalid sprint_name type: {type(sprint_name).__name__}, ignoring"
        )
        sprint_name = None

    if not isinstance(team_members, list):
        logger.warning(
            f"Invalid team_members type: {type(team_members).__name__}, using empty list"
        )
        team_members = []

    return ProjectContext(
        project_key=project_key,
        sprint_name=sprint_name,
        team_members=team_members,
    )


def extract_user_context(msg: Any) -> dict[str, Any] | None:
    """Extract user context from A2A message metadata for audit logging.

    IMPORTANT: Agent does NOT enforce authorization based on this data.
    User context is for audit/logging only.

    Args:
        msg: A2A Message object with optional metadata

    Returns:
        Dictionary with user context if available, None otherwise.
        Keys: user_id, user_email, user_full_name, default_project_key
    """
    if not hasattr(msg, "metadata") or not msg.metadata:
        return None

    metadata = msg.metadata

    # Extract user fields
    user_id = metadata.get("user_id")
    user_email = metadata.get("user_email")
    user_full_name = metadata.get("user_full_name")
    default_project_key = metadata.get("default_project_key")

    # Return None if no user context present
    if not user_id and not user_email:
        return None

    # Validate types to prevent injection attacks
    if user_id and not isinstance(user_id, str):
        logger.warning("Invalid user_id type in metadata, ignoring")
        user_id = None

    if user_email and not isinstance(user_email, str):
        logger.warning("Invalid user_email type in metadata, ignoring")
        user_email = None

    if user_full_name and not isinstance(user_full_name, str):
        logger.warning("Invalid user_full_name type in metadata, ignoring")
        user_full_name = None

    if default_project_key and not isinstance(default_project_key, str):
        logger.warning("Invalid default_project_key type in metadata, ignoring")
        default_project_key = None

    return {
        "user_id": user_id,
        "user_email": user_email,
        "user_full_name": user_full_name,
        "default_project_key": default_project_key,
    }
