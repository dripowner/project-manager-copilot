"""Unified main workflow graph for PM Copilot Agent with Command routing."""

import logging

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import StateGraph, START

from agent.core.config import AgentSettings
from agent.core.mcp_client import MCPClientWrapper
from agent.core.state import AgentState

# Import all 8 nodes
from agent.nodes.ask_project_key import ask_project_key
from agent.nodes.conversation_router import conversation_router
from agent.nodes.plan_executor import plan_executor
from agent.nodes.project_detector import project_detector
from agent.nodes.simple_chat_response import simple_chat_response
from agent.nodes.simple_executor import simple_executor
from agent.nodes.task_router import task_router
from agent.nodes.tool_validator import tool_validator

logger = logging.getLogger(__name__)


async def create_main_graph(
    mcp_client: MCPClientWrapper,
    settings: AgentSettings,
    checkpointer: BaseCheckpointSaver | None = None,
):
    """Create the unified workflow graph for PM Copilot Agent.

    This is a single unified graph with Command-based routing (no conditional_edges).
    The graph uses 8 nodes with early classification to separate simple chat from PM work:

    Flow:
    START → conversation_router →
      [if chat] → simple_chat_response → END
      [if PM work] → project_detector → task_router → tool_validator →
        [if missing project_key] → ask_project_key → END
        [if valid] → simple_executor / plan_executor → END

    Args:
        mcp_client: Connected MCP client with available tools
        settings: Agent configuration settings
        checkpointer: Optional checkpointer for persistent state (default: in-memory)

    Returns:
        Compiled LangGraph workflow with Command routing
    """
    logger.info("Creating unified workflow graph with Command routing (8 nodes)")

    # Build graph
    workflow = StateGraph(AgentState)

    # Node wrappers to inject dependencies
    async def conversation_router_wrapper(state: AgentState):
        return await conversation_router(state, settings)

    async def simple_chat_response_wrapper(state: AgentState):
        return await simple_chat_response(state, settings)

    async def project_detector_wrapper(state: AgentState):
        return await project_detector(state, settings)

    async def task_router_wrapper(state: AgentState):
        return await task_router(state, settings)

    async def tool_validator_wrapper(state: AgentState):
        return await tool_validator(state, settings, mcp_client)

    async def ask_project_key_wrapper(state: AgentState):
        return await ask_project_key(state)

    async def simple_executor_wrapper(state: AgentState):
        return await simple_executor(state, settings, mcp_client)

    async def plan_executor_wrapper(state: AgentState):
        return await plan_executor(state, settings, mcp_client)

    # Add all 8 nodes
    workflow.add_node("conversation_router", conversation_router_wrapper)
    workflow.add_node("simple_chat_response", simple_chat_response_wrapper)
    workflow.add_node("project_detector", project_detector_wrapper)
    workflow.add_node("task_router", task_router_wrapper)
    workflow.add_node("tool_validator", tool_validator_wrapper)
    workflow.add_node("ask_project_key", ask_project_key_wrapper)
    workflow.add_node("simple_executor", simple_executor_wrapper)
    workflow.add_node("plan_executor", plan_executor_wrapper)

    # Entry point - early classification!
    workflow.add_edge(START, "conversation_router")

    logger.info("All 8 nodes added to graph")

    # All routing handled by Command returns - NO conditional_edges!
    logger.info("Graph routing: all via Command pattern (no conditional_edges)")

    # Compile with checkpointer
    if checkpointer:
        logger.info(f"Compiling graph with checkpointer: {type(checkpointer).__name__}")
    else:
        logger.info("Compiling graph without checkpointer (in-memory mode)")

    graph = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=[],  # No interrupts needed - ask_project_key handles user wait
    )

    logger.info("Unified workflow graph created successfully with Command routing")
    return graph
