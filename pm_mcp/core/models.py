"""Shared Pydantic base models for MCP server."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BaseMcpModel(BaseModel):
    """Base model with common configuration for all MCP models."""

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="ignore",
    )


class TimestampedModel(BaseMcpModel):
    """Base model with timestamp fields."""

    created_at: datetime | None = None
    updated_at: datetime | None = None
