"""Constants for PM MCP Server."""

# MCP Server Instructions
SERVER_INSTRUCTIONS = """
PM MCP Server - Project Management integration server.

This server provides tools for:
- Google Calendar: List meetings and events
- Confluence: Search pages, read content, create meeting notes
- Jira: Create/list/update issues, add comments
- PM Layer: Link meetings to issues, track action items, get project snapshots

Use these tools to:
1. Find meetings in calendar (calendar_list_events)
2. Search and read meeting protocols in Confluence (confluence_search_pages, confluence_get_page_content)
3. Extract action items and create Jira issues (jira_create_issues_batch)
4. Link issues to meetings for traceability (pm_link_meeting_issues)
5. Check status of action items (pm_get_meeting_issues)
6. Get project health overview (pm_get_project_snapshot)
"""
