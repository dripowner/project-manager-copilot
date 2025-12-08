"""Jira MCP tools implementation."""

from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.context import Context
from pydantic import Field

from pm_mcp.core.errors import JiraError
from pm_mcp.tools.jira.models import (
    JiraAddCommentResponse,
    JiraCreateIssuesBatchResponse,
    JiraCreatedIssue,
    JiraIssueSummary,
    JiraIssueToCreate,
    JiraListIssuesResponse,
    JiraUpdateIssueResponse,
)


def register_jira_tools(mcp: FastMCP) -> None:
    """Register Jira tools with the MCP server.

    Tools access JiraService via ctx.fastmcp.jira_service.
    """

    @mcp.tool(
        name="jira_list_issues",
        description="List Jira issues with filters. "
        "Use to find tasks by project, status, assignee, labels, or text search. "
        "No need to write JQL - filters are applied automatically.",
    )
    async def jira_list_issues(
        project_key: Annotated[str, Field(description="Jira project key (e.g., PROJ)")],
        ctx: Context,
        status_category: Annotated[
            str | None,
            Field(
                description="Filter by status category: 'To Do', 'In Progress', or 'Done'"
            ),
        ] = None,
        assignee: Annotated[
            str | None,
            Field(description="Filter by assignee (account ID or email)"),
        ] = None,
        labels: Annotated[
            list[str] | None,
            Field(description="Filter by labels (OR logic)"),
        ] = None,
        updated_from: Annotated[
            str | None,
            Field(description="Filter: updated after this date (ISO 8601)"),
        ] = None,
        updated_to: Annotated[
            str | None,
            Field(description="Filter: updated before this date (ISO 8601)"),
        ] = None,
        text_query: Annotated[
            str | None,
            Field(description="Text search in summary/description"),
        ] = None,
        max_results: Annotated[
            int,
            Field(ge=1, le=100, description="Maximum issues to return (1-100)"),
        ] = 50,
    ) -> JiraListIssuesResponse:
        """List Jira issues with filters."""
        await ctx.info(f"Listing Jira issues for project: {project_key}")
        try:
            jira_service = ctx.fastmcp.jira_service  # type: ignore[attr-defined]
            await ctx.debug(
                f"Filters: status_category={status_category}, assignee={assignee}, "
                f"labels={labels}, text_query={text_query}"
            )
            issues = await jira_service.list_issues(
                project_key=project_key,
                status_category=status_category,
                assignee=assignee,
                labels=labels,
                updated_from=updated_from,
                updated_to=updated_to,
                text_query=text_query,
                max_results=max_results,
            )

            await ctx.info(f"Found {len(issues)} Jira issues")
            return JiraListIssuesResponse(
                issues=[JiraIssueSummary(**issue) for issue in issues]
            )

        except JiraError as e:
            raise ToolError(e.message) from e
        except Exception as e:
            raise ToolError(f"Failed to list Jira issues: {e}") from e

    @mcp.tool(
        name="jira_create_issues_batch",
        description="Create multiple Jira issues from action items. "
        "Use after extracting action items from meeting protocols to create tasks.",
    )
    async def jira_create_issues_batch(
        project_key: Annotated[str, Field(description="Jira project key (e.g., PROJ)")],
        issues: Annotated[
            list[JiraIssueToCreate],
            Field(description="List of issues to create"),
        ],
        ctx: Context,
    ) -> JiraCreateIssuesBatchResponse:
        """Create multiple Jira issues."""
        await ctx.info(f"Creating {len(issues)} Jira issues in project: {project_key}")
        try:
            jira_service = ctx.fastmcp.jira_service  # type: ignore[attr-defined]
            # Convert to dict for service
            issues_data = [issue.model_dump() for issue in issues]

            await ctx.debug(f"Issue summaries: {[i.summary for i in issues]}")
            created = await jira_service.create_issues_batch(
                project_key=project_key,
                issues=issues_data,
            )

            await ctx.info(f"Successfully created {len(created)} issues")
            return JiraCreateIssuesBatchResponse(
                created=[JiraCreatedIssue(**issue) for issue in created]
            )

        except JiraError as e:
            raise ToolError(e.message) from e
        except Exception as e:
            raise ToolError(f"Failed to create Jira issues: {e}") from e

    @mcp.tool(
        name="jira_update_issue",
        description="Update a Jira issue. "
        "Use to change status, assignee, due date, or other fields. "
        "For status changes, use the human-readable status name.",
    )
    async def jira_update_issue(
        issue_key: Annotated[str, Field(description="Issue key (e.g., PROJ-123)")],
        ctx: Context,
        summary: Annotated[str | None, Field(description="New summary")] = None,
        description: Annotated[str | None, Field(description="New description")] = None,
        status: Annotated[
            str | None,
            Field(description="New status (must be valid transition)"),
        ] = None,
        assignee: Annotated[
            str | None,
            Field(description="New assignee account ID"),
        ] = None,
        labels: Annotated[list[str] | None, Field(description="Replace labels")] = None,
        due_date: Annotated[str | None, Field(description="New due date")] = None,
    ) -> JiraUpdateIssueResponse:
        """Update a Jira issue."""
        await ctx.info(f"Updating Jira issue: {issue_key}")
        try:
            jira_service = ctx.fastmcp.jira_service  # type: ignore[attr-defined]
            # Build list of fields being updated
            updates = []
            if summary:
                updates.append("summary")
            if description:
                updates.append("description")
            if status:
                updates.append(f"status={status}")
            if assignee:
                updates.append("assignee")
            if labels:
                updates.append("labels")
            if due_date:
                updates.append("due_date")
            await ctx.debug(f"Updating fields: {updates}")

            result = await jira_service.update_issue(
                issue_key=issue_key,
                summary=summary,
                description=description,
                status=status,
                assignee=assignee,
                labels=labels,
                due_date=due_date,
            )

            await ctx.info(f"Successfully updated issue: {issue_key}")
            return JiraUpdateIssueResponse(**result)

        except JiraError as e:
            raise ToolError(e.message) from e
        except Exception as e:
            raise ToolError(f"Failed to update Jira issue: {e}") from e

    @mcp.tool(
        name="jira_add_comment",
        description="Add a comment to a Jira issue. "
        "Use to add context, link to meeting notes, or provide updates.",
    )
    async def jira_add_comment(
        issue_key: Annotated[str, Field(description="Issue key (e.g., PROJ-123)")],
        body: Annotated[str, Field(description="Comment text")],
        ctx: Context,
    ) -> JiraAddCommentResponse:
        """Add a comment to a Jira issue."""
        await ctx.info(f"Adding comment to Jira issue: {issue_key}")
        try:
            jira_service = ctx.fastmcp.jira_service  # type: ignore[attr-defined]
            await ctx.debug(f"Comment length: {len(body)} chars")
            result = await jira_service.add_comment(
                issue_key=issue_key,
                body=body,
            )

            await ctx.info(f"Successfully added comment to: {issue_key}")
            return JiraAddCommentResponse(**result)

        except JiraError as e:
            raise ToolError(e.message) from e
        except Exception as e:
            raise ToolError(f"Failed to add comment: {e}") from e
