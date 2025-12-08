"""Tests for Confluence tools."""

import pytest
from fastmcp import Client

from pm_mcp.tests.mocks.mock_services import MockConfluenceService


@pytest.mark.asyncio
async def test_confluence_search_pages(
    mcp_client: Client,
    mock_confluence_service: MockConfluenceService,
) -> None:
    """Test searching Confluence pages."""
    result = await mcp_client.call_tool(
        "confluence_search_pages",
        {"query": "sprint planning"},
    )

    assert result is not None
    mock_confluence_service.search_pages.assert_called_once()


@pytest.mark.asyncio
async def test_confluence_search_pages_with_space(
    mcp_client: Client,
    mock_confluence_service: MockConfluenceService,
) -> None:
    """Test searching Confluence pages in specific space."""
    result = await mcp_client.call_tool(
        "confluence_search_pages",
        {
            "query": "meeting notes",
            "space_key": "TEAM",
            "limit": 5,
        },
    )

    assert result is not None
    mock_confluence_service.search_pages.assert_called_once()


@pytest.mark.asyncio
async def test_confluence_get_page_content(
    mcp_client: Client,
    mock_confluence_service: MockConfluenceService,
) -> None:
    """Test getting Confluence page content."""
    result = await mcp_client.call_tool(
        "confluence_get_page_content",
        {"page_id": "123456"},
    )

    assert result is not None
    mock_confluence_service.get_page_content.assert_called_once_with(page_id="123456")


@pytest.mark.asyncio
async def test_confluence_create_meeting_page(
    mcp_client: Client,
    mock_confluence_service: MockConfluenceService,
) -> None:
    """Test creating a Confluence meeting page."""
    result = await mcp_client.call_tool(
        "confluence_create_meeting_page",
        {
            "space_key": "TEAM",
            "title": "Sprint 11 Planning",
            "body_markdown": "# Sprint 11 Planning\n\n## Attendees\n- Alice\n- Bob",
        },
    )

    assert result is not None
    mock_confluence_service.create_page.assert_called_once()


@pytest.mark.asyncio
async def test_confluence_create_meeting_page_with_parent(
    mcp_client: Client,
    mock_confluence_service: MockConfluenceService,
) -> None:
    """Test creating a Confluence page with parent."""
    result = await mcp_client.call_tool(
        "confluence_create_meeting_page",
        {
            "space_key": "TEAM",
            "title": "Sprint 11 Planning",
            "body_markdown": "Content here",
            "parent_page_id": "111111",
        },
    )

    assert result is not None
    mock_confluence_service.create_page.assert_called_once()
