"""Executor node for PM Copilot Agent."""

import json
import logging

from langchain_core.messages import AIMessage, HumanMessage

from agent.core.config import AgentSettings
from agent.core.state import AgentState

logger = logging.getLogger(__name__)


async def executor_node(state: AgentState, agent, settings: AgentSettings) -> dict:
    """Execute current step in the plan.

    Args:
        state: Current agent state with plan
        agent: ReAct agent for tool execution
        settings: Agent configuration

    Returns:
        Updated state with step results
    """
    plan = state.get("plan")
    if not plan:
        logger.error("Executor called without a plan")
        return {}

    current_step = plan.current_step
    if not current_step:
        logger.warning("No current step to execute")
        return {}

    logger.info(
        f"Executing step {plan.current_step_idx + 1}/{len(plan.steps)}: {current_step.description}"
    )

    # Mark step as running
    current_step.status = "running"

    try:
        # Build execution prompt for this step
        execution_prompt = _build_execution_prompt(current_step, state)

        # Execute using ReAct agent
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=execution_prompt)]},
            {"recursion_limit": settings.max_iterations},
        )

        # Extract result from agent messages
        result_messages = result.get("messages", [])
        if result_messages:
            last_message = result_messages[-1]
            if isinstance(last_message, AIMessage):
                result_content = last_message.content
            else:
                result_content = str(last_message)
        else:
            result_content = "Step executed (no output)"

        # Mark step as done and store result
        current_step.status = "done"
        current_step.result = {
            "output": result_content,
            "messages": [
                msg.dict() if hasattr(msg, "dict") else str(msg)
                for msg in result_messages[-3:]
            ],  # Keep last 3 messages
        }

        logger.info(f"Step {plan.current_step_idx + 1} completed successfully")

        # Add step result to tool_results history
        tool_results = state.get("tool_results", [])
        tool_results.append(
            {
                "step_id": current_step.id,
                "step_idx": plan.current_step_idx,
                "description": current_step.description,
                "status": "done",
                "result": result_content,
            }
        )

        return {
            "plan": plan,
            "tool_results": tool_results,
            "messages": [
                AIMessage(
                    content=f"✓ Step {plan.current_step_idx + 1} completed: {current_step.description}"
                )
            ],
        }

    except Exception as e:
        logger.error(f"Step {plan.current_step_idx + 1} failed: {e}")

        # Mark step as failed
        current_step.status = "failed"
        current_step.error = str(e)

        # Add failure to tool_results
        tool_results = state.get("tool_results", [])
        tool_results.append(
            {
                "step_id": current_step.id,
                "step_idx": plan.current_step_idx,
                "description": current_step.description,
                "status": "failed",
                "error": str(e),
            }
        )

        return {
            "plan": plan,
            "tool_results": tool_results,
            "messages": [
                AIMessage(
                    content=f"✗ Step {plan.current_step_idx + 1} failed: {str(e)}"
                )
            ],
        }


def _build_execution_prompt(step, state: AgentState) -> str:
    """Build execution prompt for current step.

    Args:
        step: Step to execute
        state: Current agent state

    Returns:
        Formatted prompt for agent execution
    """
    # Get project context
    project_context = state.get("project_context")
    context_str = ""
    if project_context:
        context_str = (
            f"\n**Project Context:**\n- Project: {project_context.project_key}"
        )
        if project_context.sprint_name:
            context_str += f"\n- Sprint: {project_context.sprint_name}"
        if project_context.team_members:
            context_str += f"\n- Team: {', '.join(project_context.team_members[:3])}"

    # Get previous step results
    tool_results = state.get("tool_results", [])
    previous_results = ""
    if tool_results:
        previous_results = "\n\n**Previous Step Results:**\n"
        for result in tool_results[-3:]:  # Show last 3 results
            status_icon = "✓" if result.get("status") == "done" else "✗"
            previous_results += f"{status_icon} Step {result.get('step_idx', 0) + 1}: {result.get('description', 'N/A')}\n"
            if result.get("result"):
                # Truncate long results
                result_str = str(result["result"])
                if len(result_str) > 500:
                    result_str = result_str[:500] + "... (truncated)"
                previous_results += f"  Result: {result_str}\n"

    # Build tool instruction
    tool_instruction = ""
    if step.tool_name and step.tool_args:
        tool_instruction = f"\n\n**Suggested Tool:**\nUse `{step.tool_name}` with arguments: {json.dumps(step.tool_args, indent=2)}"
    elif step.tool_name:
        tool_instruction = f"\n\n**Suggested Tool:**\nUse `{step.tool_name}` (determine appropriate arguments based on context)"

    # Combine into full prompt
    prompt = f"""**Current Step:**
{step.description}
{context_str}
{previous_results}
{tool_instruction}

**Instructions:**
Execute this step using the available tools. Provide a clear summary of what was accomplished and any key findings.
"""

    return prompt
