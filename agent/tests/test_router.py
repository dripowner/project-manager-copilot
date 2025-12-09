"""Tests for Router node."""

import pytest
from langchain_core.messages import HumanMessage

from agent.core.state import ProjectContext
from agent.nodes.router import router_node


@pytest.mark.asyncio
async def test_router_simple_request(settings):
    """Test router classifies simple requests correctly."""
    state = {
        "messages": [HumanMessage(content="Create a Jira issue for bug fix")],
        "project_context": ProjectContext(project_key="TEST"),
        "plan": None,
        "mode": "simple",
        "tool_results": [],
        "remaining_steps": 10,
    }

    result = await router_node(state, settings)

    assert "mode" in result
    assert result["mode"] == "simple"


@pytest.mark.asyncio
async def test_router_complex_request(settings):
    """Test router classifies complex requests correctly."""
    state = {
        "messages": [
            HumanMessage(
                content="Prepare sprint planning with backlog prioritization and team assignment"
            )
        ],
        "project_context": ProjectContext(project_key="TEST"),
        "plan": None,
        "mode": "simple",
        "tool_results": [],
        "remaining_steps": 10,
    }

    result = await router_node(state, settings)

    assert "mode" in result
    assert result["mode"] == "plan_execute"


@pytest.mark.asyncio
async def test_router_empty_messages(settings):
    """Test router handles empty messages gracefully."""
    state = {
        "messages": [],
        "project_context": ProjectContext(project_key="TEST"),
        "plan": None,
        "mode": "simple",
        "tool_results": [],
        "remaining_steps": 10,
    }

    result = await router_node(state, settings)

    assert "mode" in result
    # Should default to simple
    assert result["mode"] == "simple"


@pytest.mark.asyncio
async def test_router_list_request(settings):
    """Test router classifies list/query requests as simple."""
    state = {
        "messages": [HumanMessage(content="List all issues assigned to me")],
        "project_context": ProjectContext(project_key="TEST"),
        "plan": None,
        "mode": "simple",
        "tool_results": [],
        "remaining_steps": 10,
    }

    result = await router_node(state, settings)

    assert result["mode"] == "simple"


@pytest.mark.asyncio
async def test_router_analysis_request(settings):
    """Test router classifies analysis requests as plan_execute."""
    state = {
        "messages": [
            HumanMessage(content="Analyze project risks and suggest mitigation plan")
        ],
        "project_context": ProjectContext(project_key="TEST"),
        "plan": None,
        "mode": "simple",
        "tool_results": [],
        "remaining_steps": 10,
    }

    result = await router_node(state, settings)

    assert result["mode"] == "plan_execute"
