"""Ask project key node for requesting project from user."""

import logging

from langchain_core.messages import AIMessage
from langgraph.types import Command

from agent.core.state import AgentState

logger = logging.getLogger(__name__)


async def ask_project_key(state: AgentState) -> Command:
    """Ask user for project_key when required but missing.

    This node generates a message asking the user to specify which Jira project
    to work with. The conversation ends here, waiting for the user's response.
    On the next message, project_detector will try to extract the project_key.

    Args:
        state: Current agent state

    Returns:
        Command with updated messages, routing to end (wait for user)
    """
    logger.info("Asking user for project_key")

    question = AIMessage(content="""Для выполнения этого запроса мне нужно знать, с каким Jira проектом работать.

Пожалуйста, укажите ключ проекта (например: ALPHA, BETA, GAMMA).""")

    return Command(
        update={"messages": [question]},
        goto="__end__"  # Wait for user response
    )
