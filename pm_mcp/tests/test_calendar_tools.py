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


@pytest.mark.asyncio
async def test_calendar_verify_project_access_has_access(
    mcp_client: Client,
    mock_calendar_service: MockCalendarService,
) -> None:
    """Test verifying access when user has access."""
    result = await mcp_client.call_tool(
        "calendar_verify_project_access",
        {
            "project_key": "ALPHA",
            "user_email": "owner@example.com",
        },
    )

    assert result is not None
    mock_calendar_service.verify_project_access.assert_called_once_with(
        project_key="ALPHA",
        user_email="owner@example.com",
    )


@pytest.mark.asyncio
async def test_calendar_verify_project_access_no_access(
    mcp_client: Client,
    mock_calendar_service: MockCalendarService,
) -> None:
    """Test verifying access when user has no access."""
    result = await mcp_client.call_tool(
        "calendar_verify_project_access",
        {
            "project_key": "ALPHA",
            "user_email": "unknown@example.com",
        },
    )

    assert result is not None
    mock_calendar_service.verify_project_access.assert_called_once_with(
        project_key="ALPHA",
        user_email="unknown@example.com",
    )


@pytest.mark.asyncio
async def test_calendar_verify_project_access_default_email(
    mcp_client: Client,
    mock_calendar_service: MockCalendarService,
) -> None:
    """Test verifying access without providing user_email (uses default)."""
    result = await mcp_client.call_tool(
        "calendar_verify_project_access",
        {"project_key": "ALPHA"},  # No user_email parameter
    )

    assert result is not None
    mock_calendar_service.verify_project_access.assert_called_once_with(
        project_key="ALPHA",
        user_email=None,
    )


@pytest.mark.asyncio
async def test_calendar_verify_project_access_writer_role(
    mcp_client: Client,
    mock_calendar_service: MockCalendarService,
) -> None:
    """Test verifying access with writer role."""
    result = await mcp_client.call_tool(
        "calendar_verify_project_access",
        {
            "project_key": "ALPHA",
            "user_email": "writer@example.com",
        },
    )

    assert result is not None
    mock_calendar_service.verify_project_access.assert_called_once()


@pytest.mark.asyncio
async def test_calendar_verify_project_access_new_project(
    mcp_client: Client,
    mock_calendar_service: MockCalendarService,
) -> None:
    """Test verifying access creates calendar if project doesn't exist."""
    result = await mcp_client.call_tool(
        "calendar_verify_project_access",
        {
            "project_key": "NEWPROJECT",
            "user_email": "user@example.com",
        },
    )

    assert result is not None
    # Verify that verify_project_access was called
    mock_calendar_service.verify_project_access.assert_called_once_with(
        project_key="NEWPROJECT",
        user_email="user@example.com",
    )


@pytest.mark.asyncio
async def test_calendar_grant_access_new_user(
    mcp_client: Client,
    mock_calendar_service: MockCalendarService,
) -> None:
    """Test granting access to a new user."""
    result = await mcp_client.call_tool(
        "calendar_grant_access",
        {
            "project_key": "GAMMA",
            "user_email": "newuser@example.com",
            "role": "writer",
        },
    )

    assert result is not None
    mock_calendar_service.grant_project_access.assert_called_once_with(
        project_key="GAMMA",
        user_email="newuser@example.com",
        role="writer",
    )


@pytest.mark.asyncio
async def test_calendar_grant_access_already_exists(
    mcp_client: Client,
    mock_calendar_service: MockCalendarService,
) -> None:
    """Test granting access when user already has exact same role."""
    # Pre-configure ACL
    mock_calendar_service.set_calendar_acl(
        "calendar_alpha",
        [
            {
                "role": "writer",
                "scope": {"type": "user", "value": "existing@example.com"},
            }
        ],
    )

    result = await mcp_client.call_tool(
        "calendar_grant_access",
        {
            "project_key": "ALPHA",
            "user_email": "existing@example.com",
            "role": "writer",
        },
    )

    assert result is not None
    mock_calendar_service.grant_project_access.assert_called_once()


@pytest.mark.asyncio
async def test_calendar_grant_access_role_update(
    mcp_client: Client,
    mock_calendar_service: MockCalendarService,
) -> None:
    """Test updating access role for existing user."""
    # Pre-configure ACL with reader role
    mock_calendar_service.set_calendar_acl(
        "calendar_alpha",
        [
            {
                "role": "reader",
                "scope": {"type": "user", "value": "upgrade@example.com"},
            }
        ],
    )

    result = await mcp_client.call_tool(
        "calendar_grant_access",
        {
            "project_key": "ALPHA",
            "user_email": "upgrade@example.com",
            "role": "owner",
        },
    )

    assert result is not None
    mock_calendar_service.grant_project_access.assert_called_once_with(
        project_key="ALPHA",
        user_email="upgrade@example.com",
        role="owner",
    )


@pytest.mark.asyncio
async def test_calendar_grant_access_invalid_role(
    mcp_client: Client,
    mock_calendar_service: MockCalendarService,
) -> None:
    """Test error handling for invalid role."""
    with pytest.raises(Exception):  # Will be ToolError wrapping CalendarError
        await mcp_client.call_tool(
            "calendar_grant_access",
            {
                "project_key": "ALPHA",
                "user_email": "user@example.com",
                "role": "admin",  # Invalid role
            },
        )


@pytest.mark.asyncio
async def test_calendar_grant_access_default_role(
    mcp_client: Client,
    mock_calendar_service: MockCalendarService,
) -> None:
    """Test granting access with default role (writer)."""
    result = await mcp_client.call_tool(
        "calendar_grant_access",
        {
            "project_key": "DELTA",
            "user_email": "defaultuser@example.com",
            # role parameter omitted - should default to 'writer'
        },
    )

    assert result is not None
    mock_calendar_service.grant_project_access.assert_called_once_with(
        project_key="DELTA",
        user_email="defaultuser@example.com",
        role="writer",
    )


@pytest.mark.asyncio
async def test_calendar_grant_access_reader_role(
    mcp_client: Client,
    mock_calendar_service: MockCalendarService,
) -> None:
    """Test granting read-only access."""
    result = await mcp_client.call_tool(
        "calendar_grant_access",
        {
            "project_key": "BETA",
            "user_email": "readonly@example.com",
            "role": "reader",
        },
    )

    assert result is not None
    mock_calendar_service.grant_project_access.assert_called_once_with(
        project_key="BETA",
        user_email="readonly@example.com",
        role="reader",
    )


# Unit tests for CalendarService methods (PHASE 2 security improvements)
from pm_mcp.services.calendar_service import CalendarService


class TestCalendarMetadataParsing:
    """Tests for _parse_calendar_metadata (JSON + legacy support)."""

    def test_parse_json_metadata(self) -> None:
        """Test parsing JSON metadata format."""
        service = CalendarService()
        description = '{"jira_project_key": "ALPHA", "version": "v1"}'
        result = service._parse_calendar_metadata(description)

        assert result["jira_project_key"] == "ALPHA"
        assert result.get("confluence_space_key") is None

    def test_parse_json_metadata_with_confluence(self) -> None:
        """Test parsing JSON metadata with Confluence key."""
        service = CalendarService()
        description = '{"jira_project_key": "BETA", "confluence_space_key": "BETA", "version": "v1"}'
        result = service._parse_calendar_metadata(description)

        assert result["jira_project_key"] == "BETA"
        assert result["confluence_space_key"] == "BETA"

    def test_parse_legacy_metadata(self) -> None:
        """Test parsing legacy key=value metadata format."""
        service = CalendarService()
        description = "jira_project_key=GAMMA\nconfluence_space_key=GAMMA"
        result = service._parse_calendar_metadata(description)

        assert result["jira_project_key"] == "GAMMA"
        assert result["confluence_space_key"] == "GAMMA"

    def test_parse_legacy_metadata_single_line(self) -> None:
        """Test parsing legacy format with single line."""
        service = CalendarService()
        description = "jira_project_key=DELTA"
        result = service._parse_calendar_metadata(description)

        assert result["jira_project_key"] == "DELTA"
        assert result.get("confluence_space_key") is None

    def test_parse_empty_metadata(self) -> None:
        """Test parsing empty description."""
        service = CalendarService()
        result = service._parse_calendar_metadata(None)

        assert result["jira_project_key"] is None
        assert result["confluence_space_key"] is None

    def test_parse_corrupted_json_falls_back_to_legacy(self) -> None:
        """Test fallback to legacy format when JSON is corrupted."""
        service = CalendarService()
        # Invalid JSON but valid legacy format
        description = "{invalid json\njira_project_key=EPSILON"
        result = service._parse_calendar_metadata(description)

        # Should fallback to legacy parsing
        assert result["jira_project_key"] == "EPSILON"

    def test_parse_json_metadata_whitelist_validation(self) -> None:
        """Test that unknown keys are filtered out (whitelist)."""
        service = CalendarService()
        description = '{"jira_project_key": "ZETA", "unknown_key": "value", "version": "v1"}'
        result = service._parse_calendar_metadata(description)

        assert result["jira_project_key"] == "ZETA"
        assert "unknown_key" not in result


class TestDateFormatNormalization:
    """Tests for _normalize_date_format."""

    def test_normalize_datetime_event(self) -> None:
        """Test normalizing timed event (dateTime)."""
        result = CalendarService._normalize_date_format(
            {"dateTime": "2024-01-15T10:00:00Z", "timeZone": "UTC"}
        )

        assert result["time"] == "2024-01-15T10:00:00Z"
        assert result["is_all_day"] is False

    def test_normalize_all_day_event(self) -> None:
        """Test normalizing all-day event (date)."""
        result = CalendarService._normalize_date_format(
            {"date": "2024-01-15"}
        )

        assert result["time"] == "2024-01-15"
        assert result["is_all_day"] is True

    def test_normalize_empty_event_time(self) -> None:
        """Test normalizing empty event time."""
        result = CalendarService._normalize_date_format({})

        assert result["time"] is None
        assert result["is_all_day"] is False
