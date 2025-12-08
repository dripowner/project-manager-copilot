"""Database connection pool management using asyncpg."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg
from asyncpg import Pool

from pm_mcp.config import Settings, get_settings
from pm_mcp.core.errors import PmError

logger = logging.getLogger(__name__)

_pool: Pool | None = None
_lock = asyncio.Lock()


class DatabasePool:
    """Async database pool manager."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._pool: Pool | None = None

    async def init(self) -> None:
        """Initialize the connection pool."""
        if self._pool is not None:
            return

        try:
            self._pool = await asyncpg.create_pool(
                host=self.settings.postgres_host,
                port=self.settings.postgres_port,
                database=self.settings.postgres_db,
                user=self.settings.postgres_user,
                password=self.settings.postgres_password,
                min_size=2,
                max_size=10,
            )
            logger.info("Database pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise PmError(
                message=f"Database connection failed: {e}",
                details={"host": self.settings.postgres_host},
            ) from e

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            logger.info("Database pool closed")

    @property
    def pool(self) -> Pool:
        """Get the connection pool."""
        if self._pool is None:
            raise PmError(
                message="Database pool not initialized",
                details={"hint": "Call init() first"},
            )
        return self._pool

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get a connection from the pool."""
        async with self.pool.acquire() as conn:
            yield conn

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get a connection with transaction."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                yield conn


# Global pool instance
_db_pool: DatabasePool | None = None


async def get_db_pool() -> DatabasePool:
    """Get or create the global database pool."""
    global _db_pool
    async with _lock:
        if _db_pool is None:
            _db_pool = DatabasePool()
            await _db_pool.init()
        return _db_pool


async def close_db_pool() -> None:
    """Close the global database pool."""
    global _db_pool
    async with _lock:
        if _db_pool is not None:
            await _db_pool.close()
            _db_pool = None


@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Dependency for obtaining a database connection.

    This async context manager can be used with FastMCP Depends to inject
    a database connection into tool handlers.

    Usage:
        from fastmcp import Depends
        from pm_mcp.core.database import get_db_connection

        @mcp.tool()
        async def my_tool(db = Depends(get_db_connection)):
            result = await db.fetch("SELECT * FROM table")

    Yields:
        asyncpg.Connection: A connection from the pool.
    """
    pool = await get_db_pool()
    async with pool.connection() as conn:
        yield conn
