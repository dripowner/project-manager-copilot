"""Message conversion utilities for A2A protocol integration."""

import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from agent.core.config import AgentSettings
from agent.core.state import ProjectContext

logger = logging.getLogger(__name__)


def a2a_to_langchain_message(msg: Any) -> HumanMessage:
    """Convert A2A message to LangChain message.

    Args:
        msg: A2A Message object with 'content' or 'parts' attribute

    Returns:
        LangChain HumanMessage

    Raises:
        ValueError: If message format is invalid (no content or parts)
    """
    if hasattr(msg, "content"):
        content = msg.content
    elif hasattr(msg, "parts") and msg.parts:
        # Try to extract from parts (A2A message structure)
        if msg.parts[0].root and hasattr(msg.parts[0].root, "text"):
            content = msg.parts[0].root.text
        else:
            content = ""
    else:
        # Don't use str(msg) - it might expose internal state
        raise ValueError(
            f"Invalid A2A message format: missing 'content' or 'parts' "
            f"(type: {type(msg).__name__})"
        )

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

    WARNING: Do not log raw metadata - it may contain sensitive data.

    Args:
        msg: A2A Message object with optional metadata
        settings: Agent settings for defaults

    Returns:
        ProjectContext with validated project metadata
    """
    metadata = {}
    if hasattr(msg, "metadata") and msg.metadata:
        metadata = msg.metadata

    # Extract with validation
    project_key = metadata.get("project_key", settings.default_project_key)
    sprint_name = metadata.get("sprint_name", settings.default_sprint_name)
    team_members = metadata.get("team_members", [])

    # Validate types to prevent injection attacks
    if project_key and not isinstance(project_key, str):
        logger.warning(
            f"Invalid project_key type: {type(project_key).__name__}, using default"
        )
        project_key = settings.default_project_key

    if sprint_name and not isinstance(sprint_name, str):
        logger.warning(
            f"Invalid sprint_name type: {type(sprint_name).__name__}, using default"
        )
        sprint_name = settings.default_sprint_name

    if not isinstance(team_members, list):
        logger.warning(
            f"Invalid team_members type: {type(team_members).__name__}, using empty list"
        )
        team_members = []

    return ProjectContext(
        project_key=project_key or "UNKNOWN",
        sprint_name=sprint_name,
        team_members=team_members,
    )
