"""Prompt for tool prediction from user request."""

TOOL_PREDICTION_PROMPT = """Given this user request, predict which MCP tools will likely be called to fulfill it.

Available tools:
{tool_names}

User request:
{request}

Instructions:
- Analyze the user's intent carefully
- Return comma-separated list of tool names that will likely be needed
- If no tools needed (unlikely), return "none"
- Be conservative: it's better to predict a tool that won't be used than to miss one that's needed

Examples:
- "создай issue в ALPHA" → jira_create_issues_batch
- "покажи все задачи в проекте BETA" → jira_list_issues
- "найди документацию по API" → confluence_search_pages
- "какие встречи сегодня" → calendar_list_events
- "свяжи встречу с задачей ALPHA-123" → pm_link_meeting_issues
- "статус проекта GAMMA" → pm_get_project_snapshot

Return ONLY comma-separated tool names (or "none"):
"""
