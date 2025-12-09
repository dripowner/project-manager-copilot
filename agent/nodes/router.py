"""Router node for classifying user requests."""

import logging
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from agent.core.config import AgentSettings
from agent.core.state import AgentState
from agent.prompts.router import ROUTER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class RouteDecision(BaseModel):
    """Router decision output."""

    reasoning: str = Field(description="Brief explanation of the classification")
    mode: Literal["simple", "plan_execute"] = Field(
        description="Execution mode: 'simple' or 'plan_execute'"
    )


def create_router_prompt() -> ChatPromptTemplate:
    """Create router prompt template.

    Returns:
        ChatPromptTemplate for router
    """
    return ChatPromptTemplate.from_messages(
        [
            ("system", ROUTER_SYSTEM_PROMPT),
            ("user", "{input}"),
        ]
    )


async def router_node(state: AgentState, settings: AgentSettings) -> dict:
    """Classify user request into simple or plan_execute mode.

    This node analyzes the user's request and determines whether it
    can be handled with a simple ReAct agent or requires a complex
    plan-and-execute workflow.

    Args:
        state: Current agent state
        settings: Agent configuration

    Returns:
        Updated state with mode set to 'simple' or 'plan_execute'
    """
    messages = state.get("messages", [])

    if not messages:
        logger.warning("No messages in state, defaulting to simple mode")
        return {"mode": "simple"}

    # Get the last user message
    last_message = messages[-1]
    user_input = (
        last_message.content if hasattr(last_message, "content") else str(last_message)
    )

    logger.info(f"Routing request: {user_input[:100]}...")

    # Create LLM with structured output
    llm = ChatOpenAI(
        model=settings.openai_base_model,
        temperature=0.0,  # Deterministic for classification
        openai_api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

    structured_llm = llm.with_structured_output(RouteDecision)

    # Create and invoke chain
    prompt = create_router_prompt()
    chain = prompt | structured_llm

    try:
        decision = await chain.ainvoke({"input": user_input})

        logger.info(
            f"Router decision: {decision.mode} (reasoning: {decision.reasoning})"
        )

        return {"mode": decision.mode}

    except Exception as e:
        logger.error(f"Router failed: {e}, defaulting to simple mode")
        return {"mode": "simple"}
