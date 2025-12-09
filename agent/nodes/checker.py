"""Checker node for PM Copilot Agent."""

import logging
from typing import Literal

from agent.core.state import AgentState

logger = logging.getLogger(__name__)


def checker_node(state: AgentState) -> dict[str, str | AgentState]:
    """Check plan progress and determine next action.

    This node validates the current step's execution status and decides whether to:
    - Continue to the next step
    - End the workflow (all steps completed)
    - Report failure (step failed with no recovery)

    Args:
        state: Current agent state with plan

    Returns:
        Dictionary with routing decision and updated state
    """
    plan = state.get("plan")
    if not plan:
        logger.error("Checker called without a plan")
        return {"next": "end"}

    current_step = plan.current_step

    logger.info(
        f"Checker: Validating step {plan.current_step_idx + 1}/{len(plan.steps)}"
    )

    # Check if current step failed
    if current_step and current_step.status == "failed":
        logger.warning(f"Step {plan.current_step_idx + 1} failed: {current_step.error}")
        # For now, we end on failure. Future: implement replanner
        return {"next": "end"}

    # Check if current step is done
    if current_step and current_step.status == "done":
        # Move to next step
        plan.current_step_idx += 1
        logger.info(f"Moving to step {plan.current_step_idx + 1}")

    # Check if all steps completed
    if plan.current_step_idx >= len(plan.steps):
        logger.info("All steps completed")
        return {"next": "end"}

    # Check if plan is complete (all steps marked done)
    if plan.is_complete:
        logger.info("Plan marked as complete")
        return {"next": "end"}

    # More steps to execute
    logger.info(f"Continuing to step {plan.current_step_idx + 1}")
    return {"next": "continue"}


def route_checker_decision(state: AgentState) -> Literal["continue", "end"]:
    """Route based on checker decision.

    This is a routing function for LangGraph conditional edges.

    Args:
        state: Current agent state

    Returns:
        Next node name: "continue" (executor) or "end"
    """
    plan = state.get("plan")
    if not plan:
        return "end"

    # Check if more steps remain
    if plan.current_step_idx < len(plan.steps):
        current_step = plan.current_step
        # Don't continue if current step failed
        if current_step and current_step.status == "failed":
            return "end"
        return "continue"

    return "end"
