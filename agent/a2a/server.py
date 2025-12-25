"""FastAPI server for A2A protocol."""

import logging
from contextlib import asynccontextmanager

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from fastapi import FastAPI

from agent.a2a.agent_card import get_agent_card
from agent.a2a.executor import PMCopilotExecutor
from agent.core.checkpointer import close_checkpointer
from agent.core.config import AgentSettings
from agent.core.mcp_client import MCPClientWrapper

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for A2A server.

    Handles setup and cleanup of AsyncPostgresSaver.
    Dependencies are initialized in create_a2a_app() before handler creation.

    Args:
        app: FastAPI application
    """
    logger.info("A2A server starting...")

    # Setup AsyncPostgresSaver tables (idempotent, safe to call on every startup)
    checkpointer = app.state.checkpointer
    await checkpointer.setup()
    logger.info("AsyncPostgresSaver tables initialized")

    logger.info("A2A server started")

    yield

    # Cleanup
    logger.info("Shutting down A2A server...")
    await close_checkpointer(checkpointer)
    logger.info("A2A server shutdown complete")


def create_a2a_app() -> FastAPI:
    """Create A2A FastAPI application.

    Returns:
        FastAPI application with A2A endpoints
    """
    settings = AgentSettings()

    logger.info("Creating A2A FastAPI application...")

    # Initialize dependencies BEFORE creating handler
    # (handler needs actual instances, not factories)

    # Initialize MCP client
    mcp_config = {
        "pm-mcp-server": {
            "url": settings.mcp_server_url,
            "transport": "http",
        }
    }
    mcp_client = MCPClientWrapper(mcp_config)
    logger.info(f"MCP client initialized for {settings.mcp_server_url}")

    # Initialize checkpointer with manual lifecycle management
    # NOTE: Can't use recommended 'async with' pattern in FastAPI startup phase
    # Cleanup is handled explicitly in lifespan shutdown via close_checkpointer()
    # Reference: LangGraph docs recommend context managers, but not applicable for long-running servers
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    checkpointer = AsyncPostgresSaver.from_conn_string(
        settings.agent_database_url,
        pool_size=5,
        max_overflow=10,
    )
    logger.info("AsyncPostgresSaver instance created (setup in lifespan)")

    # Initialize task store
    task_store = InMemoryTaskStore()
    logger.info("In-memory task store initialized")

    # Create executor with initialized dependencies
    executor = PMCopilotExecutor(
        mcp_client=mcp_client,
        checkpointer=checkpointer,
        settings=settings,
    )

    # Create request handler with executor and task store
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store,
    )

    # Create A2A app with handler instance (using Starlette like cloud.ru example)
    a2a_app = A2AStarletteApplication(
        agent_card=get_agent_card(settings),
        http_handler=handler,
    )

    # Build Starlette app
    starlette_app = a2a_app.build()

    # Wrap in FastAPI for lifespan support
    app = FastAPI(lifespan=lifespan)
    app.mount("/", starlette_app)

    # Store dependencies in app state for cleanup in lifespan
    app.state.mcp_client = mcp_client
    app.state.checkpointer = checkpointer
    app.state.task_store = task_store
    app.state.settings = settings

    logger.info("A2A FastAPI application created successfully")

    return app


# Create app instance for uvicorn
app = create_a2a_app()
