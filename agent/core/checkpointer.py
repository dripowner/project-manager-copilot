"""Checkpointer management for PM Copilot Agent."""

import logging

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from agent.core.config import AgentSettings

logger = logging.getLogger(__name__)


async def create_checkpointer(settings: AgentSettings) -> BaseCheckpointSaver | None:
    """Create and initialize checkpointer based on configuration.

    This function creates either an in-memory or PostgreSQL checkpointer
    based on the settings. For PostgreSQL, it automatically calls asetup()
    to create necessary tables on first use.

    Args:
        settings: Agent configuration with postgres credentials

    Returns:
        Configured checkpointer or None if disabled
    """
    # Check if PostgreSQL credentials are available
    if not settings.postgres_url or not settings.postgres_password:
        logger.info("Checkpointing disabled (no PostgreSQL credentials)")
        return None

    try:
        logger.info("Initializing PostgreSQL checkpointer")

        # Create AsyncPostgresSaver with connection string
        checkpointer = AsyncPostgresSaver.from_conn_string(settings.postgres_url)

        # Enter async context and setup tables safely
        try:
            await checkpointer.__aenter__()

            # Setup database tables (creates tables if they don't exist)
            logger.info("Setting up checkpoint tables...")
            await checkpointer.asetup()
            logger.info("PostgreSQL checkpointer initialized successfully")

            return checkpointer

        except Exception as setup_error:
            # If setup fails after entering context, ensure proper cleanup
            logger.warning(f"Setup failed, cleaning up connection: {setup_error}")
            await checkpointer.__aexit__(None, None, None)
            raise  # Re-raise to trigger outer exception handler

    except Exception as e:
        logger.error(f"Failed to initialize PostgreSQL checkpointer: {e}")
        logger.warning("Falling back to in-memory checkpointer")
        return MemorySaver()


def create_memory_checkpointer() -> MemorySaver:
    """Create in-memory checkpointer for development/testing.

    Returns:
        In-memory checkpointer (no persistence)
    """
    logger.info("Using in-memory checkpointer (no persistence)")
    return MemorySaver()


async def close_checkpointer(checkpointer: BaseCheckpointSaver | None) -> None:
    """Properly close checkpointer and cleanup resources.

    Args:
        checkpointer: Checkpointer instance to close
    """
    if checkpointer is None:
        return

    try:
        # AsyncPostgresSaver supports async context manager
        if isinstance(checkpointer, AsyncPostgresSaver):
            await checkpointer.__aexit__(None, None, None)
            logger.info("PostgreSQL checkpointer closed")
        else:
            logger.info("Checkpointer closed")
    except Exception as e:
        logger.error(f"Error closing checkpointer: {e}")
