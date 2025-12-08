"""Pydantic models for PM tools."""

from datetime import datetime

from pydantic import Field

from pm_mcp.core.models import BaseMcpModel
from pm_mcp.tools.jira.models import JiraIssueSummary


# Link meeting issues models
class PmLinkMeetingIssuesRequest(BaseMcpModel):
    """Request model for pm_link_meeting_issues tool."""

    calendar_event_id: str = Field(description="Google Calendar event ID")
    jira_issue_keys: list[str] = Field(
        description="List of Jira issue keys to link (e.g., ['PROJ-1', 'PROJ-2'])"
    )
    confluence_page_id: str | None = Field(
        default=None,
        description="Optional Confluence page ID with meeting notes",
    )
    meeting_title: str | None = Field(
        default=None,
        description="Optional meeting title for reference",
    )
    meeting_date: datetime | None = Field(
        default=None,
        description="Optional meeting date",
    )
    project_key: str | None = Field(
        default=None,
        description="Optional project key for filtering",
    )


class PmLinkMeetingIssuesResponse(BaseMcpModel):
    """Response model for pm_link_meeting_issues tool."""

    calendar_event_id: str = Field(description="Calendar event ID")
    jira_issue_keys: list[str] = Field(description="Linked issue keys")
    confluence_page_id: str | None = Field(
        default=None, description="Linked Confluence page ID"
    )


# Get meeting issues models
class PmGetMeetingIssuesRequest(BaseMcpModel):
    """Request model for pm_get_meeting_issues tool."""

    calendar_event_id: str = Field(description="Google Calendar event ID")


class PmGetMeetingIssuesResponse(BaseMcpModel):
    """Response model for pm_get_meeting_issues tool."""

    calendar_event_id: str = Field(description="Calendar event ID")
    issues: list[JiraIssueSummary] = Field(
        description="List of linked Jira issues with current status"
    )
    confluence_page_id: str | None = Field(
        default=None, description="Linked Confluence page ID"
    )
    meeting_title: str | None = Field(default=None, description="Meeting title")
    meeting_date: str | None = Field(default=None, description="Meeting date")


# Project snapshot models
class PmGetProjectSnapshotRequest(BaseMcpModel):
    """Request model for pm_get_project_snapshot tool."""

    project_key: str = Field(description="Jira project key")
    since: str | None = Field(
        default=None,
        description="Optional: count progress from this date (ISO 8601)",
    )


class PmProjectSnapshot(BaseMcpModel):
    """Project statistics snapshot."""

    project_key: str = Field(description="Project key")
    total_open: int = Field(description="Issues in 'To Do' status category")
    total_in_progress: int = Field(
        description="Issues in 'In Progress' status category"
    )
    total_done: int = Field(description="Issues in 'Done' status category")
    total_overdue: int = Field(description="Open issues past due date")
    by_assignee: dict[str, int] | None = Field(
        default=None,
        description="Issue count per assignee",
    )
