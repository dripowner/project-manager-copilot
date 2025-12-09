"""Core agent execution logic extracted from CLI."""

import logging
from typing import Optional

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver

from agent.core.config import AgentSettings
from agent.core.mcp_client import MCPClientWrapper
from agent.core.state import AgentState, ProjectContext
from agent.graphs.main_graph import create_main_graph

logger = logging.getLogger(__name__)


async def run_agent(
    query: str,
    settings: AgentSettings,
    project_key: Optional[str] = None,
    sprint_name: Optional[str] = None,
    checkpointer: Optional[BaseCheckpointSaver] = None,
    thread_id: str = "cli-session",
) -> str:
    """Run the agent with a query.

    Args:
        query: User query to process
        settings: Agent settings
        project_key: Optional Jira project key
        sprint_name: Optional sprint name
        checkpointer: Optional checkpointer for persistent state
        thread_id: Thread ID for conversation persistence

    Returns:
        Agent response text
    """
    # Configure MCP server connection based on transport type
    if settings.mcp_server_transport == "http":
        # HTTP mode: connect to external MCP server (production deployment)
        mcp_server_config = {
            "pm-mcp-server": {
                "url": settings.mcp_server_url,
                "transport": "http",
            }
        }
    else:
        # STDIO mode: launch MCP server as subprocess (local development)
        mcp_server_config = {
            "pm-mcp-server": {
                "command": settings.mcp_server_command,
                "args": settings.mcp_server_args,
                "transport": "stdio",
            }
        }

    # Initialize MCP client and agent
    # Note: MultiServerMCPClient is stateless - cleanup happens automatically
    mcp_client = MCPClientWrapper(mcp_server_config)
    graph = await create_main_graph(mcp_client, settings, checkpointer)

    # Prepare project context (fail-fast if project_key missing)
    resolved_project_key = project_key or settings.default_project_key
    if not resolved_project_key:
        raise ValueError(
            "project_key is required. Provide via parameter or set DEFAULT_PROJECT_KEY env var."
        )

    project_context = ProjectContext(
        project_key=resolved_project_key,
        sprint_name=sprint_name or settings.default_sprint_name,
        team_members=[],
    )

    # Prepare initial state
    initial_state = {
        "messages": [HumanMessage(content=query)],
        "project_context": project_context,
        "plan": None,
        "mode": "simple",
        "tool_results": [],
        "remaining_steps": settings.max_iterations,
    }

    # Run agent
    logger.info(f"Executing agent (thread: {thread_id})...")
    result = await graph.ainvoke(
        initial_state, config={"configurable": {"thread_id": thread_id}}
    )

    # Extract final message
    final_message = result["messages"][-1]
    return final_message.content


async def run_agent_streaming(
    query: str,
    settings: AgentSettings,
    project_context: ProjectContext,
    mcp_client: MCPClientWrapper,
    checkpointer: Optional[BaseCheckpointSaver] = None,
    thread_id: str = "a2a-session",
):
    """Run agent with streaming support for A2A.

    Yields LangGraph events instead of returning final result.

    Args:
        query: User query to process
        settings: Agent settings
        project_context: Project context information
        mcp_client: Initialized MCP client wrapper
        checkpointer: Optional checkpointer for persistent state
        thread_id: Thread ID for conversation persistence

    Yields:
        LangGraph events
    """
    graph = await create_main_graph(mcp_client, settings, checkpointer)

    # Prepare initial state
    initial_state: AgentState = {
        "messages": [HumanMessage(content=query)],
        "project_context": project_context,
        "plan": None,
        "mode": "simple",
        "tool_results": [],
        "remaining_steps": settings.max_iterations,
    }

    # Stream events
    logger.info(f"Streaming agent execution (thread: {thread_id})...")
    async for event in graph.astream_events(
        initial_state,
        config={"configurable": {"thread_id": thread_id}},
        version="v2",
    ):
        yield event
