"""MCP client wrapper for PM Copilot Agent."""

import logging
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)


class MCPClientWrapper:
    """Wrapper around MultiServerMCPClient for easy integration with LangGraph.

    This wrapper manages the connection to MCP servers and provides
    convenient access to tools.
    """

    def __init__(self, server_config: dict[str, Any]):
        """Initialize MCP client with server configuration.

        Args:
            server_config: Dictionary mapping server names to their configurations.
                Each config should specify 'command', 'args', and 'transport'.

        Example:
            ```python
            config = {
                "pm-mcp-server": {
                    "command": "python",
                    "args": ["-m", "pm_mcp"],
                    "transport": "stdio"
                }
            }
            client = MCPClientWrapper(config)
            ```
        """
        self.server_config = server_config
        self.client = MultiServerMCPClient(server_config)
        self._tools = None

    async def __aenter__(self):
        """Enter async context manager - connect to MCP servers."""
        logger.info(f"Connecting to {len(self.server_config)} MCP server(s)...")
        await self.client.__aenter__()
        logger.info("MCP client connected successfully")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager - disconnect from MCP servers."""
        logger.info("Disconnecting from MCP servers...")
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
        logger.info("MCP client disconnected")

    async def get_tools(self) -> list:
        """Get all available tools from connected MCP servers.

        Returns:
            List of LangChain tool objects that can be used with agents.
        """
        if self._tools is None:
            self._tools = await self.client.get_tools()
            logger.info(f"Retrieved {len(self._tools)} tools from MCP servers")
            logger.debug(f"Available tools: {[t.name for t in self._tools]}")
        return self._tools

    async def get_tool_by_name(self, name: str):
        """Get a specific tool by name.

        Args:
            name: Name of the tool to retrieve.

        Returns:
            Tool object if found, None otherwise.
        """
        tools = await self.get_tools()
        for tool in tools:
            if tool.name == name:
                return tool
        logger.warning(f"Tool '{name}' not found")
        return None

    async def list_tool_names(self) -> list[str]:
        """Get list of all available tool names.

        Returns:
            List of tool names.
        """
        return [t.name for t in await self.get_tools()]
