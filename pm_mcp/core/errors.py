"""Error classes for MCP server."""

from typing import Any

from pydantic import BaseModel


class McpErrorResponse(BaseModel):
    """Standard error response model for MCP tools."""

    error: str
    message: str
    details: dict[str, Any] | None = None


class McpError(Exception):
    """Base exception for MCP server errors."""

    def __init__(
        self,
        error: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.error = error
        self.message = message
        self.details = details
        super().__init__(message)

    def to_response(self) -> McpErrorResponse:
        """Convert exception to error response model."""
        return McpErrorResponse(
            error=self.error,
            message=self.message,
            details=self.details,
        )


class JiraError(McpError):
    """Jira-specific error."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error="jira_error",
            message=message,
            details=details,
        )


class ConfluenceError(McpError):
    """Confluence-specific error."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error="confluence_error",
            message=message,
            details=details,
        )


class CalendarError(McpError):
    """Google Calendar-specific error."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error="calendar_error",
            message=message,
            details=details,
        )


class PmError(McpError):
    """PM layer (database) specific error."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error="pm_error",
            message=message,
            details=details,
        )
