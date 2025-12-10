"""Checkpointer management for PM Copilot Agent."""

import logging

from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)


def create_checkpointer() -> MemorySaver:
    """Create in-memory checkpointer for conversation state.

    Uses MemorySaver for lightweight conversation history without persistence.
    Conversation state is lost on agent restart.

    Note: For task persistence, see InMemoryTaskStore (agent.a2a.server).

    Returns:
        In-memory checkpointer (no persistence across restarts)
    """
    logger.info("Using in-memory checkpointer (conversation state not persisted)")
    return MemorySaver()


def close_checkpointer(checkpointer: MemorySaver) -> None:
    """Close checkpointer and cleanup resources.

    No-op for MemorySaver (kept for symmetry with create_checkpointer).

    Args:
        checkpointer: Checkpointer instance to close
    """
    logger.info("Checkpointer cleanup (no-op for MemorySaver)")
