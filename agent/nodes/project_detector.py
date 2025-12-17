"""Project detector node for extracting project_key from conversation."""

import logging

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.types import Command

from agent.core.config import AgentSettings
from agent.core.state import AgentState, ProjectContext
from agent.prompts import PROJECT_DETECTION_PROMPT

logger = logging.getLogger(__name__)


async def project_detector(state: AgentState, settings: AgentSettings) -> Command:
    """Extract project_key from conversation history using LLM.

    This node analyzes the conversation history to find mentions of Jira project keys,
    either explicitly ("работаем с проектом ALPHA") or implicitly ("issue ALPHA-123").

    Args:
        state: Current agent state
        settings: Agent settings with LLM configuration

    Returns:
        Command with updated project_context (if found), routing to task_router
    """
    project_context = state["project_context"]
    current_project_key = project_context.project_key

    # If already have project_key, skip detection
    if current_project_key:
        logger.info(
            f"Project key already set: {current_project_key}, skipping detection"
        )
        return Command(goto="task_router")

    messages = state["messages"]
    logger.info("Attempting to detect project_key from conversation history")

    try:
        # Build conversation history for prompt
        conversation_history = "\n".join(
            [
                f"{'User' if i % 2 == 0 else 'Assistant'}: {msg.content}"
                for i, msg in enumerate(messages)
            ]
        )

        # Use LLM to extract project_key
        llm = ChatOpenAI(
            model=settings.openai_base_model,
            temperature=0.0,
            openai_api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )

        prompt = PROJECT_DETECTION_PROMPT.format(
            conversation_history=conversation_history
        )
        response = await llm.ainvoke([HumanMessage(content=prompt)])

        detected_key = response.content.strip().upper()

        if detected_key != "UNKNOWN" and detected_key:
            logger.info(f"Project key detected: {detected_key}")

            # Update project_context with detected key
            updated_context = ProjectContext(
                project_key=detected_key,
                sprint_name=project_context.sprint_name,
                team_members=project_context.team_members,
            )

            return Command(
                update={"project_context": updated_context}, goto="task_router"
            )
        else:
            logger.info("No project key detected, continuing without it")
            return Command(goto="task_router")

    except Exception as e:
        logger.error(f"Error in project_detector: {e}", exc_info=True)
        # Continue to task_router even on error (it will handle missing project)
        logger.warning("Continuing to task_router despite detection error")
        return Command(goto="task_router")
