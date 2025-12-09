"""Planner node for PM Copilot Agent."""

import logging

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from agent.core.config import AgentSettings
from agent.core.state import AgentState, Plan
from agent.prompts.planner import PLANNER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


async def planner_node(state: AgentState, tools: list, settings: AgentSettings) -> dict:
    """Generate execution plan for complex multi-step workflows.

    Args:
        state: Current agent state with messages and context
        tools: List of available MCP tools
        settings: Agent configuration

    Returns:
        Updated state with generated plan
    """
    logger.info("Planner node: Generating execution plan")

    # Get user's goal from last message
    last_message = state["messages"][-1]
    if isinstance(last_message, HumanMessage):
        goal = last_message.content
    else:
        goal = str(last_message.content)

    # Format tool information for prompt
    tool_descriptions = []
    for tool in tools:
        tool_info = f"- **{tool.name}**: {tool.description}"
        tool_descriptions.append(tool_info)

    tools_str = (
        "\n".join(tool_descriptions) if tool_descriptions else "No tools available"
    )

    # Create prompt with system message and user goal
    planner_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", PLANNER_SYSTEM_PROMPT),
            ("user", "Goal: {goal}\n\nPlease create a detailed execution plan."),
        ]
    )

    # Use LLM with structured output
    llm = ChatOpenAI(
        model=settings.openai_base_model,
        temperature=0.0,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

    # Get structured output as Plan model
    structured_llm = llm.with_structured_output(Plan)

    # Create chain
    chain = planner_prompt | structured_llm

    try:
        # Generate plan
        plan: Plan = await chain.ainvoke({"goal": goal, "tools": tools_str})

        logger.info(f"Plan generated: {len(plan.steps)} steps")
        logger.debug(f"Plan: {plan.model_dump_json(indent=2)}")

        # Reset current step index
        plan.current_step_idx = 0

        # Return updated state with plan
        return {"plan": plan}

    except Exception as e:
        logger.error(f"Failed to generate plan: {e}")
        # Fallback: create simple single-step plan
        from agent.core.state import Step

        fallback_plan = Plan(
            goal=goal,
            reasoning="Fallback plan due to planner error",
            steps=[
                Step(
                    id="step_1",
                    description=f"Execute request: {goal}",
                    tool_name=None,
                    tool_args=None,
                )
            ],
        )

        logger.warning("Using fallback single-step plan")
        return {"plan": fallback_plan}
