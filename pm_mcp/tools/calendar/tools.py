"""Calendar MCP tools implementation."""

from datetime import datetime
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.context import Context
from pydantic import Field

from pm_mcp.core.errors import CalendarError
from pm_mcp.tools.calendar.models import CalendarEvent, CalendarListEventsResponse


def register_calendar_tools(mcp: FastMCP) -> None:
    """Register calendar tools with the MCP server.

    Tools access CalendarService via ctx.fastmcp.calendar_service.
    """

    @mcp.tool(
        name="calendar_list_events",
        description="List calendar events/meetings in the specified time range. "
        "Use this to find meetings for briefings, action item extraction, or scheduling.",
    )
    async def calendar_list_events(
        ctx: Context,
        time_min: Annotated[
            datetime | None,
            Field(description="Start of time range (ISO 8601). Default: now - 7 days"),
        ] = None,
        time_max: Annotated[
            datetime | None,
            Field(description="End of time range (ISO 8601). Default: now + 7 days"),
        ] = None,
        text_query: Annotated[
            str | None,
            Field(description="Optional text search in event summary/description"),
        ] = None,
        max_results: Annotated[
            int,
            Field(
                ge=1, le=250, description="Maximum number of events to return (1-250)"
            ),
        ] = 50,
    ) -> CalendarListEventsResponse:
        """List calendar events in time range."""
        await ctx.info("Fetching calendar events")
        try:
            calendar_service = ctx.fastmcp.calendar_service  # type: ignore[attr-defined]
            await ctx.debug(
                f"Params: time_min={time_min}, time_max={time_max}, "
                f"text_query={text_query}, max_results={max_results}"
            )
            events = await calendar_service.list_events(
                time_min=time_min,
                time_max=time_max,
                text_query=text_query,
                max_results=max_results,
            )

            await ctx.info(f"Found {len(events)} calendar events")
            return CalendarListEventsResponse(
                events=[CalendarEvent(**event) for event in events]
            )

        except CalendarError as e:
            raise ToolError(e.message) from e
        except Exception as e:
            raise ToolError(f"Failed to list calendar events: {e}") from e
