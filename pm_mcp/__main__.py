"""Entry point for running the MCP server.

This module serves as the unified entry point for the PM MCP server,
supporting both HTTP and STDIO transports via environment configuration.

Usage:
    HTTP mode (default):
        python -m pm_mcp
        # or with explicit config:
        MCP_TRANSPORT=http python -m pm_mcp

    STDIO mode (for Claude Desktop / CLI tools):
        MCP_TRANSPORT=stdio python -m pm_mcp

Environment Variables:
    MCP_TRANSPORT: Transport mode ('http' or 'stdio', default: 'http')
    SERVER_HOST: HTTP server host (default: '0.0.0.0')
    SERVER_PORT: HTTP server port (default: 8000)
"""

import logging
import sys

import uvicorn

from pm_mcp.config import get_settings
from pm_mcp.server import create_http_app, run_stdio_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the MCP server based on configuration."""
    settings = get_settings()

    if settings.mcp_transport == "stdio":
        # STDIO mode
        logger.info("Starting PM MCP Server in STDIO mode")
        logger.info("Server will communicate via standard input/output")
        run_stdio_server()

    elif settings.mcp_transport == "http":
        # HTTP mode
        logger.info(
            f"Starting PM MCP Server in HTTP mode on {settings.server_host}:{settings.server_port}"
        )

        # Get ASGI app
        app = create_http_app()

        # Run with uvicorn
        uvicorn.run(
            app,
            host=settings.server_host,
            port=settings.server_port,
            log_level="info",
        )

    else:
        # Should never happen due to Literal type, but good to have
        logger.error(f"Invalid MCP_TRANSPORT: {settings.mcp_transport}")
        logger.error("Valid options: 'stdio', 'http'")
        sys.exit(1)


if __name__ == "__main__":
    main()
