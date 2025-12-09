"""Pydantic response models for PM Copilot Agent."""

from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    """Standard response from the agent."""

    message: str = Field(description="Human-readable response message")
    success: bool = Field(description="Whether the operation was successful")
    data: dict | None = Field(default=None, description="Additional response data")
    tool_calls: list[dict] = Field(
        default_factory=list, description="List of tool calls made"
    )


class ErrorResponse(BaseModel):
    """Error response from the agent."""

    error: str = Field(description="Error message")
    error_type: str = Field(description="Type of error")
    details: dict | None = Field(default=None, description="Additional error details")
