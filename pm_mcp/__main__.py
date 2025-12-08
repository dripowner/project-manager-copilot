"""Entry point for running the MCP server."""

import logging
import sys

import uvicorn

from pm_mcp.config import get_settings
from pm_mcp.server import get_http_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the MCP server."""
    settings = get_settings()

    logger.info(
        f"Starting PM MCP Server on {settings.server_host}:{settings.server_port}"
    )

    # Get ASGI app
    app = get_http_app()

    # Run with uvicorn
    uvicorn.run(
        app,
        host=settings.server_host,
        port=settings.server_port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
