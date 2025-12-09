"""Tests for Simple ReAct agent node."""

import pytest
from langchain_core.messages import HumanMessage

from agent.graphs.main_graph import create_main_graph


@pytest.mark.asyncio
async def test_create_main_graph(mock_mcp_client, settings):
    """Test creating the main workflow graph."""
    graph = await create_main_graph(mock_mcp_client, settings)
    assert graph is not None
    assert mock_mcp_client.get_tools.called


@pytest.mark.asyncio
async def test_simple_react_execution(mock_mcp_client, settings, sample_agent_state):
    """Test executing the Simple ReAct agent with a query."""
    graph = await create_main_graph(mock_mcp_client, settings)

    # Execute graph with sample state
    result = await graph.ainvoke(
        sample_agent_state, config={"configurable": {"thread_id": "test-1"}}
    )

    # Verify result structure
    assert "messages" in result
    assert len(result["messages"]) > 0
    assert result["project_context"] is not None
    assert result["mode"] == "simple"


@pytest.mark.asyncio
async def test_agent_state_update(mock_mcp_client, settings):
    """Test that agent properly updates state with new messages."""
    graph = await create_main_graph(mock_mcp_client, settings)

    from agent.core.state import ProjectContext

    initial_state = {
        "messages": [HumanMessage(content="Hello agent")],
        "project_context": ProjectContext(project_key="TEST"),
        "plan": None,
        "mode": "simple",
        "tool_results": [],
        "remaining_steps": 10,
    }

    result = await graph.ainvoke(
        initial_state, config={"configurable": {"thread_id": "test-2"}}
    )

    # Check that messages were added
    assert len(result["messages"]) >= len(initial_state["messages"])


@pytest.mark.asyncio
async def test_graph_with_empty_tools(settings):
    """Test graph creation with no tools available."""
    from unittest.mock import AsyncMock
    from agent.core.mcp_client import MCPClientWrapper

    empty_client = AsyncMock(spec=MCPClientWrapper)
    empty_client.get_tools.return_value = []
    empty_client.list_tool_names.return_value = []

    graph = await create_main_graph(empty_client, settings)
    assert graph is not None


def test_project_context_creation(sample_project_context):
    """Test ProjectContext model creation."""
    assert sample_project_context.project_key == "TEST"
    assert sample_project_context.sprint_name == "Sprint 1"
    assert len(sample_project_context.team_members) == 2


def test_agent_state_structure(sample_agent_state):
    """Test AgentState structure and typing."""
    assert "messages" in sample_agent_state
    assert "project_context" in sample_agent_state
    assert "plan" in sample_agent_state
    assert "mode" in sample_agent_state
    assert "tool_results" in sample_agent_state
    assert "remaining_steps" in sample_agent_state

    assert sample_agent_state["mode"] == "simple"
    assert sample_agent_state["plan"] is None
    assert len(sample_agent_state["tool_results"]) == 0
    assert sample_agent_state["remaining_steps"] == 10
