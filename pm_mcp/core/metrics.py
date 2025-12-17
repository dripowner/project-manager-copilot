"""Prometheus metrics for PM MCP Server."""

import logging
from contextlib import contextmanager

from prometheus_client import Counter, Histogram

from pm_mcp.config import get_settings

logger = logging.getLogger(__name__)


# Check if monitoring is enabled (default: True for production)
MONITORING_ENABLED = get_settings().enable_monitoring

if MONITORING_ENABLED:
    logger.info("Prometheus metrics enabled (ENABLE_MONITORING=true)")

    # Tool call tracking
    TOOL_CALLS = Counter(
        "tool_calls_total",
        "Total number of MCP tool calls",
        ["tool_name", "status"],  # status: success | error
    )

    # External API call tracking (Jira, Confluence, Calendar)
    API_CALLS = Counter(
        "api_calls_total",
        "External API calls to Atlassian/Google services",
        ["service", "endpoint", "status"],  # service: jira | confluence | calendar
    )

    # Tool execution duration
    TOOL_DURATION = Histogram(
        "tool_duration_seconds",
        "Tool execution duration in seconds",
        ["tool_name"],
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    )

    # Error tracking
    ERROR_COUNT = Counter(
        "errors_total",
        "Total errors by domain",
        ["error_type", "domain"],  # domain: jira | confluence | calendar | pm
    )
else:
    logger.info("Prometheus metrics disabled (ENABLE_MONITORING=false)")

    # Create no-op metrics that do nothing when monitoring is disabled
    class _NoOpMetric:
        """No-op metric that does nothing."""

        def labels(self, **kwargs):  # noqa: ARG002
            return self

        def inc(self, amount=1):  # noqa: ARG002
            pass

        def time(self):
            @contextmanager
            def _noop():
                yield

            return _noop()

    TOOL_CALLS = _NoOpMetric()
    API_CALLS = _NoOpMetric()
    TOOL_DURATION = _NoOpMetric()
    ERROR_COUNT = _NoOpMetric()
