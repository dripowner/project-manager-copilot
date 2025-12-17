"""State schemas for PM Copilot Agent."""

from typing import Annotated, Literal, TypedDict
from uuid import uuid4

from langgraph.graph import add_messages
from pydantic import BaseModel, Field


class Step(BaseModel):
    """A single step in an execution plan."""

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique step ID")
    description: str = Field(description="What needs to be done in this step")
    tool_name: str | None = Field(default=None, description="MCP tool to use")
    tool_args: dict | None = Field(default=None, description="Arguments for the tool")
    status: Literal["pending", "running", "done", "failed"] = Field(
        default="pending", description="Current step status"
    )
    result: dict | None = Field(default=None, description="Step execution result")
    error: str | None = Field(default=None, description="Error message if failed")


class Plan(BaseModel):
    """Multi-step execution plan for complex workflows."""

    goal: str = Field(description="The overall goal of this plan")
    reasoning: str = Field(description="Why this plan was chosen")
    steps: list[Step] = Field(
        default_factory=list, description="List of steps to execute"
    )
    current_step_idx: int = Field(
        default=0, description="Index of current step being executed"
    )

    @property
    def current_step(self) -> Step | None:
        """Get the current step being executed."""
        if 0 <= self.current_step_idx < len(self.steps):
            return self.steps[self.current_step_idx]
        return None

    @property
    def is_complete(self) -> bool:
        """Check if all steps are completed."""
        return all(step.status == "done" for step in self.steps)

    @property
    def has_failures(self) -> bool:
        """Check if any step has failed."""
        return any(step.status == "failed" for step in self.steps)


class ProjectContext(BaseModel):
    """Context about the current project being managed."""

    project_key: str | None = Field(
        default=None,
        description="Jira project key (e.g., 'PROJ'). Agent determines from context if not provided.",
    )
    sprint_name: str | None = Field(default=None, description="Current sprint name")
    team_members: list[str] = Field(
        default_factory=list, description="Team member names/emails"
    )


class AgentState(TypedDict):
    """State for PM Copilot Agent graph.

    This state is passed between nodes and tracks the conversation,
    project context, execution plan, and results.
    """

    messages: Annotated[
        list, add_messages
    ]  # Conversation history with add_messages reducer
    project_context: ProjectContext  # Current project context
    plan: Plan | None  # Execution plan (None for simple mode)
    mode: Literal["simple", "plan_execute"]  # Execution mode
    tool_results: list[dict]  # History of tool call results
    remaining_steps: (
        int  # Remaining steps for iteration control (required by create_react_agent)
    )
