"""Validation utilities for agent nodes."""

from agent.core.mcp_client import MCPClientWrapper

# Tools that require project_key to function
TOOLS_REQUIRING_PROJECT = {
    "jira_list_issues",
    "jira_create_issues_batch",
    "pm_link_meeting_issues",
    "pm_get_meeting_issues",
    "pm_get_project_snapshot",
}


async def get_available_tool_names(mcp_client: MCPClientWrapper) -> list[str]:
    """Get list of available MCP tool names.

    Args:
        mcp_client: Initialized MCP client wrapper

    Returns:
        List of tool names
    """
    tools = await mcp_client.get_tools()
    return [tool.name for tool in tools]


def check_tools_need_project(tool_names: set[str]) -> bool:
    """Check if any tools require project_key.

    Args:
        tool_names: Set of tool names to check

    Returns:
        True if any tool requires project_key, False otherwise
    """
    return bool(tool_names & TOOLS_REQUIRING_PROJECT)
