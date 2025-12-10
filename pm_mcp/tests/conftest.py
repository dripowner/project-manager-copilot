"""Pytest fixtures for MCP server tests."""

from typing import AsyncGenerator, Generator

import pytest
from fastmcp import Client, FastMCP

from pm_mcp.services.pm_service import PmService
from pm_mcp.tests.mocks.mock_services import (
    MockCalendarService,
    MockConfluenceService,
    MockJiraService,
)
from pm_mcp.tools.calendar import register_calendar_tools
from pm_mcp.tools.confluence import register_confluence_tools
from pm_mcp.tools.jira import register_jira_tools
from pm_mcp.tools.pm import register_pm_tools


@pytest.fixture
def mock_calendar_service() -> MockCalendarService:
    """Create mock calendar service."""
    return MockCalendarService()


@pytest.fixture
def mock_jira_service() -> MockJiraService:
    """Create mock Jira service."""
    return MockJiraService()


@pytest.fixture
def mock_confluence_service() -> MockConfluenceService:
    """Create mock Confluence service."""
    return MockConfluenceService()


@pytest.fixture
def mock_pm_service() -> PmService:
    """Create PM service."""
    return PmService()


@pytest.fixture
def mcp_server(
    mock_calendar_service: MockCalendarService,
    mock_jira_service: MockJiraService,
    mock_confluence_service: MockConfluenceService,
    mock_pm_service: PmService,
) -> Generator[FastMCP, None, None]:
    """Create MCP server with mocked services attached to mcp instance."""
    mcp = FastMCP(name="test-pm-mcp")

    # Attach mock services directly to mcp instance
    # (same pattern as production code in server.py)
    mcp.jira_service = mock_jira_service  # type: ignore[attr-defined]
    mcp.confluence_service = mock_confluence_service  # type: ignore[attr-defined]
    mcp.calendar_service = mock_calendar_service  # type: ignore[attr-defined]
    mcp.pm_service = mock_pm_service  # type: ignore[attr-defined]

    # Register tools (they will access services via ctx.fastmcp)
    register_calendar_tools(mcp)
    register_confluence_tools(mcp)
    register_jira_tools(mcp)
    register_pm_tools(mcp)

    yield mcp


@pytest.fixture
async def mcp_client(mcp_server: FastMCP) -> AsyncGenerator[Client, None]:
    """Create MCP client connected to test server."""
    async with Client(mcp_server) as client:
        yield client
