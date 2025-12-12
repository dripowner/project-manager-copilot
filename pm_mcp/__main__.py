"""Entry point for running the MCP server.

This module serves as the entry point for the PM MCP server,
running in HTTP transport mode.

Usage:
    python -m pm_mcp

Environment Variables:
    SERVER_HOST: HTTP server host (default: '0.0.0.0')
    SERVER_PORT: HTTP server port (default: 8000)
"""

import logging
import sys

import uvicorn

from pm_mcp.config import get_settings
from pm_mcp.server import create_http_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the MCP server in HTTP mode."""
    settings = get_settings()

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


if __name__ == "__main__":
    main()
