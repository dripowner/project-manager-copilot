"""Tool validator node for checking prerequisites before execution."""

import logging

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.types import Command

from agent.core.config import AgentSettings
from agent.core.mcp_client import MCPClientWrapper
from agent.core.state import AgentState
from agent.prompts import TOOL_PREDICTION_PROMPT
from agent.utils.validators import TOOLS_REQUIRING_PROJECT, get_available_tool_names

logger = logging.getLogger(__name__)


async def tool_validator(
    state: AgentState,
    settings: AgentSettings,
    mcp_client: MCPClientWrapper,
) -> Command:
    """Validate prerequisites before tool execution.

    This node predicts which tools will be needed for the user's request
    and checks if they require project_key. If project_key is missing when
    needed, it routes to ask_project_key.

    Args:
        state: Current agent state
        settings: Agent settings with LLM configuration
        mcp_client: MCP client for getting available tools

    Returns:
        Command routing to ask_project_key, simple_executor, or plan_executor
    """
    mode = state.get("mode", "simple")
    project_key = state["project_context"].project_key
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""

    logger.info(f"Validating prerequisites for mode: {mode}")

    try:
        # Get available tools from MCP
        available_tools = await get_available_tool_names(mcp_client)
        logger.debug(f"Available tools: {available_tools}")

        # Predict which tools will be needed
        llm = ChatOpenAI(
            model=settings.openai_base_model,
            temperature=0.0,
            openai_api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )

        prompt = TOOL_PREDICTION_PROMPT.format(
            tool_names=", ".join(available_tools),
            request=last_message
        )

        response = await llm.ainvoke([HumanMessage(content=prompt)])
        predicted_tools_str = response.content.strip()

        logger.info(f"Predicted tools: {predicted_tools_str}")

        # Parse predicted tools
        if predicted_tools_str.lower() == "none":
            predicted_tools = set()
        else:
            predicted_tools = {
                tool.strip()
                for tool in predicted_tools_str.split(",")
                if tool.strip()
            }

        # Check if any predicted tool requires project_key
        needs_project = bool(predicted_tools & TOOLS_REQUIRING_PROJECT)

        logger.info(f"Tools requiring project: {predicted_tools & TOOLS_REQUIRING_PROJECT}")
        logger.info(f"Current project_key: {project_key}")

        if needs_project and not project_key:
            # Missing required project_key
            logger.warning("Project key required but missing, routing to ask_project_key")
            return Command(goto="ask_project_key")

        # All prerequisites met, proceed to execution
        if mode == "simple":
            logger.info("Routing to simple_executor")
            return Command(goto="simple_executor")
        else:
            logger.info("Routing to plan_executor")
            return Command(goto="plan_executor")

    except Exception as e:
        logger.error(f"Error in tool_validator: {e}", exc_info=True)
        # Conservative fallback: if error, proceed with execution
        # (tools will fail gracefully if project_key actually needed)
        logger.warning(f"Proceeding to {mode}_executor despite validation error")
        if mode == "simple":
            return Command(goto="simple_executor")
        else:
            return Command(goto="plan_executor")
