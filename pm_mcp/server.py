"""FastMCP server initialization and configuration."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Mount

from pm_mcp.config import get_settings
from pm_mcp.constants import SERVER_INSTRUCTIONS
from pm_mcp.core.database import close_db_pool, get_db_pool
from pm_mcp.services.calendar_service import CalendarService
from pm_mcp.services.confluence_service import ConfluenceService
from pm_mcp.services.jira_service import JiraService
from pm_mcp.services.pm_service import PmService
from pm_mcp.tools.calendar import register_calendar_tools
from pm_mcp.tools.confluence import register_confluence_tools
from pm_mcp.tools.jira import register_jira_tools
from pm_mcp.tools.pm import register_pm_tools

logger = logging.getLogger(__name__)


def create_mcp_server() -> FastMCP:
    """Create and configure MCP server with all tools registered.

    Returns:
        FastMCP: Server instance ready for HTTP or STDIO transport.
    """
    mcp = FastMCP(name="pm-mcp", instructions=SERVER_INSTRUCTIONS)

    # Register all tools (they access services via ctx.fastmcp)
    register_calendar_tools(mcp)
    register_confluence_tools(mcp)
    register_jira_tools(mcp)
    register_pm_tools(mcp)

    logger.info("MCP server created, tools registered")
    return mcp


def create_http_app():
    """Create ASGI application with MCP server for HTTP deployment.

    Initializes all services (Jira, Confluence, Calendar, PM/DB) during startup
    and handles proper cleanup on shutdown.

    Returns:
        Starlette: ASGI application ready for uvicorn/gunicorn.
    """

    # Create reusable MCP server
    mcp = create_mcp_server()
    mcp_app = mcp.http_app(path="/mcp")

    @asynccontextmanager
    async def app_lifespan(app: Any) -> AsyncGenerator[None, None]:
        """Initialize services on startup, cleanup on shutdown."""
        logger.info("Starting PM MCP Server (HTTP transport)...")

        # Initialize all services (sync ones first)
        settings = get_settings()
        mcp.jira_service = JiraService(settings)
        mcp.confluence_service = ConfluenceService(settings)
        mcp.calendar_service = CalendarService(settings)
        logger.info("External services initialized (Jira, Confluence, Calendar)")

        # Initialize async resources (database pool and PM service)
        db_pool = None
        try:
            db_pool = await get_db_pool()
            mcp.pm_service = PmService(db_pool, settings)
            logger.info("Database pool and PM service initialized")
        except Exception as e:
            logger.warning(f"Database pool initialization failed: {e}")
            logger.warning("PM tools requiring database will not work")
            mcp.pm_service = None

        yield

        # Cleanup
        logger.info("Shutting down PM MCP Server...")
        if db_pool:
            await close_db_pool()
        logger.info("Cleanup completed")

    @asynccontextmanager
    async def combined_lifespan(app: Any) -> AsyncGenerator[None, None]:
        """Combine app and MCP session lifespans."""
        async with app_lifespan(app):
            async with mcp_app.lifespan(app):
                yield

    return Starlette(
        lifespan=combined_lifespan,
        routes=[Mount("/", app=mcp_app)],
    )


def run_stdio_server() -> None:
    """Run MCP server in STDIO mode for local/desktop use.

    Initializes all services and blocks until stdin closes.
    Database connections are properly cleaned up on shutdown.
    """
    logger.info("Starting PM MCP Server (STDIO transport)...")

    # Create reusable MCP server
    mcp = create_mcp_server()

    # Initialize services synchronously
    settings = get_settings()
    mcp.jira_service = JiraService(settings)
    mcp.confluence_service = ConfluenceService(settings)
    mcp.calendar_service = CalendarService(settings)
    logger.info("External services initialized (Jira, Confluence, Calendar)")

    # Initialize async resources (database pool and PM service)
    async def init_async_services():
        """Initialize database and PM service."""
        try:
            db_pool = await get_db_pool()
            mcp.pm_service = PmService(db_pool, settings)
            logger.info("Database pool and PM service initialized")
            return db_pool
        except Exception as e:
            logger.warning(f"Database pool initialization failed: {e}")
            logger.warning("PM tools requiring database will not work")
            mcp.pm_service = None
            return None

    # Run async initialization before starting server
    db_pool = asyncio.run(init_async_services())

    logger.info("MCP server ready, waiting for requests...")

    try:
        # Run in STDIO mode (blocks until stdin closes)
        mcp.run()
    finally:
        # Cleanup on shutdown
        if db_pool:
            logger.info("Cleaning up database connection...")
            asyncio.run(close_db_pool())
