"""Entry point for PM Copilot A2A Agent."""

import uvicorn

from agent.core.config import AgentSettings

if __name__ == "__main__":
    settings = AgentSettings()

    uvicorn.run(
        "agent.a2a.server:app",
        host=settings.a2a_server_host,
        port=settings.a2a_server_port,
        reload=False,
    )
