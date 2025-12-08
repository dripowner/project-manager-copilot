"""Pydantic models for Jira tools."""

from pydantic import Field

from pm_mcp.core.models import BaseMcpModel


# Issue models
class JiraIssueSummary(BaseMcpModel):
    """Summary of a Jira issue."""

    key: str = Field(description="Issue key (e.g., PROJ-123)")
    id: str = Field(description="Internal Jira issue ID")
    url: str = Field(description="Direct URL to issue in Jira")
    summary: str = Field(description="Issue summary/title")
    status: str = Field(description="Current status name")
    status_category: str | None = Field(
        default=None,
        description="Status category: 'To Do', 'In Progress', or 'Done'",
    )
    assignee: str | None = Field(
        default=None, description="Assignee display name or email"
    )
    labels: list[str] | None = Field(default=None, description="Issue labels")
    due_date: str | None = Field(default=None, description="Due date (ISO 8601)")
    updated: str | None = Field(
        default=None, description="Last update timestamp (ISO 8601)"
    )


class JiraCreatedIssue(BaseMcpModel):
    """Created Jira issue response."""

    key: str = Field(description="Issue key (e.g., PROJ-123)")
    id: str = Field(description="Internal Jira issue ID")
    url: str = Field(description="Direct URL to issue in Jira")


# List issues models
class JiraListIssuesRequest(BaseMcpModel):
    """Request model for jira_list_issues tool."""

    project_key: str = Field(description="Jira project key (e.g., PROJ)")
    status_category: str | None = Field(
        default=None,
        description="Filter by status category: 'To Do', 'In Progress', or 'Done'",
    )
    assignee: str | None = Field(
        default=None,
        description="Filter by assignee (account ID or email)",
    )
    labels: list[str] | None = Field(
        default=None,
        description="Filter by labels (OR logic)",
    )
    updated_from: str | None = Field(
        default=None,
        description="Filter: updated after this date (ISO 8601)",
    )
    updated_to: str | None = Field(
        default=None,
        description="Filter: updated before this date (ISO 8601)",
    )
    text_query: str | None = Field(
        default=None,
        description="Text search in summary/description",
    )
    max_results: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum issues to return (1-100)",
    )


class JiraListIssuesResponse(BaseMcpModel):
    """Response model for jira_list_issues tool."""

    issues: list[JiraIssueSummary] = Field(description="List of matching issues")


# Create issues batch models
class JiraIssueToCreate(BaseMcpModel):
    """Single issue to create in batch."""

    summary: str = Field(description="Issue summary/title")
    description: str | None = Field(default=None, description="Issue description")
    issue_type: str | None = Field(
        default="Task",
        description="Issue type (e.g., Task, Bug, Story)",
    )
    assignee: str | None = Field(
        default=None,
        description="Assignee account ID or email",
    )
    labels: list[str] | None = Field(default=None, description="Labels to add")
    due_date: str | None = Field(
        default=None,
        description="Due date (ISO 8601 date)",
    )
    meeting_ref: str | None = Field(
        default=None,
        description="Reference to meeting (Confluence URL or Calendar ID)",
    )


class JiraCreateIssuesBatchRequest(BaseMcpModel):
    """Request model for jira_create_issues_batch tool."""

    project_key: str = Field(description="Jira project key (e.g., PROJ)")
    issues: list[JiraIssueToCreate] = Field(description="List of issues to create")


class JiraCreateIssuesBatchResponse(BaseMcpModel):
    """Response model for jira_create_issues_batch tool."""

    created: list[JiraCreatedIssue] = Field(description="List of created issues")


# Update issue models
class JiraUpdateIssueRequest(BaseMcpModel):
    """Request model for jira_update_issue tool."""

    issue_key: str = Field(description="Issue key (e.g., PROJ-123)")
    summary: str | None = Field(default=None, description="New summary")
    description: str | None = Field(default=None, description="New description")
    status: str | None = Field(
        default=None,
        description="New status (must be valid transition)",
    )
    assignee: str | None = Field(
        default=None,
        description="New assignee account ID",
    )
    labels: list[str] | None = Field(default=None, description="Replace labels")
    due_date: str | None = Field(default=None, description="New due date")


class JiraUpdateIssueResponse(BaseMcpModel):
    """Response model for jira_update_issue tool."""

    key: str = Field(description="Issue key")
    url: str = Field(description="Direct URL to issue")


# Add comment models
class JiraAddCommentRequest(BaseMcpModel):
    """Request model for jira_add_comment tool."""

    issue_key: str = Field(description="Issue key (e.g., PROJ-123)")
    body: str = Field(description="Comment text")


class JiraAddCommentResponse(BaseMcpModel):
    """Response model for jira_add_comment tool."""

    issue_key: str = Field(description="Issue key")
    comment_id: str = Field(description="Created comment ID")
