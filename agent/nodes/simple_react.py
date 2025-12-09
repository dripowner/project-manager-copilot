"""Simple ReAct agent node for PM Copilot."""

import logging

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from agent.core.config import AgentSettings
from agent.core.state import AgentState

logger = logging.getLogger(__name__)


SIMPLE_REACT_SYSTEM_PROMPT = """You are PM Copilot, an AI assistant specialized in project management tasks.

You have access to tools for managing Jira issues, Confluence pages, Google Calendar events,
and PM-specific operations like linking meetings to issues.

**Your capabilities:**
- Create, update, and list Jira issues
- Search and read Confluence documentation
- Manage calendar events
- Link meetings to Jira issues
- Generate project status reports

**Guidelines:**
- Use the available tools to accomplish user requests efficiently
- Always confirm what you're doing before executing actions
- Provide clear, concise responses
- If you're unsure, ask for clarification
- Format responses in a user-friendly way

**Current project context:**
- Project: {project_key}
- Sprint: {sprint_name}
- Team: {team_members}
"""


def create_simple_react_node(tools: list, settings: AgentSettings):
    """Create a Simple ReAct agent node.

    This creates a LangGraph ReAct agent that can handle straightforward
    requests using available MCP tools.

    Args:
        tools: List of LangChain tools from MCP client
        settings: Agent configuration settings

    Returns:
        Compiled LangGraph agent
    """
    logger.info(f"Creating Simple ReAct agent with {len(tools)} tools")

    llm = ChatOpenAI(
        model=settings.openai_base_model,
        temperature=0.0,
        openai_api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

    # Create ReAct agent with tools
    agent = create_react_agent(
        llm,
        tools,
        state_schema=AgentState,
    )

    logger.info("Simple ReAct agent created successfully")
    return agent


async def simple_react_node(state: AgentState, agent, max_iterations: int = 10) -> dict:
    """Execute the Simple ReAct agent node.

    This node processes the user's request using the ReAct agent
    and returns the response.

    Args:
        state: Current agent state
        agent: The compiled ReAct agent
        max_iterations: Maximum number of iterations

    Returns:
        Updated state with agent response
    """
    project_context = state.get("project_context")
    messages = state.get("messages", [])

    # Format system prompt with project context
    if project_context:
        system_prompt = SIMPLE_REACT_SYSTEM_PROMPT.format(
            project_key=project_context.project_key,
            sprint_name=project_context.sprint_name or "Not set",
            team_members=", ".join(project_context.team_members)
            if project_context.team_members
            else "Not specified",
        )
    else:
        system_prompt = """You are PM Copilot, an AI assistant specialized in project management tasks."""

    # Prepend system message to conversation
    enhanced_messages = [HumanMessage(content=system_prompt)] + messages

    # Invoke ReAct agent
    logger.info("Executing Simple ReAct agent")
    result = await agent.ainvoke(
        {"messages": enhanced_messages},
        {"recursion_limit": max_iterations},
    )

    logger.info("Simple ReAct agent completed")

    # Return updated messages
    return {"messages": result["messages"]}
