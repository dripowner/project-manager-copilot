"""Monitoring and metrics for PM Copilot Agent."""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ToolCallMetrics:
    """Metrics for tool call execution."""

    tool_name: str
    start_time: float
    end_time: float | None = None
    success: bool = False
    error: str | None = None
    args: dict = field(default_factory=dict)
    result: Any = None

    @property
    def duration_ms(self) -> float | None:
        """Calculate duration in milliseconds."""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return None


@dataclass
class AgentRunMetrics:
    """Metrics for agent run execution."""

    thread_id: str
    start_time: float
    end_time: float | None = None
    mode: str = "simple"
    messages_count: int = 0
    tool_calls: list[ToolCallMetrics] = field(default_factory=list)
    error: str | None = None

    @property
    def duration_ms(self) -> float | None:
        """Calculate duration in milliseconds."""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return None

    @property
    def success(self) -> bool:
        """Check if run was successful."""
        return self.error is None


class AgentMonitor:
    """Monitor agent execution and collect metrics."""

    def __init__(self):
        """Initialize monitor with empty metrics."""
        self.runs: list[AgentRunMetrics] = []
        self.tool_calls_by_name: dict[str, list[ToolCallMetrics]] = defaultdict(list)
        self.current_run: AgentRunMetrics | None = None

    def start_run(self, thread_id: str, mode: str = "simple") -> None:
        """Start monitoring a new agent run.

        Args:
            thread_id: Thread ID for the run
            mode: Execution mode (simple or plan_execute)
        """
        self.current_run = AgentRunMetrics(
            thread_id=thread_id, start_time=time.time(), mode=mode
        )
        logger.info(f"Started monitoring run: {thread_id} (mode: {mode})")

    def end_run(self, messages_count: int = 0, error: str | None = None) -> None:
        """End monitoring current agent run.

        Args:
            messages_count: Number of messages in conversation
            error: Error message if run failed
        """
        if not self.current_run:
            logger.warning("No current run to end")
            return

        self.current_run.end_time = time.time()
        self.current_run.messages_count = messages_count
        self.current_run.error = error

        # Add to history
        self.runs.append(self.current_run)

        # Log summary
        if self.current_run.success:
            logger.info(
                f"Run completed: {self.current_run.thread_id} "
                f"({self.current_run.duration_ms:.0f}ms, "
                f"{len(self.current_run.tool_calls)} tools called)"
            )
        else:
            logger.error(
                f"Run failed: {self.current_run.thread_id} "
                f"({self.current_run.duration_ms:.0f}ms) - {error}"
            )

        self.current_run = None

    def start_tool_call(self, tool_name: str, args: dict) -> ToolCallMetrics:
        """Start monitoring a tool call.

        Args:
            tool_name: Name of the tool being called
            args: Arguments passed to the tool

        Returns:
            Tool call metrics object
        """
        metrics = ToolCallMetrics(
            tool_name=tool_name, start_time=time.time(), args=args
        )

        if self.current_run:
            self.current_run.tool_calls.append(metrics)

        self.tool_calls_by_name[tool_name].append(metrics)

        logger.debug(f"Tool call started: {tool_name}")
        return metrics

    def end_tool_call(
        self,
        metrics: ToolCallMetrics,
        success: bool = True,
        result: Any = None,
        error: str | None = None,
    ) -> None:
        """End monitoring a tool call.

        Args:
            metrics: Tool call metrics object
            success: Whether tool call succeeded
            result: Tool call result
            error: Error message if failed
        """
        metrics.end_time = time.time()
        metrics.success = success
        metrics.result = result
        metrics.error = error

        if success:
            logger.debug(
                f"Tool call completed: {metrics.tool_name} ({metrics.duration_ms:.0f}ms)"
            )
        else:
            logger.warning(
                f"Tool call failed: {metrics.tool_name} ({metrics.duration_ms:.0f}ms) - {error}"
            )

    def get_summary(self) -> dict[str, Any]:
        """Get monitoring summary statistics.

        Returns:
            Dictionary with summary metrics
        """
        total_runs = len(self.runs)
        successful_runs = sum(1 for run in self.runs if run.success)
        failed_runs = total_runs - successful_runs

        total_tool_calls = sum(len(run.tool_calls) for run in self.runs)
        successful_tool_calls = sum(
            sum(1 for tc in run.tool_calls if tc.success) for run in self.runs
        )

        avg_run_duration = (
            sum(run.duration_ms or 0 for run in self.runs) / total_runs
            if total_runs > 0
            else 0
        )

        tool_usage = {
            name: {
                "count": len(calls),
                "success_rate": sum(1 for c in calls if c.success) / len(calls) * 100,
                "avg_duration_ms": sum(c.duration_ms or 0 for c in calls) / len(calls),
            }
            for name, calls in self.tool_calls_by_name.items()
        }

        return {
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "success_rate": successful_runs / total_runs * 100 if total_runs > 0 else 0,
            "avg_run_duration_ms": avg_run_duration,
            "total_tool_calls": total_tool_calls,
            "successful_tool_calls": successful_tool_calls,
            "tool_success_rate": (
                successful_tool_calls / total_tool_calls * 100
                if total_tool_calls > 0
                else 0
            ),
            "tool_usage": tool_usage,
        }

    def log_summary(self) -> None:
        """Log monitoring summary to logger."""
        summary = self.get_summary()

        logger.info("=" * 60)
        logger.info("Agent Monitoring Summary")
        logger.info("=" * 60)
        logger.info(f"Total Runs: {summary['total_runs']}")
        logger.info(
            f"Success Rate: {summary['success_rate']:.1f}% "
            f"({summary['successful_runs']}/{summary['total_runs']})"
        )
        logger.info(f"Average Duration: {summary['avg_run_duration_ms']:.0f}ms")
        logger.info(f"Total Tool Calls: {summary['total_tool_calls']}")
        logger.info(f"Tool Success Rate: {summary['tool_success_rate']:.1f}%")

        if summary["tool_usage"]:
            logger.info("\nTool Usage:")
            for tool_name, stats in sorted(summary["tool_usage"].items()):
                logger.info(
                    f"  {tool_name}: {stats['count']} calls, "
                    f"{stats['success_rate']:.1f}% success, "
                    f"{stats['avg_duration_ms']:.0f}ms avg"
                )
        logger.info("=" * 60)


# Global monitor instance
_global_monitor = AgentMonitor()


def get_monitor() -> AgentMonitor:
    """Get global monitor instance.

    Returns:
        Global agent monitor
    """
    return _global_monitor
