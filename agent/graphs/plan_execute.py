"""Plan-Execute subgraph for PM Copilot Agent."""

import logging

from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, END

from agent.core.config import AgentSettings
from agent.core.state import AgentState
from agent.nodes.checker import route_checker_decision
from agent.nodes.executor import executor_node
from agent.nodes.planner import planner_node

logger = logging.getLogger(__name__)


def create_plan_execute_subgraph(tools: list, simple_agent, settings: AgentSettings):
    """Create plan-execute subgraph for complex multi-step workflows.

    This subgraph handles complex requests that require multiple steps:
    1. Planner: Generates execution plan
    2. Executor: Executes current step
    3. Checker: Validates progress and routes to next step or end

    Args:
        tools: List of available MCP tools
        simple_agent: ReAct agent for step execution
        settings: Agent configuration

    Returns:
        Compiled LangGraph subgraph
    """
    logger.info("Creating plan-execute subgraph")

    # Create subgraph
    workflow = StateGraph(AgentState)

    # Node wrappers with proper signatures
    async def planner_wrapper(state: AgentState) -> dict:
        return await planner_node(state, tools, settings)

    async def executor_wrapper(state: AgentState) -> dict:
        return await executor_node(state, simple_agent, settings)

    def checker_wrapper(state: AgentState) -> dict:
        # Checker returns routing decision
        return {}  # State updates happen in executor

    # Add nodes
    workflow.add_node("planner", planner_wrapper)
    workflow.add_node("executor", executor_wrapper)
    workflow.add_node("checker", checker_wrapper)

    # Add final summary node
    async def summarizer(state: AgentState) -> dict:
        """Summarize plan execution results."""
        plan = state.get("plan")
        if not plan:
            return {"messages": [AIMessage(content="No plan was executed.")]}

        # Build summary
        completed_steps = [s for s in plan.steps if s.status == "done"]
        failed_steps = [s for s in plan.steps if s.status == "failed"]

        summary_lines = [
            "**Plan Execution Complete**",
            "",
            f"**Goal:** {plan.goal}",
            f"**Reasoning:** {plan.reasoning}",
            "",
            f"**Steps Completed:** {len(completed_steps)}/{len(plan.steps)}",
        ]

        if failed_steps:
            summary_lines.append(f"**Failed Steps:** {len(failed_steps)}")
            summary_lines.append("")
            for step in failed_steps:
                summary_lines.append(f"✗ {step.description}")
                if step.error:
                    summary_lines.append(f"  Error: {step.error}")

        if completed_steps:
            summary_lines.append("")
            summary_lines.append("**Completed Steps:**")
            for step in completed_steps:
                summary_lines.append(f"✓ {step.description}")

        summary = "\n".join(summary_lines)

        logger.info(
            f"Plan execution summary: {len(completed_steps)} completed, {len(failed_steps)} failed"
        )

        return {"messages": [AIMessage(content=summary)]}

    workflow.add_node("summarizer", summarizer)

    # Set entry point
    workflow.set_entry_point("planner")

    # Connect planner to executor
    workflow.add_edge("planner", "executor")

    # Connect executor to checker
    workflow.add_edge("executor", "checker")

    # Conditional edge from checker
    workflow.add_conditional_edges(
        "checker",
        route_checker_decision,
        {
            "continue": "executor",  # Loop back to execute next step
            "end": "summarizer",  # All steps done, summarize
        },
    )

    # Summarizer goes to END
    workflow.add_edge("summarizer", END)

    # Compile subgraph
    subgraph = workflow.compile()

    logger.info("Plan-execute subgraph created successfully")
    return subgraph
