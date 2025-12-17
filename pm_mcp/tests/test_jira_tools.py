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


# Tests for JQL escaping utility function
from pm_mcp.services.base import escape_query_value


class TestEscapeQueryValue:
    """Tests for escape_query_value function."""

    def test_escape_quotes(self) -> None:
        """Test escaping of double quotes."""
        value = 'Test "quoted" value'
        result = escape_query_value(value)
        assert result == '"Test \\"quoted\\" value"'

    def test_escape_backslash(self) -> None:
        """Test escaping of backslashes."""
        value = "Path\\to\\file"
        result = escape_query_value(value)
        assert result == '"Path\\\\to\\\\file"'

    def test_escape_backslash_and_quotes(self) -> None:
        """Test escaping both backslashes and quotes."""
        value = 'Test\\"quoted"'
        result = escape_query_value(value)
        # First backslash is escaped, then quote is escaped
        assert result == '"Test\\\\\\"quoted\\""'

    def test_special_jql_chars_wrapped(self) -> None:
        """Test that special JQL chars are handled by wrapping."""
        # These chars are handled by wrapping in quotes
        test_cases = [
            ("test + value", '"test + value"'),
            ("test && condition", '"test && condition"'),
            ("test || or", '"test || or"'),
            ("test ! not", '"test ! not"'),
            ("test ~ fuzzy", '"test ~ fuzzy"'),
            ("test * wildcard", '"test * wildcard"'),
            ("test ? single", '"test ? single"'),
            ("test : colon", '"test : colon"'),
        ]

        for input_val, expected in test_cases:
            result = escape_query_value(input_val)
            assert result == expected, f"Failed for: {input_val}"

    def test_empty_string_returns_empty(self) -> None:
        """Test that empty string returns empty."""
        assert escape_query_value("") == ""

    def test_normal_text(self) -> None:
        """Test that normal text is wrapped in quotes."""
        value = "normal text"
        result = escape_query_value(value)
        assert result == '"normal text"'

    def test_already_safe_value(self) -> None:
        """Test value without special chars."""
        value = "SimpleValue123"
        result = escape_query_value(value)
        assert result == '"SimpleValue123"'
