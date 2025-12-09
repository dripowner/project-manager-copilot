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
                Each config should specify 'url' and 'transport' for HTTP,
                or 'command' and 'args' for STDIO.

        Example:
            ```python
            # HTTP transport (production)
            config = {
                "pm-mcp-server": {
                    "url": "http://localhost:8000/mcp",
                    "transport": "http"
                }
            }
            client = MCPClientWrapper(config)
            tools = await client.get_tools()  # Stateless - creates ephemeral session
            ```

        Note:
            As of langchain-mcp-adapters 0.1.0+, MultiServerMCPClient is stateless.
            Each tool invocation via get_tools() creates an ephemeral session that
            automatically cleans up.

            DO NOT use as async context manager - it raises NotImplementedError.
            The wrapper no longer implements __aenter__/__aexit__ methods.

            For persistent sessions, use client.client.session("server_name").
        """
        self.server_config = server_config
        self.client = MultiServerMCPClient(server_config)
        self._tools = None
        logger.info(f"MCP client initialized with {len(self.server_config)} server(s)")

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
