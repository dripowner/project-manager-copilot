"""FastMCP server initialization and configuration."""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Mount

from pm_mcp.config import get_settings
from pm_mcp.constants import SERVER_INSTRUCTIONS
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

    Initializes all services (Jira, Confluence, Calendar, PM) during startup
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

        # Initialize all services
        settings = get_settings()
        mcp.jira_service = JiraService(settings)
        mcp.confluence_service = ConfluenceService(settings)
        mcp.calendar_service = CalendarService(settings)
        mcp.pm_service = PmService(settings)
        logger.info("All services initialized (Jira, Confluence, Calendar, PM)")

        yield

        # Cleanup
        logger.info("Shutting down PM MCP Server...")
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
    """
    logger.info("Starting PM MCP Server (STDIO transport)...")

    # Create reusable MCP server
    mcp = create_mcp_server()

    # Initialize all services
    settings = get_settings()
    mcp.jira_service = JiraService(settings)
    mcp.confluence_service = ConfluenceService(settings)
    mcp.calendar_service = CalendarService(settings)
    mcp.pm_service = PmService(settings)
    logger.info("All services initialized (Jira, Confluence, Calendar, PM)")

    logger.info("MCP server ready, waiting for requests...")

    # Run in STDIO mode (blocks until stdin closes)
    mcp.run()
