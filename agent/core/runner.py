"""Core agent execution logic for A2A streaming."""

import logging
from typing import Optional

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver

from agent.core.config import AgentSettings
from agent.core.mcp_client import MCPClientWrapper
from agent.core.state import AgentState, ProjectContext
from agent.graphs.main_graph import create_main_graph

logger = logging.getLogger(__name__)


async def run_agent_streaming(
    query: str,
    settings: AgentSettings,
    project_context: ProjectContext,
    user_context: dict | None,
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
        user_context: User context for audit logging (NOT for authorization)
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
        "user_context": user_context,
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
