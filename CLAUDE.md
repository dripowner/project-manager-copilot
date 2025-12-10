# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PM MCP Server — an MCP (Model Context Protocol) server for project management integration. Provides tools for:
- **Jira**: Create/list/update issues, add comments
- **Confluence**: Search pages, read content
- **Google Calendar**: List meetings and events
- **PM Layer**: Link meetings to Jira issues, track action items (Google Calendar + Jira Labels storage)

Built with FastMCP 2.13+, uses streamable HTTP transport via Starlette/uvicorn.

## Development Commands

```bash
# Install all dependencies (dev + mcp-server)
uv sync --all-groups

# Run server locally (requires .env with valid credentials)
uv run python -m pm_mcp

# Run tests
uv run pytest

# Run single test file
uv run pytest pm_mcp/tests/test_jira_tools.py

# Run specific test
uv run pytest pm_mcp/tests/test_jira_tools.py::test_jira_list_issues_success -v

# Lint
uv run ruff check pm_mcp/
uv run ruff format pm_mcp/
```

## Docker

```bash
# Start full stack (mcp-server + agent-a2a)
docker compose up -d

# Rebuild after code changes
docker compose up -d --build mcp-server
docker compose up -d --build agent-a2a
```

## A2A Agent Server

PM Copilot is available via A2A (Agent-to-Agent) protocol.

### Running Locally

```bash
# Start A2A server (requires running MCP server)
uv run python -m agent
```

Server starts at http://localhost:8001

### A2A Endpoints

- `POST /rpc` - JSON-RPC endpoint for A2A protocol
- `GET /.well-known/agent-card.json` - Agent Card for discovery
- `GET /health` - Health check

### Agent Capabilities

1. **Sprint Planning** - Sprint planning and backlog management
2. **Status Reporting** - Generate project status reports
3. **Meeting Coordination** - Meeting and action items management
4. **Issue Lifecycle** - Complete Jira issue lifecycle management
5. **Team Coordination** - Team workload coordination
6. **Knowledge Search** - Confluence knowledge base search

### Testing Agent Card

```bash
curl http://localhost:8001/.well-known/agent-card.json
```

## Architecture

### Service Layer Pattern

Services are attached to the FastMCP instance and accessed via `ctx.fastmcp` in tool handlers:

```python
# In server.py
mcp.jira_service = JiraService(settings)

# In tools
jira_service = ctx.fastmcp.jira_service
```

### PM Layer Storage

PM Layer uses **Google Calendar extendedProperties.private** + **Jira Labels** for bidirectional data storage:

- **Meeting → Issues**: Calendar event's `extendedProperties.private` stores issue_keys, confluence_page_id, project_key as JSON
- **Issue → Meetings**: Jira issues get `gcal:{event_id}` labels for reverse lookup
- No external database required
- Automatic cleanup when events are deleted
- Size limit: ~8KB per event (validated before storage)

### Adding New Tools

1. Create models in `pm_mcp/tools/<domain>/models.py` (Pydantic response models)
2. Implement service in `pm_mcp/services/<domain>_service.py` (extends `BaseService`)
3. Register tools in `pm_mcp/tools/<domain>/tools.py` using `@mcp.tool()` decorator
4. Attach service to mcp instance in `server.py`
5. Add mock service in `pm_mcp/tests/mocks/mock_services.py`
6. Write tests using `mcp_client` fixture

### Tool Implementation Pattern

```python
@mcp.tool(name="domain_action", description="...")
async def domain_action(
    required_param: Annotated[str, Field(description="...")],
    ctx: Context,
    optional_param: Annotated[str | None, Field(description="...")] = None,
) -> ResponseModel:
    try:
        service = ctx.fastmcp.domain_service
        result = await service.do_action(required_param, optional_param)
        return ResponseModel(**result)
    except DomainError as e:
        raise ToolError(e.message) from e
```

### Testing Pattern

Tests use FastMCP's `Client` with mock services. Mock services return predefined data or raise errors based on input:

```python
async def test_tool_success(mcp_client: Client, mock_service: MockService):
    mock_service.set_response([{"key": "value"}])
    result = await mcp_client.call_tool("tool_name", {"param": "value"})
    assert result[0].text contains expected data
```

## Key Directories

- `pm_mcp/services/` — Business logic (Jira, Confluence, Calendar, PM APIs)
- `pm_mcp/tools/` — MCP tool definitions (grouped by domain)
- `pm_mcp/core/` — Error classes, shared models

## Configuration

Environment variables loaded via pydantic-settings. Copy `.env.example` to `.env` and fill in credentials. Test env vars are set in `pyproject.toml` under `[tool.pytest.ini_options]`.
