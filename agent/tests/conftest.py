"""Test fixtures for PM Copilot Agent tests."""

from unittest.mock import AsyncMock

import pytest
from langchain_core.tools import Tool

from agent.core.config import AgentSettings
from agent.core.mcp_client import MCPClientWrapper


@pytest.fixture
def settings():
    """Create test agent settings."""
    return AgentSettings(
        openai_base_model="gpt-4o-mini",
        max_iterations=5,
        openai_api_key="test-api-key",
        mcp_server_transport="stdio",
        mcp_server_command="python",
        mcp_server_args=["-m", "pm_mcp"],
    )


@pytest.fixture
def mock_tool():
    """Create a mock MCP tool."""

    def mock_func(query: str) -> str:
        return f"Mock result for: {query}"

    tool = Tool(
        name="test_tool",
        description="A test tool for unit tests",
        func=mock_func,
    )
    return tool


@pytest.fixture
async def mock_mcp_client(mock_tool):
    """Create a mock MCP client with test tools."""
    client = AsyncMock(spec=MCPClientWrapper)
    client.get_tools.return_value = [mock_tool]
    client.list_tool_names.return_value = ["test_tool"]
    client.get_tool_by_name.return_value = mock_tool
    return client


@pytest.fixture
def sample_project_context():
    """Create sample project context for tests."""
    from agent.core.state import ProjectContext

    return ProjectContext(
        project_key="TEST",
        sprint_name="Sprint 1",
        team_members=["alice@example.com", "bob@example.com"],
    )


@pytest.fixture
def sample_agent_state(sample_project_context):
    """Create sample agent state for tests."""
    from langchain_core.messages import HumanMessage

    return {
        "messages": [HumanMessage(content="Test query")],
        "project_context": sample_project_context,
        "plan": None,
        "mode": "simple",
        "tool_results": [],
        "remaining_steps": 10,
    }
