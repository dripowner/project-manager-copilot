"""Conversation router node for early classification."""

import logging

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.types import Command

from agent.core.config import AgentSettings
from agent.core.state import AgentState
from agent.prompts import CONVERSATION_CLASSIFICATION_PROMPT

logger = logging.getLogger(__name__)


async def conversation_router(state: AgentState, settings: AgentSettings) -> Command:
    """Route between simple chat and PM work using early classification.

    This node performs early classification to separate simple conversational
    queries (greetings, small talk) from actual PM work that requires tools.

    Args:
        state: Current agent state
        settings: Agent settings with LLM configuration

    Returns:
        Command routing to either simple_chat_response or project_detector
    """
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""

    # Get last 5 messages for context (excluding current message)
    recent_messages = messages[-6:-1] if len(messages) > 1 else []
    history = (
        "\n".join(
            [
                f"{'User' if hasattr(msg, 'type') and msg.type == 'human' else 'Assistant'}: {msg.content}"
                for msg in recent_messages
            ]
        )
        if recent_messages
        else "(No previous context)"
    )

    logger.info(f"Classifying conversation: '{last_message[:50]}...'")

    try:
        # Use LLM to classify conversation
        llm = ChatOpenAI(
            model=settings.openai_base_model,
            temperature=0.0,
            openai_api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )

        prompt = CONVERSATION_CLASSIFICATION_PROMPT.format(
            history=history, message=last_message
        )
        response = await llm.ainvoke([HumanMessage(content=prompt)])

        category = response.content.strip().lower()
        logger.info(f"Classification result: {category}")

        if category == "chat":
            logger.info("Routing to simple_chat_response (no PM tools needed)")
            return Command(goto="simple_chat_response")
        else:
            logger.info("Routing to project_detector (PM work detected)")
            return Command(goto="project_detector")

    except Exception as e:
        logger.error(f"Error in conversation_router: {e}", exc_info=True)
        # Fallback to PM work on error (conservative approach)
        logger.warning("Falling back to project_detector due to classification error")
        return Command(goto="project_detector")
