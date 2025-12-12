"""Base service class with common functionality."""

import asyncio
import logging
from abc import ABC
from functools import wraps
from typing import Any, Callable, ParamSpec, TypeVar

from pm_mcp.config import Settings, get_settings
from pm_mcp.core.metrics import API_CALLS

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def escape_query_value(value: str) -> str:
    """Escape special characters for JQL/CQL queries.

    Prevents injection attacks by escaping backslashes, double quotes,
    and single quotes in user-provided values.
    """
    if not value:
        return value
    special_chars = ["\\", '"', "'"]
    result = value
    for char in special_chars:
        result = result.replace(char, f"\\{char}")
    return result


def run_in_thread(func: Callable[P, T]) -> Callable[P, T]:
    """Decorator to run synchronous function in thread pool."""

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return await asyncio.to_thread(func, *args, **kwargs)

    return wrapper  # type: ignore[return-value]


class BaseService(ABC):
    """Abstract base service with common functionality."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.logger = logging.getLogger(self.__class__.__name__)

    def _log_error(
        self, operation: str, error: Exception, extra_context: dict[str, Any] | None = None
    ) -> None:
        """Log error with context."""
        if extra_context:
            self.logger.error(
                f"{operation} failed: {error}",
                extra={"context": extra_context},
            )
        else:
            self.logger.error(f"{operation} failed: {error}")

    def _log_info(self, message: str, **kwargs: Any) -> None:
        """Log info with context."""
        extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
        self.logger.info(f"{message} {extra}".strip())

    def _track_api_call(self, endpoint: str, status: str = "success") -> None:
        """Track API call metric.

        Args:
            endpoint: API endpoint called (e.g., "search", "issues")
            status: Call status (success | error)
        """
        service_name = self.__class__.__name__.replace("Service", "").lower()
        API_CALLS.labels(service=service_name, endpoint=endpoint, status=status).inc()
