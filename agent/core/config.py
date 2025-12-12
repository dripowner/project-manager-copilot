"""Configuration settings for PM Copilot Agent."""

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """Settings for PM Copilot Agent.

    Configuration is loaded from environment variables and .env file.
    Supports both local and Cloud.ru hosting variable names.
    """

    # LLM Settings
    # OPENAI_* variables have priority over LLM_* (for easier local development)
    # Cloud.ru uses: LLM_API_KEY, LLM_API_BASE, LLM_MODEL
    # Local uses: OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_BASE_MODEL
    openai_api_key: str = Field(
        validation_alias=AliasChoices("OPENAI_API_KEY", "LLM_API_KEY"),
        description="OpenAI API key for LLM access (OPENAI_API_KEY has priority, fallback to LLM_API_KEY)",
    )
    openai_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_BASE_URL", "LLM_API_BASE"),
        description="OpenAI API base URL (OPENAI_BASE_URL has priority, fallback to LLM_API_BASE)",
    )
    openai_base_model: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices("OPENAI_BASE_MODEL", "LLM_MODEL"),
        description="OpenAI model to use (OPENAI_BASE_MODEL has priority, fallback to LLM_MODEL)",
    )
    max_iterations: int = Field(
        default=10,
        description="Maximum number of agent iterations",
        ge=1,
        le=50,
    )

    # MCP Server Configuration
    # Cloud.ru uses: MCP_URL (comma-separated list)
    # Local uses: MCP_SERVER_URL (single URL)
    mcp_server_url: str = Field(
        default="http://mcp-server:8000/mcp",
        validation_alias=AliasChoices("MCP_URL", "MCP_SERVER_URL"),
        description="MCP server URL. MCP_URL in cloud (takes first from list), MCP_SERVER_URL locally.",
    )

    # A2A Server Configuration
    # Cloud.ru uses: URL_AGENT
    # Local uses: A2A_SERVER_BASE_URL
    a2a_server_host: str = Field(
        default="0.0.0.0",
        description="A2A server host",
    )
    a2a_server_port: int = Field(
        default=8001,
        description="A2A server port",
    )
    a2a_server_base_url: str = Field(
        default="http://localhost:8001",
        validation_alias=AliasChoices("URL_AGENT", "A2A_SERVER_BASE_URL"),
        description="A2A server base URL for Agent Card (URL_AGENT in cloud, A2A_SERVER_BASE_URL locally)",
    )

    # Agent Card Metadata
    # Cloud.ru provides: AGENT_NAME, AGENT_DESCRIPTION, AGENT_VERSION
    agent_name: str = Field(
        default="PM Copilot Agent",
        description="Agent name for Agent Card",
    )
    agent_description: str = Field(
        default=(
            "AI-powered assistant for project managers. "
            "Automates sprint planning, status reporting, meeting coordination, "
            "and team workload management."
        ),
        description="Agent description for Agent Card",
    )
    agent_version: str = Field(
        default="v1.0.0",
        description="Agent version",
    )

    @field_validator("mcp_server_url", mode="before")
    @classmethod
    def parse_mcp_url(cls, v: str | None) -> str:
        """Parse MCP_URL from Cloud.ru (comma-separated list) or use single URL.

        Cloud.ru provides: MCP_URL=http://server1/sse,http://server2/sse
        We take the first URL from the list.
        """
        if v and "," in v:
            # Split by comma and take first URL
            urls = [url.strip() for url in v.split(",") if url.strip()]
            return urls[0] if urls else "http://mcp-server:8000/mcp"
        return v or "http://mcp-server:8000/mcp"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
