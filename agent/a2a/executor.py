"""PM Copilot Executor for A2A protocol."""

import logging
from typing import Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from langgraph.checkpoint.base import BaseCheckpointSaver

from agent.a2a.converters import extract_project_context, langchain_to_a2a_message
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
            project_context = extract_project_context(a2a_msg, self.settings)

            logger.info(
                f"Executing PM Copilot for task {context.task.task_id}, "
                f"context: {context.context_id}"
            )

            # 2. Call run_agent_streaming()
            async for event in run_agent_streaming(
                query=a2a_msg.content,
                settings=self.settings,
                project_context=project_context,
                mcp_client=self.mcp_client,
                checkpointer=self.checkpointer,
                thread_id=context.context_id,
            ):
                # 3. Filter and convert LangGraph events
                await self._handle_event(event, event_queue, context)

            # 4. Mark task as completed
            logger.info(f"Task {context.task.task_id} completed successfully")

            # Note: Actual task state management is handled by A2A SDK
            # The final message has already been sent via event_queue

        except Exception:
            logger.exception(f"Agent execution failed for task {context.task.task_id}")
            # Note: Error handling is managed by A2A SDK
            # We just need to raise the exception
            raise

    async def _handle_event(self, event: dict[str, Any], event_queue: Any, context: Any):
        """Convert LangGraph event to A2A event.

        Handles streaming tokens, tool events, and final results.
        Non-critical errors are logged but don't stop execution.

        Args:
            event: LangGraph event dict
            event_queue: A2A EventQueue
            context: A2A RequestContext
        """
        event_type = event.get("event")

        try:
            # Stream chat model tokens
            if event_type == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    # Send partial message for streaming
                    await event_queue.put_message(
                        {
                            "role": "assistant",
                            "content": chunk.content,
                            "partial": True,
                        }
                    )

            # Update status on tool calls
            elif event_type == "on_tool_start":
                tool_name = event.get("name", "unknown_tool")
                logger.debug(f"Tool started: {tool_name}")
                await event_queue.put_task_status(
                    context.task.task_id,
                    status="working",
                    message=f"Using tool: {tool_name}",
                )

            elif event_type == "on_tool_end":
                tool_name = event.get("name", "unknown_tool")
                logger.debug(f"Tool completed: {tool_name}")

            # Final result
            elif event_type == "on_chain_end":
                output = event.get("data", {}).get("output", {})
                messages = output.get("messages", [])
                if messages:
                    final_msg = messages[-1]
                    # Send final complete message
                    msg_dict = langchain_to_a2a_message(final_msg)
                    await event_queue.put_message(
                        {
                            **msg_dict,
                            "partial": False,
                        }
                    )

        except Exception as e:
            # Log with full context for debugging
            logger.error(
                f"Error handling event {event_type}: {e}",
                exc_info=True,
                extra={
                    "event_type": event_type,
                    "task_id": context.task.task_id if context.task else None,
                },
            )

            # Critical events (final message) must succeed
            if event_type == "on_chain_end":
                logger.error("Critical event failed - re-raising")
                raise

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
        task_id = context.task.task_id if context.task else "unknown"
        logger.warning(
            f"Task cancellation requested for {task_id}. "
            "Full cancellation support not yet implemented."
        )

        try:
            await event_queue.put_task_status(
                task_id,
                status="cancelled",
                message="Cancellation requested (implementation pending)",
            )
        except Exception as e:
            logger.error(f"Error during cancellation: {e}", exc_info=True)
