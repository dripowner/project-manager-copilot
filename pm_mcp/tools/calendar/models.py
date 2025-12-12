"""Pydantic models for calendar tools."""

from datetime import datetime

from pydantic import Field

from pm_mcp.core.models import BaseMcpModel


class CalendarListEventsRequest(BaseMcpModel):
    """Request model for calendar_list_events tool."""

    time_min: datetime | None = Field(
        default=None,
        description="Start of time range (ISO 8601). Default: now - 7 days",
    )
    time_max: datetime | None = Field(
        default=None,
        description="End of time range (ISO 8601). Default: now + 7 days",
    )
    text_query: str | None = Field(
        default=None,
        description="Optional text search in event summary/description",
    )
    max_results: int = Field(
        default=50,
        ge=1,
        le=250,
        description="Maximum number of events to return",
    )


class CalendarEvent(BaseMcpModel):
    """Calendar event model."""

    id: str = Field(description="Event ID")
    summary: str = Field(description="Event title/summary")
    description: str | None = Field(default=None, description="Event description")
    start: str | None = Field(default=None, description="Event start time (ISO 8601)")
    end: str | None = Field(default=None, description="Event end time (ISO 8601)")
    location: str | None = Field(default=None, description="Event location")
    attendees: list[str] | None = Field(
        default=None, description="List of attendee names/emails"
    )


class CalendarListEventsResponse(BaseMcpModel):
    """Response model for calendar_list_events tool."""

    events: list[CalendarEvent] = Field(description="List of calendar events")


class CalendarInfo(BaseMcpModel):
    """Calendar information with metadata."""

    calendar_id: str = Field(description="Calendar ID")
    name: str = Field(description="Calendar display name")
    description: str | None = Field(
        default=None, description="Calendar description (contains metadata)"
    )
    primary: bool = Field(
        default=False, description="Whether this is the primary calendar"
    )
    jira_project_key: str | None = Field(
        default=None, description="Jira project key from metadata"
    )
    confluence_space_key: str | None = Field(
        default=None, description="Confluence space key from metadata"
    )
    created: bool | None = Field(
        default=None, description="Flag indicating if calendar was just created"
    )


class CalendarListResponse(BaseMcpModel):
    """Response model for calendar_list_calendars tool."""

    calendars: list[CalendarInfo] = Field(description="List of calendars with metadata")


class CalendarFindResponse(BaseMcpModel):
    """Response model for calendar_find_project_calendar tool."""

    calendar: CalendarInfo = Field(description="Calendar information")
    created: bool = Field(
        description="True if calendar was created, False if found existing"
    )
