"""FastMCP server initialization and configuration."""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastmcp import FastMCP

from pm_mcp.config import get_settings
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


@asynccontextmanager
async def app_lifespan(app: Any) -> AsyncGenerator[None, None]:
    """Manage application lifecycle - startup and shutdown.

    This lifespan handler initializes the database pool and PM service
    on startup, and cleans up resources on shutdown.
    """
    logger.info("Starting PM MCP Server...")

    # Initialize database pool and PM service
    try:
        db_pool = await get_db_pool()
        # Initialize pm_service on the global mcp instance
        mcp.pm_service = PmService(db_pool, mcp._app_settings)  # type: ignore[attr-defined]
        logger.info("Database pool and PM service initialized")
    except Exception as e:
        logger.warning(f"Database pool initialization failed: {e}")
        logger.warning("PM tools requiring database will not work")

    yield

    # Cleanup
    logger.info("Shutting down PM MCP Server...")
    await close_db_pool()
    logger.info("Cleanup completed")


def create_server() -> FastMCP:
    """Create and configure the FastMCP server.

    Services are attached to the mcp instance and accessed via
    ctx.fastmcp in tools (FastMCP's recommended DI pattern for v2.13).
    """
    settings = get_settings()

    # Create MCP server
    mcp = FastMCP(
        name="pm-mcp",
        instructions="""
PM MCP Server - Project Management integration server.

This server provides tools for:
- Google Calendar: List meetings and events
- Confluence: Search pages, read content, create meeting notes
- Jira: Create/list/update issues, add comments
- PM Layer: Link meetings to issues, track action items, get project snapshots

Use these tools to:
1. Find meetings in calendar (calendar_list_events)
2. Search and read meeting protocols in Confluence (confluence_search_pages, confluence_get_page_content)
3. Extract action items and create Jira issues (jira_create_issues_batch)
4. Link issues to meetings for traceability (pm_link_meeting_issues)
5. Check status of action items (pm_get_meeting_issues)
6. Get project health overview (pm_get_project_snapshot)
""",
    )

    # Attach services to mcp instance (accessed via ctx.fastmcp in tools)
    mcp.jira_service = JiraService(settings)  # type: ignore[attr-defined]
    mcp.confluence_service = ConfluenceService(settings)  # type: ignore[attr-defined]
    mcp.calendar_service = CalendarService(settings)  # type: ignore[attr-defined]
    # Note: pm_service requires db_pool, initialized lazily in lifespan
    mcp.pm_service = None  # type: ignore[attr-defined]
    mcp._app_settings = settings  # type: ignore[attr-defined]

    # Register all tools (they access services via ctx.fastmcp)
    register_calendar_tools(mcp)
    register_confluence_tools(mcp)
    register_jira_tools(mcp)
    register_pm_tools(mcp)

    logger.info("All tools registered")

    return mcp


# Create server instance
mcp = create_server()


def get_http_app():
    """Get HTTP/ASGI application for production deployment.

    This creates an ASGI application with proper lifespan management
    for database pool initialization and MCP session management.

    The combined lifespan ensures:
    1. Database pool is initialized before MCP starts accepting requests
    2. MCP session manager is properly initialized (via mcp_app.lifespan)
    3. Resources are cleaned up in reverse order on shutdown
    """
    from starlette.applications import Starlette
    from starlette.routing import Mount

    mcp_app = mcp.http_app(path="/mcp")

    @asynccontextmanager
    async def combined_lifespan(app: Any) -> AsyncGenerator[None, None]:
        """Combine app lifespan with MCP lifespan."""
        async with app_lifespan(app):
            async with mcp_app.lifespan(app):
                yield

    return Starlette(
        lifespan=combined_lifespan,
        routes=[Mount("/", app=mcp_app)],
    )
