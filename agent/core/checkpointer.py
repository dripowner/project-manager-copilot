"""Checkpointer management for PM Copilot Agent."""

import logging

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

logger = logging.getLogger(__name__)


async def close_checkpointer(checkpointer: AsyncPostgresSaver) -> None:
    """Close checkpointer and cleanup resources.

    Args:
        checkpointer: AsyncPostgresSaver instance to close
    """
    logger.info("Closing AsyncPostgresSaver...")
    # AsyncPostgresSaver uses context manager internally, but we need explicit cleanup
    # when used in long-running server (not as async context manager)
    if hasattr(checkpointer, 'aclose'):
        await checkpointer.aclose()
    elif hasattr(checkpointer, 'close'):
        checkpointer.close()
    logger.info("AsyncPostgresSaver closed")
