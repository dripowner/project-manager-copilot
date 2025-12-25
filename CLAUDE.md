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
# Start full stack (postgres + auth-service + mcp-server + agent-a2a + web-chat)
docker compose up -d

# Run database migrations (first time setup)
docker compose run --rm auth-service uv run alembic upgrade head

# Rebuild after code changes
docker compose up -d --build mcp-server
docker compose up -d --build agent-a2a
docker compose up -d --build auth-service
docker compose up -d --build web-chat
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

### Cloud.ru Hosting

Agent supports unified environment variables for both local and Cloud.ru hosting:

**Variable Mapping:**

| Local Variable (Priority) | Cloud.ru Variable (Fallback) | Description |
|---------------------------|------------------------------|-------------|
| `OPENAI_API_KEY` | `LLM_API_KEY` | LLM API key |
| `OPENAI_BASE_URL` | `LLM_API_BASE` | LLM API base URL |
| `OPENAI_BASE_MODEL` | `LLM_MODEL` | Model name (cloud uses `hosted_vllm/` prefix) |
| `MCP_SERVER_URL` | `MCP_URL` | MCP server URL (cloud supports comma-separated list, takes first) |
| `A2A_SERVER_BASE_URL` | `URL_AGENT` | Agent public URL for Agent Card |
| — | `AGENT_NAME` | Agent name (default: "PM Copilot Agent") |
| — | `AGENT_DESCRIPTION` | Agent description (default: project description) |
| — | `AGENT_VERSION` | Agent version (default: "v1.0.0") |

**Priority:** Local variables (OPENAI_*, MCP_SERVER_URL, A2A_SERVER_BASE_URL) take precedence over Cloud.ru variables (LLM_*, MCP_URL, URL_AGENT) when both are present. This allows easier local development and debugging.

**Configuration:** All mappings are handled automatically in `agent/core/config.py` using Pydantic `AliasChoices`. No code changes needed for deployment.

**Example Cloud.ru Variables:**

```bash
LLM_API_KEY=sk-...
LLM_API_BASE=https://foundation-models.api.cloud.ru/v1
LLM_MODEL=hosted_vllm/Qwen/Qwen3-Coder-480B-A35B-Instruct
MCP_URL=http://mcp-server:8000/mcp
URL_AGENT=https://abc123-agent.ai-agent.inference.cloud.ru
AGENT_NAME=PM Copilot
AGENT_VERSION=v1.0.0
```

## Architecture

### Multi-User Authentication

PM Copilot supports multi-user authentication with dual auth methods:

#### Components

1. **auth_service** ([auth_service/](auth_service/)) - FastAPI service for user authentication:
   - Email/password registration and login (FastAPI Users)
   - OAuth support (Google, GitHub) via Chainlit
   - User management with custom fields (full_name, avatar_url, default_project_key)
   - PostgreSQL database with async SQLAlchemy
   - JWT authentication backend

2. **web_chat** ([web_chat/](web_chat/)) - Chainlit web interface with authentication:
   - Password auth callback → auth_service login endpoint
   - OAuth callback → auth_service OAuth endpoints
   - User metadata passed to agent via A2A Message.metadata

3. **Agent User Context** ([agent/a2a/converters.py:125-179](agent/a2a/converters.py#L125-L179)):
   - Extracts user info from A2A metadata for **audit logging only**
   - **IMPORTANT**: Agent does NOT enforce authorization
   - User context includes: user_id, user_email, user_full_name, default_project_key

#### Authentication Flow

```text
User → web_chat (Chainlit) → auth_service (FastAPI Users)
              ↓                         ↓
        agent-a2a (NO AUTH)       PostgreSQL
              ↓
        mcp-server
```

**Key Principles:**

- **Authorization at web_chat only**: Users must authenticate to access web interface
- **Agent remains open**: A2A agent accepts requests without auth (for integrations)
- **User context for audit**: User info logged but NOT used for access control
- **Dual auth methods**: Email/password + OAuth (both work simultaneously)

#### Database Schema

**Users table** ([migrations/versions/a46f779a458d_create_users_and_oauth_accounts_tables.py:24-38](migrations/versions/a46f779a458d_create_users_and_oauth_accounts_tables.py#L24-L38)):

- id (UUID), email, hashed_password
- is_active, is_superuser, is_verified (from FastAPI Users)
- full_name, avatar_url, default_project_key (custom fields)
- created_at, updated_at

**OAuth accounts table** ([migrations/versions/a46f779a458d_create_users_and_oauth_accounts_tables.py:40-55](migrations/versions/a46f779a458d_create_users_and_oauth_accounts_tables.py#L40-L55)):

- id (UUID), user_id (FK), oauth_name, access_token
- account_id, account_email
- Unique constraint: (oauth_name, account_id)

#### Configuration

**SECURITY REQUIREMENTS:**
- `POSTGRES_PASSWORD` — minimum 16 characters (REQUIRED)
- `AUTH_SECRET_KEY` — minimum 32 characters (REQUIRED)
- `CHAINLIT_AUTH_SECRET` — minimum 32 characters (REQUIRED)

Docker Compose will fail to start without these variables set.

Required environment variables ([.env.example:26-49](.env.example#L26-L49)):

```bash
# PostgreSQL
POSTGRES_USER=pm_user
# REQUIRED: Generate with: openssl rand -base64 32
POSTGRES_PASSWORD=<your-strong-password-min-16-chars>

# Auth Service
# Uses POSTGRES_PASSWORD from above
DATABASE_URL=postgresql+asyncpg://pm_user:${POSTGRES_PASSWORD}@postgres:5432/pm_copilot

# REQUIRED: Generate with: openssl rand -base64 48 (min 32 chars)
AUTH_SECRET_KEY=<your-secret-key-min-32-chars>
CHAINLIT_AUTH_SECRET=<your-chainlit-secret-min-32-chars>

# OAuth (optional)
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GITHUB_OAUTH_CLIENT_ID=
GITHUB_OAUTH_CLIENT_SECRET=
```

#### Database Migrations

```bash
# Run migrations (first time or after model changes)
uv run alembic upgrade head

# Create new migration (after model changes)
uv run alembic revision --autogenerate -m "Description"

# Rollback last migration
uv run alembic downgrade -1
```

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

#### Multi-Calendar Architecture

Each Jira project has its own Google Calendar:

- **Calendar naming**: Calendar name = project_key (e.g., "ALPHA", "BETA", "GAMMA")
- **Metadata storage**: Calendar description contains metadata in key=value format:

  ```text
  jira_project_key=ALPHA
  confluence_space_key=ALPHA
  ```

- **Auto-creation**: Calendars are automatically created when first accessed via `calendar_find_project_calendar`
- **Project isolation**: Events for different projects are stored in separate calendars
- **Service Account**: Uses Google Service Account authentication for programmatic access to all project calendars

### Agent Storage Architecture

PM Copilot Agent uses **hybrid storage** for production:

#### Conversation Checkpointing (AsyncPostgresSaver)

- **Implementation**: `AsyncPostgresSaver` from `langgraph-checkpoint-postgres`
- **Location**: `agent/core/checkpointer.py`
- **Persistence**: PostgreSQL (same database as auth_service: `pm_copilot`)
- **Purpose**: Track conversation state and LangGraph checkpoints
- **Tables**: `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`
- **Configuration**: `AGENT_DATABASE_URL` environment variable

#### Chat Session Management (ChatSession model)

- **Implementation**: SQLAlchemy model with async PostgreSQL
- **Location**: `auth_service/models/chat_session.py`
- **Persistence**: PostgreSQL (same database)
- **Purpose**: Map users to their conversation threads (multi-chat support)
- **API**: `/users/me/chat_sessions` endpoints in auth_service
- **Features**:
  - Auto-generated chat titles from first message
  - Soft limit: 100 active chats per user (auto-archives oldest)
  - Message count tracking
  - Last activity timestamp

#### Task Metadata Store (InMemoryTaskStore)

- **Implementation**: `InMemoryTaskStore` from a2a-sdk
- **Location**: `agent/a2a/server.py`
- **Persistence**: None (in-memory, lost on restart)
- **Purpose**: Store A2A task metadata during agent execution
- **Rationale**: A2A tasks are short-lived (seconds to minutes), conversation state already persisted in AsyncPostgresSaver

#### Database Schema

Single PostgreSQL database (`pm_copilot`) contains:

- `users`, `oauth_accounts` (auth_service)
- `chat_sessions` (auth_service, user → thread mapping)
- `checkpoints`, `checkpoint_blobs`, `checkpoint_writes` (LangGraph)

#### Key Features

- **Conversation history persists** across agent restarts via AsyncPostgresSaver
- **Multi-chat support**: Users can have up to 100 active chats simultaneously
- **Thread isolation**: Each chat has unique thread_id (context_id from A2A protocol)
- **Automatic cleanup**: Oldest chat auto-archived when user exceeds 100 chats

#### When to migrate to DatabaseTaskStore

Consider migrating InMemoryTaskStore → DatabaseTaskStore if you need:

- Long-running tasks (hours/days) that survive agent restarts
- Compliance audit trail for all A2A task transitions
- Distributed agent deployment (task metadata shared across instances)
- Task retry/replay functionality

For migration, install `a2a-sdk[postgresql]` and configure `USE_DATABASE_TASK_STORE=true`.

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

### Google Calendar Service Account Setup

The application uses Google Service Account authentication for Calendar API access:

1. **Create Service Account** in Google Cloud Console:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project or select existing one
   - Enable Google Calendar API
   - Create a Service Account with Calendar access
   - Generate and download JSON key file

2. **Configure Environment Variables**:

   ```bash
   GOOGLE_SERVICE_ACCOUNT_EMAIL=your-service-account@project.iam.gserviceaccount.com
   GOOGLE_SERVICE_ACCOUNT_KEY_JSON='{"type":"service_account","project_id":"...","private_key":"...","client_email":"..."}'
   ```

3. **Share Calendars** (optional):
   - Service account automatically creates calendars for each project
   - To access existing calendars, share them with the service account email
   - Grant "Make changes to events" permission

4. **Calendar Management**:
   - Use `calendar_find_project_calendar` to find or create calendar for a project
   - Calendar naming: calendar name matches Jira project_key (ALPHA, BETA, etc.)
   - Metadata stored in calendar description for project mapping

### Observability & Monitoring

The MCP server includes built-in OpenTelemetry tracing and Prometheus metrics support for production observability.

#### Configuration Strategy

The server supports **two deployment modes** with automatic environment detection:

1. **Phoenix Cloud** (managed) - Platform provides Phoenix-specific variables
2. **Self-hosted / Local dev** - Uses standard OpenTelemetry variables

All configuration is managed via `Settings` class in `pm_mcp/config.py`.

#### Environment Variables

**Phoenix Cloud (Production)** - Auto-provided by platform:

- `PHOENIX_PROJECT_NAME` - Project identifier (used as service.name in telemetry)
- `OTEL_ENDPOINT` - OTEL Telemetry collector endpoint (e.g., `http://otel-collector:4318`)
- `ENABLE_PHOENIX` - Enable Phoenix telemetry (default: `true`)
- `ENABLE_MONITORING` - Enable Prometheus metrics (default: `true`)

**Self-hosted / Local Development** - Standard OpenTelemetry variables:

- `LOG_LEVEL` - Logging level: DEBUG, INFO, WARNING, ERROR (default: `INFO`)
- `OTEL_EXPORTER_OTLP_ENDPOINT` - OTLP endpoint (empty = console exporter)
- `OTEL_SERVICE_NAME` - Service name for telemetry (default: `pm-mcp-server`)

**Fallback Logic** (priority order):

- **Service name**: `PHOENIX_PROJECT_NAME` → `OTEL_SERVICE_NAME` → `"pm-mcp-server"`
- **OTLP endpoint**: `OTEL_ENDPOINT` → `OTEL_EXPORTER_OTLP_ENDPOINT` → console exporter

#### Configuration Examples

**Phoenix Cloud** (no setup needed):

```bash
# Variables auto-provided by platform
PHOENIX_PROJECT_NAME=my-project
OTEL_ENDPOINT=http://otel-collector:4318
```

**Self-hosted with Jaeger**:

```bash
OTEL_SERVICE_NAME=pm-mcp-server
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318
```

**Local development** (traces to console):

```bash
# No variables needed - traces output to console
uv run python -m pm_mcp
```

#### Metrics Collected

**Tool Metrics**:

- `tool_calls_total` - Counter of tool invocations (labels: `tool_name`, `status`)
- `tool_duration_seconds` - Histogram of tool execution time (label: `tool_name`)

**API Metrics**:

- `api_calls_total` - Counter of external API calls (labels: `service`, `endpoint`, `status`)

**Instrumented Tools**:

- `jira_list_issues`, `jira_create_issues_batch`
- `pm_link_meeting_issues`, `pm_get_meeting_issues`, `pm_get_project_snapshot`

#### Behavior

- **When ENABLE_PHOENIX=false**: Telemetry disabled completely
- **When ENABLE_MONITORING=false**: Metrics use no-op implementation (zero overhead)
- **When OTEL endpoint not set**: Traces are logged to console for local debugging
- **Graceful degradation**: Telemetry errors don't affect MCP server functionality
