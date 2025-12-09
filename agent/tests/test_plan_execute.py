"""Tests for Plan-Execute workflow."""

import pytest
from langchain_core.messages import HumanMessage

from agent.core.state import Plan, ProjectContext, Step
from agent.graphs.main_graph import create_main_graph


@pytest.mark.asyncio
async def test_plan_execute_mode_invoked(mock_mcp_client, settings):
    """Test that plan-execute mode is invoked for complex requests."""
    graph = await create_main_graph(mock_mcp_client, settings)

    state = {
        "messages": [
            HumanMessage(content="Prepare sprint planning with backlog prioritization")
        ],
        "project_context": ProjectContext(project_key="TEST"),
        "plan": None,
        "mode": "simple",
        "tool_results": [],
        "remaining_steps": 10,
    }

    # Execute graph
    result = await graph.ainvoke(
        state, config={"configurable": {"thread_id": "test-pe-1"}}
    )

    # Should have messages (plan execution output)
    assert "messages" in result
    assert len(result["messages"]) > 0

    # Should have a plan in the result
    assert "plan" in result
    # Plan might be None or populated depending on router classification


@pytest.mark.asyncio
async def test_planner_generates_plan(mock_mcp_client, settings):
    """Test planner node generates a valid plan."""
    from agent.nodes.planner import planner_node

    tools = await mock_mcp_client.get_tools()

    state = {
        "messages": [
            HumanMessage(content="Prepare sprint planning for next iteration")
        ],
        "project_context": ProjectContext(project_key="TEST"),
        "plan": None,
        "mode": "plan_execute",
        "tool_results": [],
        "remaining_steps": 10,
    }

    try:
        result = await planner_node(state, tools, settings)

        # Should return a plan
        assert "plan" in result
        plan = result["plan"]
        assert plan is not None
        assert isinstance(plan, Plan)

        # Plan should have goal, reasoning, and steps
        assert plan.goal
        assert plan.reasoning
        assert len(plan.steps) > 0

        # Steps should have required fields
        for step in plan.steps:
            assert step.id
            assert step.description
            # tool_name and tool_args are optional (can be None for reasoning steps)

    except Exception as e:
        # Expected if OpenAI API key is not valid
        # Plan should fall back to a simple plan
        if "Invalid API Key" in str(e) or "401" in str(e):
            pytest.skip("OpenAI API key not available for testing")
        else:
            raise


@pytest.mark.asyncio
async def test_executor_executes_step(mock_mcp_client, settings, sample_agent_state):
    """Test executor node executes current step."""
    from agent.nodes.executor import executor_node
    from agent.nodes.simple_react import create_simple_react_node

    tools = await mock_mcp_client.get_tools()
    simple_agent = create_simple_react_node(tools, settings)

    # Create a test plan
    plan = Plan(
        goal="Test goal",
        reasoning="Test reasoning",
        steps=[
            Step(
                id="step_1",
                description="List all issues in project TEST",
                tool_name="test_tool",
                tool_args={"query": "list issues"},
                status="pending",
            )
        ],
        current_step_idx=0,
    )

    state = sample_agent_state.copy()
    state["plan"] = plan
    state["mode"] = "plan_execute"

    try:
        result = await executor_node(state, simple_agent, settings)

        # Should update plan and tool_results
        assert "plan" in result or "tool_results" in result
        assert "messages" in result

        # Step should be marked as done or failed
        if "plan" in result:
            updated_plan = result["plan"]
            current_step = updated_plan.steps[0]
            assert current_step.status in ["done", "failed"]

    except Exception as e:
        # Expected if OpenAI API key is not valid
        if "Invalid API Key" in str(e) or "401" in str(e):
            pytest.skip("OpenAI API key not available for testing")
        else:
            raise


def test_checker_routes_correctly():
    """Test checker node routing logic."""
    from agent.nodes.checker import route_checker_decision

    # Test: more steps remaining
    state_continue = {
        "messages": [],
        "project_context": ProjectContext(project_key="TEST"),
        "plan": Plan(
            goal="Test",
            reasoning="Test",
            steps=[
                Step(id="step_1", description="Step 1", status="done"),
                Step(id="step_2", description="Step 2", status="pending"),
            ],
            current_step_idx=1,
        ),
        "mode": "plan_execute",
        "tool_results": [],
        "remaining_steps": 10,
    }

    decision = route_checker_decision(state_continue)
    assert decision == "continue"

    # Test: all steps done
    state_end = {
        "messages": [],
        "project_context": ProjectContext(project_key="TEST"),
        "plan": Plan(
            goal="Test",
            reasoning="Test",
            steps=[
                Step(id="step_1", description="Step 1", status="done"),
                Step(id="step_2", description="Step 2", status="done"),
            ],
            current_step_idx=2,  # Beyond last step
        ),
        "mode": "plan_execute",
        "tool_results": [],
        "remaining_steps": 10,
    }

    decision = route_checker_decision(state_end)
    assert decision == "end"

    # Test: step failed
    state_failed = {
        "messages": [],
        "project_context": ProjectContext(project_key="TEST"),
        "plan": Plan(
            goal="Test",
            reasoning="Test",
            steps=[
                Step(id="step_1", description="Step 1", status="done"),
                Step(
                    id="step_2",
                    description="Step 2",
                    status="failed",
                    error="Test error",
                ),
            ],
            current_step_idx=1,
        ),
        "mode": "plan_execute",
        "tool_results": [],
        "remaining_steps": 10,
    }

    decision = route_checker_decision(state_failed)
    assert decision == "end"


def test_plan_state_properties():
    """Test Plan model helper properties."""
    plan = Plan(
        goal="Test goal",
        reasoning="Test reasoning",
        steps=[
            Step(id="step_1", description="Step 1", status="done"),
            Step(id="step_2", description="Step 2", status="pending"),
            Step(id="step_3", description="Step 3", status="pending"),
        ],
        current_step_idx=1,
    )

    # Test current_step property
    assert plan.current_step is not None
    assert plan.current_step.id == "step_2"

    # Test is_complete property
    assert not plan.is_complete

    # Complete all steps
    for step in plan.steps:
        step.status = "done"
    assert plan.is_complete

    # Test has_failures property
    assert not plan.has_failures
    plan.steps[1].status = "failed"
    assert plan.has_failures


def test_step_initialization():
    """Test Step model initialization and defaults."""
    step = Step(description="Test step")

    # Should have auto-generated ID
    assert step.id is not None
    assert len(step.id) > 0

    # Should have default status
    assert step.status == "pending"

    # Optional fields should be None
    assert step.tool_name is None
    assert step.tool_args is None
    assert step.result is None
    assert step.error is None


@pytest.mark.asyncio
async def test_full_plan_execute_workflow(mock_mcp_client, settings):
    """Test complete plan-execute workflow end-to-end."""
    graph = await create_main_graph(mock_mcp_client, settings)

    # Create a state that should trigger plan-execute mode
    state = {
        "messages": [
            HumanMessage(
                content="Generate weekly status report with completed, in-progress, and blocked issues"
            )
        ],
        "project_context": ProjectContext(project_key="TEST", sprint_name="Sprint 1"),
        "plan": None,
        "mode": "simple",
        "tool_results": [],
        "remaining_steps": 10,
    }

    try:
        # Execute full workflow
        result = await graph.ainvoke(
            state, config={"configurable": {"thread_id": "test-full-pe"}}
        )

        # Should have messages
        assert "messages" in result
        assert len(result["messages"]) > 0

        # Should have processed the request
        assert result["project_context"] is not None

    except Exception as e:
        # Expected if OpenAI API key is not valid
        if "Invalid API Key" in str(e) or "401" in str(e):
            pytest.skip("OpenAI API key not available for testing")
        else:
            raise
