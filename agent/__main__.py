"""Entry point for PM Copilot A2A Agent."""

import logging
import sys

import uvicorn

from agent.core.config import AgentSettings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%d.%m.%Y %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)

if __name__ == "__main__":
    settings = AgentSettings()

    uvicorn.run(
        "agent.a2a.server:app",
        host=settings.a2a_server_host,
        port=settings.a2a_server_port,
        reload=False,
    )
