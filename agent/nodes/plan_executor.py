"""Plan executor node for multi-step workflows with self-loop."""

import logging

from langchain_core.messages import AIMessage
from langgraph.types import Command

from agent.core.config import AgentSettings
from agent.core.mcp_client import MCPClientWrapper
from agent.core.state import AgentState

logger = logging.getLogger(__name__)


async def plan_executor(
    state: AgentState,
    settings: AgentSettings,
    mcp_client: MCPClientWrapper,
) -> Command:
    """Execute plan-execute workflow with self-loop using Command.

    This node handles multi-step workflows by combining planning, execution,
    and checking into a single self-looping node. It progresses through three phases:

    Phase 1 (Planning): Create execution plan if none exists
    Phase 2 (Execution): Execute steps one by one
    Phase 3 (Completion): Summarize results and end

    Args:
        state: Current agent state
        settings: Agent settings with LLM configuration
        mcp_client: MCP client with available tools

    Returns:
        Command routing to self (plan_executor) or end
    """
    plan = state.get("plan")
    remaining_steps = state.get("remaining_steps", 10)

    # Phase 1: Planning (if no plan exists)
    if not plan:
        logger.info("Phase 1: Creating execution plan")
        try:
            # Import planner node functionality
            from agent.nodes.planner import planner_node

            tools = await mcp_client.get_tools()
            planner_result = await planner_node(state, tools, settings)

            new_plan = planner_result.get("plan")
            if not new_plan:
                # Planning failed
                error_msg = AIMessage(
                    content="Не удалось создать план выполнения. Попробуйте переформулировать запрос."
                )
                return Command(update={"messages": [error_msg]}, goto="__end__")

            logger.info(f"Plan created with {len(new_plan.steps)} steps")

            # Move to Phase 2 (Execution)
            return Command(
                update={
                    "plan": new_plan,
                    "remaining_steps": remaining_steps - 1,
                },
                goto="plan_executor",  # Self-loop to Phase 2
            )

        except Exception as e:
            logger.error(f"Error in planning phase: {e}", exc_info=True)
            error_msg = AIMessage(content=f"Ошибка при создании плана: {str(e)}")
            return Command(update={"messages": [error_msg]}, goto="__end__")

    # Phase 2: Execution (if plan exists but not finished)
    if plan.current_step_idx < len(plan.steps):
        current_step = plan.steps[plan.current_step_idx]
        logger.info(
            f"Phase 2: Executing step {plan.current_step_idx + 1}/{len(plan.steps)}: {current_step.description}"
        )

        try:
            # Import executor node functionality
            from agent.nodes.executor import executor_node

            # Create simple agent for execution
            from agent.nodes.simple_executor import simple_executor

            tools = await mcp_client.get_tools()

            # Execute current step (executor updates plan.current_step_idx)
            executor_result = await executor_node(state, simple_executor, settings)

            updated_plan = executor_result.get("plan", plan)
            updated_messages = executor_result.get("messages", [])

            # Check if step failed critically
            if current_step.status == "failed":
                logger.error(
                    f"Step {plan.current_step_idx + 1} failed: {current_step.error}"
                )

                # For now, continue to next step unless it's the last step
                if plan.current_step_idx >= len(plan.steps) - 1:
                    # Last step failed, stop execution
                    failure_msg = AIMessage(
                        content=f"План прерван: ошибка на последнем шаге '{current_step.description}'\n\nОшибка: {current_step.error}"
                    )
                    return Command(
                        update={
                            "plan": updated_plan,
                            "messages": updated_messages + [failure_msg],
                        },
                        goto="__end__",
                    )

            # Check if we've exceeded max iterations
            if remaining_steps <= 1:
                logger.warning("Max iterations reached, stopping execution")
                timeout_msg = AIMessage(
                    content="Достигнуто максимальное количество итераций. План выполнен частично."
                )
                return Command(
                    update={
                        "plan": updated_plan,
                        "messages": updated_messages + [timeout_msg],
                    },
                    goto="__end__",
                )

            # Continue to next step
            logger.info("Continuing to next step")
            return Command(
                update={
                    "plan": updated_plan,
                    "messages": updated_messages,
                    "remaining_steps": remaining_steps - 1,
                },
                goto="plan_executor",  # Self-loop to next step
            )

        except Exception as e:
            logger.error(f"Error in execution phase: {e}", exc_info=True)
            error_msg = AIMessage(content=f"Ошибка при выполнении шага: {str(e)}")
            return Command(update={"messages": [error_msg]}, goto="__end__")

    # Phase 3: Completion (all steps finished)
    logger.info("Phase 3: Plan execution completed, generating summary")

    completed_steps = [s for s in plan.steps if s.status == "done"]
    failed_steps = [s for s in plan.steps if s.status == "failed"]

    summary_lines = [
        "**План выполнен**",
        "",
        f"**Цель:** {plan.goal}",
        f"**Обоснование:** {plan.reasoning}",
        "",
        f"**Выполнено шагов:** {len(completed_steps)}/{len(plan.steps)}",
    ]

    if failed_steps:
        summary_lines.append(f"**Ошибок:** {len(failed_steps)}")
        summary_lines.append("")
        for step in failed_steps:
            summary_lines.append(f"✗ {step.description}")
            if step.error:
                summary_lines.append(f"  Ошибка: {step.error}")

    if completed_steps:
        summary_lines.append("")
        summary_lines.append("**Выполненные шаги:**")
        for step in completed_steps:
            summary_lines.append(f"✓ {step.description}")

    summary = "\n".join(summary_lines)

    logger.info(
        f"Plan execution summary: {len(completed_steps)} completed, {len(failed_steps)} failed"
    )

    final_message = AIMessage(content=summary)

    return Command(update={"messages": [final_message]}, goto="__end__")
