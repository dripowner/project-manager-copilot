"""Service factory functions for testing.

In production, services are attached directly to the FastMCP instance
and accessed via ctx.fastmcp in tools. These factories are kept for:
1. Testing - to create service instances with custom settings
2. Potential future use if FastMCP adds proper Depends() support

Note: FastMCP 2.13.3 doesn't have fastmcp.dependencies.Depends.
The recommended DI pattern for 2.13.x is attaching services to
the mcp instance and accessing via ctx.fastmcp.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from pm_mcp.config import Settings, get_settings
from pm_mcp.services.calendar_service import CalendarService
from pm_mcp.services.confluence_service import ConfluenceService
from pm_mcp.services.jira_service import JiraService
from pm_mcp.services.pm_service import PmService


def get_jira_service(settings: Settings | None = None) -> JiraService:
    """Create JiraService instance.

    Args:
        settings: Optional settings override. If None, uses default settings.

    Returns:
        JiraService instance.
    """
    return JiraService(settings or get_settings())


def get_confluence_service(settings: Settings | None = None) -> ConfluenceService:
    """Create ConfluenceService instance.

    Args:
        settings: Optional settings override. If None, uses default settings.

    Returns:
        ConfluenceService instance.
    """
    return ConfluenceService(settings or get_settings())


def get_calendar_service(settings: Settings | None = None) -> CalendarService:
    """Create CalendarService instance.

    Args:
        settings: Optional settings override. If None, uses default settings.

    Returns:
        CalendarService instance.
    """
    return CalendarService(settings or get_settings())


@asynccontextmanager
async def get_pm_service(
    settings: Settings | None = None,
) -> AsyncGenerator[PmService, None]:
    """Async context manager for PmService with database connection.

    PmService requires database pool initialization, so we use
    asynccontextmanager pattern for proper resource management.

    Args:
        settings: Optional settings override. If None, uses default settings.

    Yields:
        PmService instance with initialized database connection.
    """
    from pm_mcp.core.database import get_db_pool

    db_pool = await get_db_pool()
    pm_service = PmService(db_pool, settings or get_settings())
    yield pm_service
