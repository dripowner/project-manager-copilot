"""Tests for calendar tools."""

import pytest
from fastmcp import Client

from pm_mcp.tests.mocks.mock_services import MockCalendarService


@pytest.mark.asyncio
async def test_calendar_list_events(
    mcp_client: Client,
    mock_calendar_service: MockCalendarService,
) -> None:
    """Test listing calendar events."""
    result = await mcp_client.call_tool(
        "calendar_list_events", {"project_key": "ALPHA"}
    )

    assert result is not None
    # Check that service was called
    mock_calendar_service.list_events.assert_called_once()
    mock_calendar_service.find_or_create_project_calendar.assert_called_once_with(
        project_key="ALPHA"
    )


@pytest.mark.asyncio
async def test_calendar_list_events_with_params(
    mcp_client: Client,
    mock_calendar_service: MockCalendarService,
) -> None:
    """Test listing calendar events with parameters."""
    result = await mcp_client.call_tool(
        "calendar_list_events",
        {
            "project_key": "ALPHA",
            "time_min": "2024-01-01T00:00:00Z",
            "time_max": "2024-01-31T23:59:59Z",
            "text_query": "sprint",
            "max_results": 10,
        },
    )

    assert result is not None
    mock_calendar_service.list_events.assert_called_once()


@pytest.mark.asyncio
async def test_calendar_list_events_returns_events(
    mcp_client: Client,
    mock_calendar_service: MockCalendarService,
) -> None:
    """Test that calendar events are returned correctly."""
    mock_calendar_service.list_events.return_value = [
        {
            "id": "test-event-1",
            "summary": "Test Meeting",
            "description": "A test meeting",
            "start": "2024-01-15T10:00:00Z",
            "end": "2024-01-15T11:00:00Z",
            "location": "Room A",
            "attendees": ["user@example.com"],
        }
    ]

    result = await mcp_client.call_tool(
        "calendar_list_events", {"project_key": "ALPHA"}
    )

    assert result is not None


@pytest.mark.asyncio
async def test_calendar_list_calendars(
    mcp_client: Client,
    mock_calendar_service: MockCalendarService,
) -> None:
    """Test listing all calendars."""
    result = await mcp_client.call_tool("calendar_list_calendars", {})

    assert result is not None
    mock_calendar_service.list_calendars.assert_called_once()


@pytest.mark.asyncio
async def test_calendar_find_project_calendar_existing(
    mcp_client: Client,
    mock_calendar_service: MockCalendarService,
) -> None:
    """Test finding existing calendar for project."""
    result = await mcp_client.call_tool(
        "calendar_find_project_calendar", {"project_key": "ALPHA"}
    )

    assert result is not None
    mock_calendar_service.find_or_create_project_calendar.assert_called_once_with(
        project_key="ALPHA", confluence_space_key=None
    )


@pytest.mark.asyncio
async def test_calendar_find_project_calendar_with_confluence(
    mcp_client: Client,
    mock_calendar_service: MockCalendarService,
) -> None:
    """Test finding/creating calendar with Confluence space."""
    result = await mcp_client.call_tool(
        "calendar_find_project_calendar",
        {"project_key": "GAMMA", "confluence_space_key": "GAMMA"},
    )

    assert result is not None
    mock_calendar_service.find_or_create_project_calendar.assert_called_once_with(
        project_key="GAMMA", confluence_space_key="GAMMA"
    )
