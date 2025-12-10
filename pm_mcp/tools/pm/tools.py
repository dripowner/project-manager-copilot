"""PM layer MCP tools implementation."""

from datetime import datetime
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.context import Context
from pydantic import Field

from pm_mcp.core.errors import PmError
from pm_mcp.tools.jira.models import JiraIssueSummary
from pm_mcp.tools.pm.models import (
    PmGetMeetingIssuesResponse,
    PmLinkMeetingIssuesResponse,
    PmProjectSnapshot,
)


def register_pm_tools(mcp: FastMCP) -> None:
    """Register PM layer tools with the MCP server.

    Tools access services via ctx.fastmcp (jira_service, pm_service).
    """

    @mcp.tool(
        name="pm_link_meeting_issues",
        description="Link a calendar meeting to Jira issues. "
        "Use after creating issues from action items to maintain traceability.",
    )
    async def pm_link_meeting_issues(
        calendar_event_id: Annotated[
            str, Field(description="Google Calendar event ID")
        ],
        jira_issue_keys: Annotated[
            list[str],
            Field(description="List of Jira issue keys (e.g., ['PROJ-1', 'PROJ-2'])"),
        ],
        ctx: Context,
        confluence_page_id: Annotated[
            str | None,
            Field(description="Optional Confluence page ID with meeting notes"),
        ] = None,
        meeting_title: Annotated[
            str | None,
            Field(description="Optional meeting title for reference"),
        ] = None,
        meeting_date: Annotated[
            datetime | None,
            Field(description="Optional meeting date"),
        ] = None,
        project_key: Annotated[
            str | None,
            Field(description="Optional project key for filtering"),
        ] = None,
    ) -> PmLinkMeetingIssuesResponse:
        """Link meeting to Jira issues."""
        await ctx.info(
            f"Linking meeting {calendar_event_id} to {len(jira_issue_keys)} issues"
        )
        try:
            pm_service = ctx.fastmcp.pm_service  # type: ignore[attr-defined]
            calendar_service = ctx.fastmcp.calendar_service  # type: ignore[attr-defined]
            jira_service = ctx.fastmcp.jira_service  # type: ignore[attr-defined]

            if pm_service is None:
                raise ToolError("PM service not available")
            if calendar_service is None:
                raise ToolError("Calendar service not available")
            if jira_service is None:
                raise ToolError("Jira service not available")

            await ctx.debug(
                f"Issue keys: {jira_issue_keys}, "
                f"confluence_page_id={confluence_page_id}"
            )
            result = await pm_service.link_meeting_issues(
                calendar_service=calendar_service,
                jira_service=jira_service,
                meeting_id=calendar_event_id,
                issue_keys=jira_issue_keys,
                confluence_page_id=confluence_page_id,
                meeting_title=meeting_title,
                meeting_date=meeting_date,
                project_key=project_key,
            )

            # Предупредить если были ошибки с labels
            if "label_errors" in result:
                await ctx.warning(
                    f"Some Jira labels failed to add: {result['label_errors']}"
                )

            await ctx.info("Successfully linked meeting to issues")
            return PmLinkMeetingIssuesResponse(
                calendar_event_id=result["meeting_id"],
                jira_issue_keys=result["issue_keys"],
                confluence_page_id=result["confluence_page_id"],
            )

        except PmError as e:
            raise ToolError(e.message) from e
        except ToolError:
            raise
        except Exception as e:
            raise ToolError(f"Failed to link meeting to issues: {e}") from e

    @mcp.tool(
        name="pm_get_meeting_issues",
        description="Get Jira issues linked to a meeting. "
        "Use to check status of action items from a specific meeting.",
    )
    async def pm_get_meeting_issues(
        calendar_event_id: Annotated[
            str, Field(description="Google Calendar event ID")
        ],
        ctx: Context,
    ) -> PmGetMeetingIssuesResponse:
        """Get issues linked to a meeting."""
        await ctx.info(f"Getting issues linked to meeting: {calendar_event_id}")
        try:
            pm_service = ctx.fastmcp.pm_service  # type: ignore[attr-defined]
            calendar_service = ctx.fastmcp.calendar_service  # type: ignore[attr-defined]
            jira_service = ctx.fastmcp.jira_service  # type: ignore[attr-defined]

            if pm_service is None:
                raise ToolError("PM service not available")
            if calendar_service is None:
                raise ToolError("Calendar service not available")

            # Get meeting link data from Calendar
            meeting_data = await pm_service.get_meeting_issues(
                calendar_service=calendar_service,
                meeting_id=calendar_event_id
            )

            # Get current issue details from Jira using direct lookup
            issue_keys = meeting_data.get("issue_keys", [])
            issues = []

            if issue_keys:
                await ctx.debug(f"Fetching {len(issue_keys)} linked issues from Jira")
                # Fetch each issue directly by key (more efficient than text search)
                for key in issue_keys:
                    try:
                        issue = await jira_service.get_issue(key)
                        if issue:
                            issues.append(JiraIssueSummary(**issue))
                    except Exception:
                        await ctx.warning(f"Could not fetch issue: {key}")

            await ctx.info(f"Retrieved {len(issues)} issues for meeting")
            return PmGetMeetingIssuesResponse(
                calendar_event_id=calendar_event_id,
                issues=issues,
                confluence_page_id=meeting_data.get("confluence_page_id"),
                meeting_title=meeting_data.get("meeting_title"),
                meeting_date=meeting_data.get("meeting_date"),
            )

        except PmError as e:
            raise ToolError(e.message) from e
        except ToolError:
            raise
        except Exception as e:
            raise ToolError(f"Failed to get meeting issues: {e}") from e

    @mcp.tool(
        name="pm_get_project_snapshot",
        description="Get aggregated project statistics. "
        "Use for quick project health overview: open/in-progress/done counts, "
        "overdue issues, workload by assignee.",
    )
    async def pm_get_project_snapshot(
        project_key: Annotated[str, Field(description="Jira project key")],
        ctx: Context,
        since: Annotated[
            str | None,
            Field(description="Optional: count progress from this date (ISO 8601)"),
        ] = None,
    ) -> PmProjectSnapshot:
        """Get project statistics snapshot."""
        await ctx.info(f"Getting project snapshot for: {project_key}")
        try:
            pm_service = ctx.fastmcp.pm_service  # type: ignore[attr-defined]
            jira_service = ctx.fastmcp.jira_service  # type: ignore[attr-defined]

            if pm_service is None:
                raise ToolError("PM service not available")

            if since:
                await ctx.debug(f"Calculating progress since: {since}")
            result = await pm_service.get_project_snapshot(
                project_key=project_key,
                jira_service=jira_service,
                since=since,
            )

            await ctx.info(
                f"Snapshot: {result.get('total_issues', 0)} total issues, "
                f"{result.get('overdue_count', 0)} overdue"
            )
            return PmProjectSnapshot(**result)

        except PmError as e:
            raise ToolError(e.message) from e
        except ToolError:
            raise
        except Exception as e:
            raise ToolError(f"Failed to get project snapshot: {e}") from e
