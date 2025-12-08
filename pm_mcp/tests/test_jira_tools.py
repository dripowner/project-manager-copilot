"""Tests for Jira tools."""

import pytest
from fastmcp import Client

from pm_mcp.tests.mocks.mock_services import MockJiraService


@pytest.mark.asyncio
async def test_jira_list_issues(
    mcp_client: Client,
    mock_jira_service: MockJiraService,
) -> None:
    """Test listing Jira issues."""
    result = await mcp_client.call_tool(
        "jira_list_issues",
        {"project_key": "PROJ"},
    )

    assert result is not None
    mock_jira_service.list_issues.assert_called_once()


@pytest.mark.asyncio
async def test_jira_list_issues_with_filters(
    mcp_client: Client,
    mock_jira_service: MockJiraService,
) -> None:
    """Test listing Jira issues with filters."""
    result = await mcp_client.call_tool(
        "jira_list_issues",
        {
            "project_key": "PROJ",
            "status_category": "In Progress",
            "assignee": "alice@example.com",
            "labels": ["backend", "urgent"],
            "max_results": 20,
        },
    )

    assert result is not None
    mock_jira_service.list_issues.assert_called_once()


@pytest.mark.asyncio
async def test_jira_create_issues_batch(
    mcp_client: Client,
    mock_jira_service: MockJiraService,
) -> None:
    """Test batch creating Jira issues."""
    result = await mcp_client.call_tool(
        "jira_create_issues_batch",
        {
            "project_key": "PROJ",
            "issues": [
                {"summary": "Task 1", "description": "First task"},
                {"summary": "Task 2", "assignee": "alice"},
                {"summary": "Task 3", "labels": ["backend"]},
            ],
        },
    )

    assert result is not None
    mock_jira_service.create_issues_batch.assert_called_once()


@pytest.mark.asyncio
async def test_jira_update_issue(
    mcp_client: Client,
    mock_jira_service: MockJiraService,
) -> None:
    """Test updating a Jira issue."""
    result = await mcp_client.call_tool(
        "jira_update_issue",
        {
            "issue_key": "PROJ-1",
            "summary": "Updated summary",
            "status": "Done",
        },
    )

    assert result is not None
    mock_jira_service.update_issue.assert_called_once()


@pytest.mark.asyncio
async def test_jira_add_comment(
    mcp_client: Client,
    mock_jira_service: MockJiraService,
) -> None:
    """Test adding a comment to a Jira issue."""
    result = await mcp_client.call_tool(
        "jira_add_comment",
        {
            "issue_key": "PROJ-1",
            "body": "This task was discussed in the sprint planning meeting.",
        },
    )

    assert result is not None
    mock_jira_service.add_comment.assert_called_once()
