"""PM Copilot Executor for A2A protocol."""

import logging
from typing import Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState
from a2a.utils.message import new_agent_text_message
from a2a.utils.task import new_task
from langgraph.checkpoint.base import BaseCheckpointSaver

from agent.a2a.converters import (
    extract_message_content,
    extract_project_context,
)
from agent.core.config import AgentSettings
from agent.core.mcp_client import MCPClientWrapper
from agent.core.runner import run_agent_streaming

logger = logging.getLogger(__name__)


class PMCopilotExecutor(AgentExecutor):
    """A2A executor for PM Copilot Agent."""

    def __init__(
        self,
        mcp_client: MCPClientWrapper,
        checkpointer: BaseCheckpointSaver | None,
        settings: AgentSettings,
    ):
        """Initialize PMCopilotExecutor.

        Args:
            mcp_client: MCP client wrapper for tool access
            checkpointer: Checkpointer for state persistence (None for stateless)
            settings: Agent settings
        """
        self.mcp_client = mcp_client
        self.checkpointer = checkpointer
        self.settings = settings

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ):
        """Execute agent for A2A request.

        Args:
            context: A2A RequestContext
            event_queue: A2A EventQueue for streaming updates
        """
        try:
            # 1. Convert A2A message to LangChain
            a2a_msg = context.message
            query = extract_message_content(a2a_msg)
            project_context = extract_project_context(a2a_msg, self.settings)

            logger.info(
                f"Executing PM Copilot for task {context.task_id}, "
                f"context: {context.context_id}"
            )

            # Create task first (following cloud.ru example)
            task = context.current_task
            if not task:
                task = new_task(context.message)
                await event_queue.enqueue_event(task)
                logger.info(f"Created task {task.id}")

            # Create TaskUpdater for streaming updates
            updater = TaskUpdater(event_queue, task.id, task.context_id)

            # Send initial working status (streaming support)
            await updater.update_status(
                TaskState.working,
                new_agent_text_message(
                    "Processing your request...", task.context_id, task.id
                ),
            )
            logger.info("Sent initial working status")

            # Track final message content
            final_content = None

            # 2. Call run_agent_streaming()
            async for event in run_agent_streaming(
                query=query,
                settings=self.settings,
                project_context=project_context,
                mcp_client=self.mcp_client,
                checkpointer=self.checkpointer,
                thread_id=context.context_id,
            ):
                # Track final output from agent
                if event.get("event") == "on_chain_end":
                    logger.info("Received on_chain_end event")
                    output = event.get("data", {}).get("output", {})

                    if isinstance(output, dict) and "messages" in output:
                        messages = output.get("messages", [])
                        logger.info(f"Found {len(messages)} messages in output")
                        if messages and hasattr(messages[-1], "content"):
                            final_content = messages[-1].content
                            logger.info(f"Captured final content: {len(final_content)} chars")
                    else:
                        logger.info(f"Output type: {type(output)}, has messages key: {'messages' in output if isinstance(output, dict) else False}")

                # 3. Filter and convert LangGraph events (pass updater for heartbeats)
                await self._handle_event(event, updater, context)

            # 4. Send final message (task and updater already created at start)
            if final_content:
                logger.info(f"Sending final completed status ({len(final_content)} chars)")
                await updater.update_status(
                    TaskState.completed,
                    new_agent_text_message(
                        final_content, task.context_id, task.id
                    ),
                )
                logger.info("Final message sent successfully")
            else:
                logger.warning(f"No final content for task {context.task_id}")
                # Send failure status if no content
                await updater.update_status(
                    TaskState.failed,
                    new_agent_text_message(
                        "No response generated", task.context_id, task.id
                    ),
                )

            logger.info(f"Task {context.task_id} completed successfully")

        except Exception:
            logger.exception(f"Agent execution failed for task {context.task_id}")
            # Note: Error handling is managed by A2A SDK
            # We just need to raise the exception
            raise

    async def _handle_event(
        self, event: dict[str, Any], updater: TaskUpdater, context: Any
    ):
        """Convert LangGraph event to A2A event.

        Handles streaming tokens, tool events, and final results.
        Non-critical errors are logged but don't stop execution.

        Note: Final message is sent by execute() after event loop completes
        to avoid race condition with event_queue closure.

        Args:
            event: LangGraph event dict
            updater: A2A TaskUpdater for sending status updates
            context: A2A RequestContext
        """
        event_type = event.get("event")
        event_name = event.get("name", "")
        event_tags = event.get("tags", [])

        try:
            # Note: We do NOT stream individual LLM tokens to avoid overwhelming EventQueue
            # A2A SDK expects only meaningful updates, not every token

            # Send heartbeat on chain/node start to keep connection alive
            if event_type == "on_chain_start":
                # Filter out verbose chain events, keep only meaningful nodes
                node_names = ["conversation_router", "project_detector", "task_router",
                             "tool_validator", "simple_executor", "plan_executor"]
                if any(node in event_name for node in node_names):
                    logger.debug(f"Node started: {event_name}")
                    try:
                        await updater.update_status(
                            TaskState.working,
                            new_agent_text_message(
                                "Processing...", context.context_id, context.task_id
                            ),
                        )
                    except Exception:
                        # Queue might be closed, ignore for non-critical status
                        pass

            # Update status on tool calls
            elif event_type == "on_tool_start":
                tool_name = event.get("name", "unknown_tool")
                logger.debug(f"Tool started: {tool_name}")
                try:
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(
                            f"Using tool: {tool_name}", context.context_id, context.task_id
                        ),
                    )
                except Exception:
                    # Queue might be closed, ignore for non-critical status
                    pass

            elif event_type == "on_tool_end":
                tool_name = event.get("name", "unknown_tool")
                logger.debug(f"Tool completed: {tool_name}")

            # Note: Final message is now handled by execute() to guarantee delivery
            # before event_queue is closed by A2A SDK

        except Exception as e:
            # Log with full context for debugging
            logger.error(
                f"Error handling event {event_type}: {e}",
                exc_info=True,
                extra={
                    "event_type": event_type,
                    "task_id": context.task_id,
                },
            )

            # Non-critical events: log and continue
            logger.debug(f"Non-critical event {event_type} failed, continuing")

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        """Cancel running task.

        TODO: Full cancellation requires LangGraph graph interruption support.
        Currently marks task as cancelled but doesn't stop execution.

        Args:
            context: A2A RequestContext
            event_queue: A2A EventQueue
        """
        task_id = context.task_id or "unknown"
        logger.warning(
            f"Task cancellation requested for {task_id}. "
            "Full cancellation support not yet implemented."
        )

        try:
            status_event = TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=context.context_id,
                status=TaskStatus(
                    state="cancelled",
                    message="Cancellation requested (implementation pending)",
                ),
                final=True,
            )
            await event_queue.enqueue_event(status_event)
        except Exception as e:
            logger.error(f"Error during cancellation: {e}", exc_info=True)
