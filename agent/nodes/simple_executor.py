"""Simple executor node for single-step PM tasks."""

import logging

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from agent.core.config import AgentSettings
from agent.core.mcp_client import MCPClientWrapper
from agent.core.state import AgentState

logger = logging.getLogger(__name__)


SIMPLE_EXECUTOR_SYSTEM_PROMPT = """You are PM Copilot, an AI assistant specialized in project management tasks.

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
{project_context}
"""


def format_project_context(state: AgentState) -> str:
    """Format project context for system prompt.

    Args:
        state: Current agent state

    Returns:
        Formatted project context string
    """
    project_context = state["project_context"]

    if not project_context.project_key:
        return "- Project: Not specified (will use default or ask if needed for specific operations)"

    parts = [f"- Project: {project_context.project_key}"]

    if project_context.sprint_name:
        parts.append(f"- Sprint: {project_context.sprint_name}")
    else:
        parts.append("- Sprint: Not set")

    if project_context.team_members:
        parts.append(f"- Team: {', '.join(project_context.team_members)}")
    else:
        parts.append("- Team: Not specified")

    return "\n".join(parts)


async def simple_executor(
    state: AgentState,
    settings: AgentSettings,
    mcp_client: MCPClientWrapper,
    max_iterations: int = 10,
) -> Command:
    """Execute simple single-step requests using ReAct agent with Command return.

    This node processes the user's request using a ReAct agent with access to
    all MCP tools. It handles straightforward tasks that don't require multi-step
    planning.

    Args:
        state: Current agent state
        settings: Agent settings with LLM configuration
        mcp_client: MCP client with available tools
        max_iterations: Maximum number of ReAct iterations

    Returns:
        Command with updated messages, routing to end
    """
    messages = state.get("messages", [])
    logger.info("Executing simple ReAct agent")

    try:
        # Get tools from MCP client
        tools = await mcp_client.get_tools()
        logger.debug(f"Available tools: {[tool.name for tool in tools]}")

        # Create LLM
        llm = ChatOpenAI(
            model=settings.openai_base_model,
            temperature=0.0,
            openai_api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )

        # Build system prompt with project context
        project_context_str = format_project_context(state)
        system_prompt = SIMPLE_EXECUTOR_SYSTEM_PROMPT.format(
            project_context=project_context_str
        )

        # Prepend system message to conversation
        enhanced_messages = [HumanMessage(content=system_prompt)] + messages

        # Create and invoke ReAct agent
        agent = create_react_agent(
            llm,
            tools,
            state_schema=AgentState,
        )

        result = await agent.ainvoke(
            {"messages": enhanced_messages},
            {"recursion_limit": max_iterations},
        )

        logger.info("Simple ReAct agent completed successfully")

        # Return updated messages with Command
        return Command(
            update={"messages": result["messages"]},
            goto="__end__"
        )

    except Exception as e:
        logger.error(f"Error in simple_executor: {e}", exc_info=True)
        # Return error message to user
        from langchain_core.messages import AIMessage

        error_message = AIMessage(
            content=f"Произошла ошибка при выполнении запроса: {str(e)}\n\nПопробуйте переформулировать запрос или обратитесь к администратору."
        )
        return Command(
            update={"messages": [error_message]},
            goto="__end__"
        )
