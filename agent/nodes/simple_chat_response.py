"""Simple chat response node for conversational queries."""

import logging

from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.types import Command

from agent.core.config import AgentSettings
from agent.core.state import AgentState

logger = logging.getLogger(__name__)


SIMPLE_CHAT_SYSTEM_PROMPT = """Ты PM Copilot - AI ассистент для управления проектами.

Ты умеешь:
- Создавать и искать Jira issues
- Искать документацию в Confluence
- Управлять Calendar событиями
- Генерировать статус-репорты
- Связывать встречи с задачами

Отвечай дружелюбно и кратко. Если пользователь просит помощь с задачей - предложи конкретные действия.
"""


async def simple_chat_response(state: AgentState, settings: AgentSettings) -> Command:
    """Handle simple conversational queries without PM tools.

    This node responds to simple chat messages like greetings, thanks, and general
    questions. It does NOT have access to PM tools to keep responses fast and avoid
    unnecessary LLM calls.

    Args:
        state: Current agent state
        settings: Agent settings with LLM configuration

    Returns:
        Command with updated messages, routing to end
    """
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""

    logger.info(f"Handling simple chat: '{last_message[:50]}...'")

    try:
        # Simple conversational LLM (NO TOOLS!)
        llm = ChatOpenAI(
            model=settings.openai_base_model,
            temperature=0.7,  # Slightly higher for more natural conversation
            openai_api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )

        response = await llm.ainvoke([
            SystemMessage(content=SIMPLE_CHAT_SYSTEM_PROMPT),
            *messages
        ])

        logger.info("Simple chat response generated")

        return Command(
            update={"messages": [response]},
            goto="__end__"
        )

    except Exception as e:
        logger.error(f"Error in simple_chat_response: {e}", exc_info=True)
        # Fallback response on error
        fallback_message = AIMessage(content="Извините, произошла ошибка. Попробуйте еще раз.")
        return Command(
            update={"messages": [fallback_message]},
            goto="__end__"
        )
