"""Task router node for classifying PM tasks (simple vs plan_execute)."""

import logging

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.types import Command

from agent.core.config import AgentSettings
from agent.core.state import AgentState
from agent.prompts import TASK_CLASSIFICATION_PROMPT

logger = logging.getLogger(__name__)


async def task_router(state: AgentState, settings: AgentSettings) -> Command:
    """Route PM task to appropriate execution mode using Command pattern.

    This node analyzes the PM task and determines whether it can be handled
    with a simple ReAct agent (single-step) or requires a complex plan-and-execute
    workflow (multi-step).

    Args:
        state: Current agent state
        settings: Agent settings with LLM configuration

    Returns:
        Command with updated mode, routing to tool_validator
    """
    messages = state.get("messages", [])

    if not messages:
        logger.warning("No messages in state, defaulting to simple mode")
        return Command(update={"mode": "simple"}, goto="tool_validator")

    # Get the last user message
    last_message = messages[-1]
    user_input = (
        last_message.content if hasattr(last_message, "content") else str(last_message)
    )

    logger.info(f"Classifying PM task: {user_input[:100]}...")

    try:
        # Create LLM for classification
        llm = ChatOpenAI(
            model=settings.openai_base_model,
            temperature=0.0,  # Deterministic for classification
            openai_api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )

        # Invoke with classification prompt
        prompt = TASK_CLASSIFICATION_PROMPT.format(request=user_input)
        response = await llm.ainvoke([HumanMessage(content=prompt)])

        mode = response.content.strip().lower()

        # Validate mode
        if mode not in ["simple", "plan_execute"]:
            logger.warning(f"Invalid mode '{mode}', defaulting to simple")
            mode = "simple"

        logger.info(f"Task classification: {mode}")

        return Command(update={"mode": mode}, goto="tool_validator")

    except Exception as e:
        logger.error(
            f"Task router failed: {e}, defaulting to simple mode",
            exc_info=True,
            extra={
                "model": settings.openai_base_model,
                "base_url": settings.openai_base_url,
            },
        )
        return Command(update={"mode": "simple"}, goto="tool_validator")
