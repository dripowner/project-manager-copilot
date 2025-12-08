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
    start: str = Field(description="Event start time (ISO 8601)")
    end: str = Field(description="Event end time (ISO 8601)")
    location: str | None = Field(default=None, description="Event location")
    attendees: list[str] | None = Field(
        default=None, description="List of attendee names/emails"
    )


class CalendarListEventsResponse(BaseMcpModel):
    """Response model for calendar_list_events tool."""

    events: list[CalendarEvent] = Field(description="List of calendar events")
