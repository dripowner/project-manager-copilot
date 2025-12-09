"""FastAPI server for A2A protocol."""

import logging
from contextlib import asynccontextmanager

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.tasks import DatabaseTaskStore
from fastapi import FastAPI

from agent.a2a.agent_card import get_agent_card
from agent.a2a.executor import PMCopilotExecutor
from agent.core.checkpointer import close_checkpointer, create_checkpointer
from agent.core.config import AgentSettings
from agent.core.database import close_database_engine, create_database_engine
from agent.core.mcp_client import MCPClientWrapper

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for A2A server.

    Handles initialization and cleanup of database engine, MCP client,
    and checkpointer.

    Args:
        app: FastAPI application
    """
    settings = AgentSettings()
    logger.info("Initializing A2A server...")

    # Initialize database engine FIRST (required by DatabaseTaskStore)
    db_engine = await create_database_engine(settings)

    # Initialize MCP client
    mcp_config = {
        "pm-mcp-server": {
            "url": settings.mcp_server_url,
            "transport": "http",
        }
    }
    mcp_client = MCPClientWrapper(mcp_config)
    logger.info(f"MCP client initialized for {settings.mcp_server_url}")

    # Initialize checkpointer
    checkpointer = await create_checkpointer(settings)
    logger.info(f"Checkpointer initialized: {type(checkpointer).__name__}")

    # Store in app state
    app.state.db_engine = db_engine
    app.state.mcp_client = mcp_client
    app.state.checkpointer = checkpointer
    app.state.settings = settings

    logger.info("A2A server initialized successfully")

    yield

    # Cleanup (order matters: checkpointer first, then engine)
    logger.info("Shutting down A2A server...")
    await close_checkpointer(checkpointer)
    await close_database_engine(db_engine)
    logger.info("A2A server shutdown complete")


def create_a2a_app() -> FastAPI:
    """Create A2A FastAPI application.

    Returns:
        FastAPI application with A2A endpoints
    """
    settings = AgentSettings()

    logger.info("Creating A2A FastAPI application...")

    # Factory that gets task store from app.state.db_engine
    def get_task_store(app: FastAPI) -> DatabaseTaskStore:
        """Create DatabaseTaskStore with engine from lifespan.

        The engine is initialized in lifespan() and stored in app.state.
        """
        return DatabaseTaskStore(
            engine=app.state.db_engine,
            create_table=True,
        )

    # Create executor factory
    def executor_factory(app: FastAPI) -> PMCopilotExecutor:
        """Create PMCopilotExecutor with dependencies from app state."""
        return PMCopilotExecutor(
            mcp_client=app.state.mcp_client,
            checkpointer=app.state.checkpointer,
            settings=app.state.settings,
        )

    # Create request handler factory
    def handler_factory(app: FastAPI) -> DefaultRequestHandler:
        """Create DefaultRequestHandler with executor and task store."""
        return DefaultRequestHandler(
            agent_executor=executor_factory(app),
            task_store=get_task_store(app),
        )

    # Create A2A app
    a2a_app = A2AFastAPIApplication(
        agent_card=get_agent_card(settings),
        http_handler=handler_factory,
    )

    # Build FastAPI app with lifespan (standard FastAPI pattern)
    app = a2a_app.build(lifespan=lifespan)

    logger.info("A2A FastAPI application created")

    return app


# Create app instance for uvicorn
app = create_a2a_app()
