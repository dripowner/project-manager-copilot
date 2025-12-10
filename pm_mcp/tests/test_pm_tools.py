"""Tests for PM layer tools."""

import pytest
from fastmcp import Client

from pm_mcp.tests.mocks.mock_services import (
    MockCalendarService,
    MockJiraService,
)


@pytest.mark.asyncio
async def test_pm_link_meeting_issues(
    mcp_client: Client,
    mock_calendar_service: MockCalendarService,
) -> None:
    """Test linking meeting to issues."""
    # Setup: create mock event
    mock_calendar_service.set_event(
        event_id="event123",
        summary="Sprint Planning",
        start_datetime="2024-01-15T10:00:00Z",
    )

    result = await mcp_client.call_tool(
        "pm_link_meeting_issues",
        {
            "calendar_event_id": "event123",
            "jira_issue_keys": ["PROJ-1", "PROJ-2"],
            "confluence_page_id": "page456",
            "meeting_title": "Sprint Planning",
        },
    )

    assert result is not None

    # Verify metadata was stored
    metadata = await mock_calendar_service.get_event_metadata("event123")
    assert metadata["issue_keys"] == ["PROJ-1", "PROJ-2"]
    assert metadata["confluence_page_id"] == "page456"


@pytest.mark.asyncio
async def test_pm_link_meeting_issues_minimal(
    mcp_client: Client,
    mock_calendar_service: MockCalendarService,
) -> None:
    """Test linking meeting with minimal data."""
    # Setup: create mock event
    mock_calendar_service.set_event(
        event_id="event789",
        summary="Team Sync",
        start_datetime="2024-01-16T14:00:00Z",
    )

    result = await mcp_client.call_tool(
        "pm_link_meeting_issues",
        {
            "calendar_event_id": "event789",
            "jira_issue_keys": ["PROJ-3"],
        },
    )

    assert result is not None

    # Verify metadata was stored
    metadata = await mock_calendar_service.get_event_metadata("event789")
    assert metadata["issue_keys"] == ["PROJ-3"]


@pytest.mark.asyncio
async def test_pm_get_meeting_issues(
    mcp_client: Client,
    mock_calendar_service: MockCalendarService,
    mock_jira_service: MockJiraService,
) -> None:
    """Test getting issues for a meeting."""
    # Setup: create event with metadata
    mock_calendar_service.set_event(
        event_id="event123",
        summary="Sprint Planning",
        start_datetime="2024-01-15T10:00:00Z",
    )
    await mock_calendar_service.update_event_metadata(
        event_id="event123",
        jira_issues=["PROJ-1", "PROJ-2"],
        confluence_page_id="page456",
        project_key="PROJ",
    )

    result = await mcp_client.call_tool(
        "pm_get_meeting_issues",
        {"calendar_event_id": "event123"},
    )

    assert result is not None


@pytest.mark.asyncio
async def test_pm_get_meeting_issues_not_found(
    mcp_client: Client,
) -> None:
    """Test getting issues for non-existent meeting."""
    result = await mcp_client.call_tool(
        "pm_get_meeting_issues",
        {"calendar_event_id": "nonexistent"},
    )

    assert result is not None


@pytest.mark.asyncio
async def test_pm_get_project_snapshot(
    mcp_client: Client,
    mock_jira_service: MockJiraService,
) -> None:
    """Test getting project snapshot."""
    # Setup mock issues with different statuses
    mock_jira_service.list_issues.return_value = [
        {
            "key": "PROJ-1",
            "id": "10001",
            "url": "https://jira.example.com/browse/PROJ-1",
            "summary": "Task 1",
            "status": "To Do",
            "status_category": "To Do",
            "assignee": "Alice",
            "labels": [],
            "due_date": "2024-01-10",  # Overdue
            "updated": "2024-01-15T10:00:00Z",
        },
        {
            "key": "PROJ-2",
            "id": "10002",
            "url": "https://jira.example.com/browse/PROJ-2",
            "summary": "Task 2",
            "status": "In Progress",
            "status_category": "In Progress",
            "assignee": "Bob",
            "labels": [],
            "due_date": None,
            "updated": "2024-01-15T10:00:00Z",
        },
        {
            "key": "PROJ-3",
            "id": "10003",
            "url": "https://jira.example.com/browse/PROJ-3",
            "summary": "Task 3",
            "status": "Done",
            "status_category": "Done",
            "assignee": "Alice",
            "labels": [],
            "due_date": None,
            "updated": "2024-01-15T10:00:00Z",
        },
    ]

    result = await mcp_client.call_tool(
        "pm_get_project_snapshot",
        {"project_key": "PROJ"},
    )

    assert result is not None
