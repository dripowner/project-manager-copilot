"""Database engine management for A2A task storage."""

import logging

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from agent.core.config import AgentSettings

logger = logging.getLogger(__name__)


async def create_database_engine(settings: AgentSettings) -> AsyncEngine:
    """Create SQLAlchemy AsyncEngine for A2A DatabaseTaskStore.

    Uses postgresql+asyncpg driver with connection pooling optimized for
    A2A task storage workloads.

    Args:
        settings: Agent configuration with PostgreSQL credentials

    Returns:
        Configured AsyncEngine ready for use with DatabaseTaskStore

    Example:
        ```python
        settings = AgentSettings()
        engine = await create_database_engine(settings)
        task_store = DatabaseTaskStore(engine=engine, create_table=True)
        ```
    """
    # Build asyncpg connection string
    conn_str = (
        f"postgresql+asyncpg://{settings.postgres_user}:"
        f"{settings.postgres_password}@{settings.postgres_host}:"
        f"{settings.postgres_port}/{settings.postgres_db}"
    )

    engine = create_async_engine(
        conn_str,
        pool_size=5,  # Connections per worker
        max_overflow=10,  # Additional connections under load
        pool_pre_ping=True,  # Test connections before use
        pool_recycle=3600,  # Recycle connections after 1 hour
        echo=False,  # Set True for SQL debugging
    )

    logger.info(
        f"Database engine created: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )
    return engine


async def close_database_engine(engine: AsyncEngine) -> None:
    """Close database engine and cleanup all connections.

    This should be called during application shutdown to ensure all
    database connections are properly closed.

    Args:
        engine: AsyncEngine to close
    """
    await engine.dispose()
    logger.info("Database engine closed and connections cleaned up")
