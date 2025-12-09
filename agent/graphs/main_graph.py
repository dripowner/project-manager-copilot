"""Main workflow graph for PM Copilot Agent."""

import logging

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import StateGraph, END

from agent.core.config import AgentSettings
from agent.core.mcp_client import MCPClientWrapper
from agent.core.state import AgentState
from agent.graphs.plan_execute import create_plan_execute_subgraph
from agent.nodes.router import router_node
from agent.nodes.simple_react import create_simple_react_node, simple_react_node

logger = logging.getLogger(__name__)


async def create_main_graph(
    mcp_client: MCPClientWrapper,
    settings: AgentSettings,
    checkpointer: BaseCheckpointSaver | None = None,
):
    """Create the main workflow graph for PM Copilot Agent.

    Phase 4: Full graph with router, simple ReAct, plan-execute, and checkpointing.
    Routes between simple ReAct execution and plan-execute workflows with persistent state.

    Args:
        mcp_client: Connected MCP client with available tools
        settings: Agent configuration settings
        checkpointer: Optional checkpointer for persistent state (PostgreSQL or in-memory)

    Returns:
        Compiled LangGraph workflow
    """
    logger.info("Creating main workflow graph with router and plan-execute")

    # Get tools from MCP client
    tools = await mcp_client.get_tools()
    logger.info(f"Available tools: {await mcp_client.list_tool_names()}")

    # Create Simple ReAct agent
    simple_agent = create_simple_react_node(tools, settings)

    # Create plan-execute subgraph
    plan_execute_graph = create_plan_execute_subgraph(tools, simple_agent, settings)

    # Create workflow graph
    workflow = StateGraph(AgentState)

    # Node wrappers
    async def router_wrapper(state: AgentState) -> dict:
        return await router_node(state, settings)

    async def simple_react_wrapper(state: AgentState) -> dict:
        return await simple_react_node(state, simple_agent, settings.max_iterations)

    async def plan_execute_wrapper(state: AgentState) -> dict:
        """Execute plan-execute subgraph."""
        logger.info("Plan-execute mode invoked")
        result = await plan_execute_graph.ainvoke(state)
        return result

    # Add nodes
    workflow.add_node("router", router_wrapper)
    workflow.add_node("simple_react", simple_react_wrapper)
    workflow.add_node("plan_execute", plan_execute_wrapper)

    # Set entry point (start at router)
    workflow.set_entry_point("router")

    # Conditional routing based on mode
    def route_by_mode(state: AgentState) -> str:
        """Route to simple_react or plan_execute based on mode."""
        mode = state.get("mode", "simple")
        logger.info(f"Routing to: {mode}")
        return mode

    workflow.add_conditional_edges(
        "router",
        route_by_mode,
        {
            "simple": "simple_react",
            "plan_execute": "plan_execute",
        },
    )

    # Both execution paths end the graph
    workflow.add_edge("simple_react", END)
    workflow.add_edge("plan_execute", END)

    # Compile with checkpointer
    if checkpointer:
        logger.info(f"Compiling graph with checkpointer: {type(checkpointer).__name__}")
    else:
        logger.info("Compiling graph without checkpointer (stateless mode)")

    graph = workflow.compile(checkpointer=checkpointer)

    logger.info("Main workflow graph created successfully")
    return graph
