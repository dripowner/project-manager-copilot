"""Calendar MCP tools implementation."""

from datetime import datetime
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.context import Context
from pydantic import Field

from pm_mcp.core.errors import CalendarError
from pm_mcp.tools.calendar.models import (
    AccessInfo,
    CalendarAccessVerificationResponse,
    CalendarEvent,
    CalendarFindResponse,
    CalendarGrantAccessResponse,
    CalendarInfo,
    CalendarListEventsResponse,
    CalendarListResponse,
    GrantedAccessInfo,
)


def register_calendar_tools(mcp: FastMCP) -> None:
    """Register calendar tools with the MCP server.

    Tools access CalendarService via ctx.fastmcp.calendar_service.
    """

    @mcp.tool(
        name="calendar_list_events",
        description="List calendar events/meetings in the specified time range. "
        "Use this to find meetings for briefings, action item extraction, or scheduling. "
        "Provide either project_key (recommended) or calendar_id.",
    )
    async def calendar_list_events(
        ctx: Context,
        project_key: Annotated[
            str | None,
            Field(description="Jira project key to find calendar (e.g., 'ALPHA')"),
        ] = None,
        calendar_id: Annotated[
            str | None,
            Field(description="Direct calendar ID (alternative to project_key)"),
        ] = None,
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

            # Validate: at least one identifier provided
            if not project_key and not calendar_id:
                raise ToolError("Must provide either project_key or calendar_id")

            # Resolve calendar_id from project_key if needed
            resolved_calendar_id = calendar_id
            if project_key:
                await ctx.debug(f"Resolving calendar for project: {project_key}")
                calendar = await calendar_service.find_or_create_project_calendar(
                    project_key=project_key
                )
                resolved_calendar_id = calendar["calendar_id"]
                await ctx.debug(f"Resolved calendar_id: {resolved_calendar_id}")

            await ctx.debug(
                f"Params: calendar_id={resolved_calendar_id}, time_min={time_min}, "
                f"time_max={time_max}, text_query={text_query}, max_results={max_results}"
            )

            events = await calendar_service.list_events(
                calendar_id=resolved_calendar_id,
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

    @mcp.tool(
        name="calendar_list_calendars",
        description="List all calendars accessible to the service account with metadata. "
        "Use this to discover available project calendars and their mappings.",
    )
    async def calendar_list_calendars(ctx: Context) -> CalendarListResponse:
        """List all calendars with metadata."""
        await ctx.info("Listing all calendars")
        try:
            calendar_service = ctx.fastmcp.calendar_service  # type: ignore[attr-defined]
            calendars = await calendar_service.list_calendars()

            await ctx.info(f"Found {len(calendars)} calendars")
            return CalendarListResponse(
                calendars=[CalendarInfo(**cal) for cal in calendars]
            )

        except CalendarError as e:
            raise ToolError(e.message) from e
        except Exception as e:
            raise ToolError(f"Failed to list calendars: {e}") from e

    @mcp.tool(
        name="calendar_find_project_calendar",
        description="Find calendar for a Jira project by project key. "
        "Creates a new calendar if not found. Calendar name = project_key. "
        "Use this before working with project-specific meetings.",
    )
    async def calendar_find_project_calendar(
        project_key: Annotated[
            str, Field(description="Jira project key (e.g., 'ALPHA')")
        ],
        ctx: Context,
        confluence_space_key: Annotated[
            str | None,
            Field(description="Optional Confluence space key for metadata"),
        ] = None,
    ) -> CalendarFindResponse:
        """Find or create calendar for project."""
        await ctx.info(f"Finding calendar for project: {project_key}")
        try:
            calendar_service = ctx.fastmcp.calendar_service  # type: ignore[attr-defined]
            calendar = await calendar_service.find_or_create_project_calendar(
                project_key=project_key,
                confluence_space_key=confluence_space_key,
            )

            created = calendar.get("created", False)
            if created:
                await ctx.info(f"Created new calendar for project {project_key}")
            else:
                await ctx.info(f"Found existing calendar for project {project_key}")

            return CalendarFindResponse(
                calendar=CalendarInfo(**calendar),
                created=created,
            )

        except CalendarError as e:
            raise ToolError(e.message) from e
        except Exception as e:
            raise ToolError(f"Failed to find/create calendar: {e}") from e

    @mcp.tool(
        name="calendar_verify_project_access",
        description="Verify user access to project calendar via ACL. "
        "Use this to troubleshoot calendar access issues or validate permissions before operations. "
        "Returns detailed access information including user role, ACL status, and troubleshooting data. "
        "Automatically finds/creates calendar for the project.",
    )
    async def calendar_verify_project_access(
        project_key: Annotated[
            str,
            Field(description="Jira project key (e.g., 'ALPHA', 'BETA')"),
        ],
        ctx: Context,
        user_email: Annotated[
            str | None,
            Field(
                description="User email to verify access for. "
                "If not provided, uses calendar_owner_email from settings. "
                "Example: 'user@example.com'"
            ),
        ] = None,
    ) -> CalendarAccessVerificationResponse:
        """Verify user access to project calendar via ACL."""
        email_info = f" for {user_email}" if user_email else " (using default email)"
        await ctx.info(
            f"Verifying calendar access for project '{project_key}'{email_info}"
        )

        try:
            calendar_service = ctx.fastmcp.calendar_service  # type: ignore[attr-defined]

            result = await calendar_service.verify_project_access(
                project_key=project_key,
                user_email=user_email,
            )

            # Build human-readable message
            calendar_name = result["calendar"]["name"]
            checked_email = result["user_email"]
            has_access = result["has_access"]
            role = result["role"]
            acl_count = result["acl_entries_count"]

            if has_access:
                access_status = f"HAS ACCESS with role '{role}'"
            else:
                access_status = "does NOT have access"

            message = (
                f"User '{checked_email}' {access_status} "
                f"to calendar '{calendar_name}' (project: {project_key}). "
                f"Total ACL entries: {acl_count}"
            )

            if result["calendar"].get("created"):
                message += " [Calendar was just created - ACL not yet configured]"

            await ctx.info(message)

            return CalendarAccessVerificationResponse(
                calendar=CalendarInfo(**result["calendar"]),
                access=AccessInfo(
                    has_access=result["has_access"],
                    role=result["role"],
                    user_email=result["user_email"],
                    acl_entries_count=result["acl_entries_count"],
                    service_account_email=result["service_account_email"],
                ),
                message=message,
            )

        except CalendarError as e:
            await ctx.error(f"Calendar access verification failed: {e.message}")
            raise ToolError(e.message) from e
        except Exception as e:
            await ctx.error(f"Unexpected error during access verification: {e}")
            raise ToolError(f"Failed to verify calendar access: {e}") from e

    @mcp.tool(
        name="calendar_grant_access",
        description="Grant calendar access to user by adding/updating ACL entry. "
        "Use this to share project calendars with team members. "
        "Automatically finds/creates calendar for the project. "
        "Supports role updates if user already has access with different role. "
        "Idempotent: safe to call multiple times with same parameters.",
    )
    async def calendar_grant_access(
        project_key: Annotated[
            str,
            Field(description="Jira project key (e.g., 'ALPHA', 'BETA')"),
        ],
        user_email: Annotated[
            str,
            Field(
                description="Email address to grant access to. Example: 'user@example.com'"
            ),
        ],
        ctx: Context,
        role: Annotated[
            str,
            Field(
                description="ACL role to grant. Options: 'owner', 'writer', 'reader', 'freeBusyReader'. "
                "Default: 'writer' (can create/edit events)"
            ),
        ] = "writer",
    ) -> CalendarGrantAccessResponse:
        """Grant calendar access to user via ACL."""
        await ctx.info(
            f"Granting '{role}' access to '{user_email}' for project '{project_key}'"
        )

        try:
            calendar_service = ctx.fastmcp.calendar_service  # type: ignore[attr-defined]

            result = await calendar_service.grant_project_access(
                project_key=project_key,
                user_email=user_email,
                role=role,
            )

            # Build human-readable message
            calendar_name = result["calendar"]["name"]
            action_taken = result["action_taken"]
            granted_role = result["role"]
            previous_role = result["previous_role"]

            if action_taken == "granted":
                message = (
                    f"Successfully granted '{granted_role}' access to '{user_email}' "
                    f"for calendar '{calendar_name}' (project: {project_key})"
                )
            elif action_taken == "updated":
                message = (
                    f"Updated access for '{user_email}' on calendar '{calendar_name}' "
                    f"(project: {project_key}): '{previous_role}' -> '{granted_role}'"
                )
            else:  # already_exists
                message = (
                    f"User '{user_email}' already has '{granted_role}' access "
                    f"to calendar '{calendar_name}' (project: {project_key}). No changes made."
                )

            await ctx.info(message)

            return CalendarGrantAccessResponse(
                calendar=CalendarInfo(**result["calendar"]),
                access=GrantedAccessInfo(
                    user_email=result["user_email"],
                    role=result["role"],
                    action_taken=result["action_taken"],
                    previous_role=result["previous_role"],
                ),
                message=message,
            )

        except CalendarError as e:
            await ctx.error(f"Failed to grant calendar access: {e.message}")
            raise ToolError(e.message) from e
        except Exception as e:
            await ctx.error(f"Unexpected error during access grant: {e}")
            raise ToolError(f"Failed to grant calendar access: {e}") from e
